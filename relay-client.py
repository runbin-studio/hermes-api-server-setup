#!/usr/bin/env python3
"""Hermes 中继客户端 — 连接中继服务器"""
import argparse
import http.client
import json
import signal
import sys
import time
import urllib.request

VERSION = "1.0.0"
RECONNECT_DELAY = 5


class RelayClient:
    def __init__(self, relay_host, token, target):
        self.relay_host = relay_host.rstrip("/")
        self.token = token
        self.target = target.rstrip("/")
        self.ws = None
        self.running = True
        # 解析 target 的 host 和 port
        t = self.target.split("://")[-1].split("/")[0]
        self._target_host = t.split(":")[0]
        self._target_port = int(t.split(":")[1]) if ":" in t else 80

    def _http(self, url, data=None):
        body = json.dumps(data).encode() if data else None
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}),
                timeout=10)
            return json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}

    def connect(self):
        import websocket
        print("[relay] 注册到 %s/api/register ..." % self.relay_host)
        for i in range(3):
            r = self._http("%s/api/register" % self.relay_host,
                           {"token": self.token, "version": VERSION})
            if "error" not in r:
                break
            print("[relay] 重试 %d/3: %s" % (i + 1, r.get("error")))
            time.sleep(2)
        else:
            print("[relay] 注册失败")
            return False

        ws_url = r.get("ws_url")
        rpath = r.get("relay_path", "")
        print("[relay] 已注册, 中继路径: %s" % rpath)
        print("[relay] App 连接地址: %s%s/v1/chat/completions" % (self.relay_host, rpath))

        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    on_message=lambda ws, msg: self._forward(msg),
                    on_error=lambda ws, e: print("[relay] 错误: %s" % e),
                    on_close=lambda ws, c, m: (
                        print("[relay] 断开 (%d), %ds 后重连..." % (c or 0, RECONNECT_DELAY)),
                        time.sleep(RECONNECT_DELAY)),
                    on_open=lambda ws: print("[relay] WebSocket 已连接")
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
                if not self.running:
                    break
            except Exception as e:
                print("[relay] 异常: %s" % e)
                time.sleep(RECONNECT_DELAY)
        return True

    def _forward(self, raw):
        req_id = None
        try:
            msg = json.loads(raw)
            req_id = msg["id"]
            method = msg.get("method", "POST")
            path = msg.get("path", "/v1/chat/completions")
            headers = msg.get("headers", {})
            body = msg.get("body")

            # 判断是否流式请求
            is_stream = False
            if body:
                try:
                    body_json = json.loads(body)
                    is_stream = body_json.get("stream", False)
                except json.JSONDecodeError:
                    pass

            conn = http.client.HTTPConnection(
                self._target_host, self._target_port, timeout=60)
            conn.request(method, path, body=body.encode("utf-8") if body else None, headers=headers)
            resp = conn.getresponse()

            if is_stream:
                # 流式路径：逐 chunk 转发
                # 不设超时，让 readline 自然阻塞等下一行数据
                buf = ""
                while True:
                    try:
                        line = resp.readline()
                    except Exception:
                        break
                    if not line:
                        break
                    line_decoded = line.decode("utf-8", errors="replace")
                    buf += line_decoded
                    # SSE 事件以空行结束，此时发一个 chunk
                    if line_decoded == "\n" or line_decoded == "\r\n":
                        if self.ws and self.ws.sock and self.ws.sock.connected:
                            try:
                                self.ws.send(json.dumps({
                                    "id": req_id, "chunk": buf
                                }))
                            except Exception:
                                pass
                        buf = ""
                # 发结束标志
                if self.ws and self.ws.sock and self.ws.sock.connected:
                    try:
                        self.ws.send(json.dumps({
                            "id": req_id, "chunk": "", "done": True
                        }))
                    except Exception:
                        pass
            else:
                # 非流式路径：一次性发
                resp_body = resp.read()
                result = json.dumps({
                    "id": req_id, "status": resp.status,
                    "headers": dict(resp.getheaders()),
                    "body": resp_body.decode("utf-8", errors="replace")
                })
                if self.ws and self.ws.sock and self.ws.sock.connected:
                    self.ws.send(result)
            conn.close()
        except Exception as e:
            if req_id:
                err = json.dumps({
                    "id": req_id, "status": 502,
                    "body": '{"error":"relay proxy error: %s"}' % str(e)
                })
                if self.ws and self.ws.sock and self.ws.sock.connected:
                    self.ws.send(err)

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()


def main():
    p = argparse.ArgumentParser(description="Hermes 中继客户端")
    p.add_argument("--relay", required=True, help="中继服务器地址")
    p.add_argument("--token", required=True, help="用户 token")
    p.add_argument("--target", default="http://127.0.0.1:8650",
                    help="本地 API Server 地址")
    args = p.parse_args()

    c = RelayClient(args.relay, args.token, args.target)
    signal.signal(signal.SIGINT, lambda s, f: c.stop())
    signal.signal(signal.SIGTERM, lambda s, f: c.stop())

    try:
        c.connect()
    except KeyboardInterrupt:
        print("\n[relay] 已停止")


if __name__ == "__main__":
    main()