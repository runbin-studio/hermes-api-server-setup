#!/usr/bin/env python3
"""
Hermes 中继客户端 — 让无公网 IP 的 Hermes 实例可通过中继被 App 访问

用法:
  python3 relay-client.py --relay relay.example.com --token user-xxx

安装为服务:
  python3 relay-client.py --relay relay.example.com --token user-xxx --install

环境变量（优先级低于命令行参数）:
  RELAY_SERVER, RELAY_TOKEN, LOCAL_API_PORT
"""
import argparse
import asyncio
import json
import os
import signal
import sys
import time
import urllib.request
import urllib.error
import subprocess
import pathlib

VERSION = "1.0.0"
LOCAL_API = "http://127.0.0.1:8650"
RECONNECT_DELAY = 5  # 断线重连等待秒数


class RelayClient:
    def __init__(self, relay_host: str, token: str, local_port: int = 8650):
        self.relay_host = relay_host.rstrip("/")
        self.token = token
        self.local_port = local_port
        self.ws = None
        self.running = True
        self.relay_path = ""

    def _http_request(self, url: str, data: dict = None) -> dict:
        """发送 HTTP 请求"""
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
        except Exception as e:
            return {"error": str(e)}

    def _forward_request(self, msg: dict):
        """将中继转发的 HTTP 请求发给本地 API Server"""
        import http.client

        req_id = msg.get("id")
        method = msg.get("method", "POST")
        path = msg.get("path", "/v1/chat/completions")
        headers = msg.get("headers", {})
        body = msg.get("body")

        try:
            conn = http.client.HTTPConnection("127.0.0.1", self.local_port, timeout=60)
            conn.request(method, path, body=body, headers=headers)
            resp = conn.getresponse()
            resp_body = resp.read()

            # 将结果发回中继
            result = json.dumps({
                "id": req_id,
                "status": resp.status,
                "headers": dict(resp.getheaders()),
                "body": resp_body.decode("utf-8", errors="replace")
            })
            if self.ws and self.ws.sock and self.ws.sock.connected:
                self.ws.send(result)
            conn.close()
        except Exception as e:
            error_msg = json.dumps({
                "id": req_id, "status": 502,
                "body": f'{{"error":"relay proxy error: {str(e)}"}}'
            })
            if self.ws and self.ws.sock and self.ws.sock.connected:
                self.ws.send(error_msg)

    def connect(self):
        """连接中继服务器（同步阻塞，适合作为主循环）"""
        import websocket

        # 1. 注册
        register_url = f"{self.relay_host}/api/register"
        result = None
        for attempt in range(3):
            result = self._http_request(register_url, {
                "token": self.token, "version": VERSION})
            if "error" not in result:
                break
            print(f"[relay] 注册失败(尝试 {attempt+1}/3): {result.get('error')}")
            time.sleep(2)

        if not result or "error" in result:
            print(f"[relay] 注册失败，请检查中继地址和 token")
            return False

        ws_url = result.get("ws_url")
        self.relay_path = result.get("relay_path", "")
        print(f"[relay] 已注册，中继路径: {self.relay_path}")
        print(f"[relay] App 连接地址: {self.relay_host}{self.relay_path}/v1/chat/completions")

        # 2. 连接 WebSocket
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    on_message=lambda ws, msg: self._forward_request(json.loads(msg)),
                    on_error=lambda ws, err: print(f"[relay] 连接错误: {err}"),
                    on_close=lambda ws, code, msg: (
                        print(f"[relay] 连接断开 ({code})"),
                        print(f"[relay] {RECONNECT_DELAY} 秒后重连...")
                    ),
                    on_open=lambda ws: print(f"[relay] 已连接到中继服务器")
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
                if not self.running:
                    break
                time.sleep(RECONNECT_DELAY)
            except Exception as e:
                print(f"[relay] 异常: {e}")
                time.sleep(RECONNECT_DELAY)

        return True

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()


def install_service(relay: str, token: str, port: int):
    """安装为 systemd 用户服务"""
    home = pathlib.Path.home()
    service_dir = home / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)

    script_path = home / ".local" / "bin" / "hermes-relay-client.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)

    # 复制自身到目标路径
    import shutil
    shutil.copy(__file__, str(script_path))
    os.chmod(str(script_path), 0o755)

    service_content = f"""[Unit]
Description=Hermes Relay Client — 中继连接
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={sys.executable} {script_path} --relay {relay} --token {token} --port {port}
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
"""
    service_file = service_dir / "hermes-relay.service"
    service_file.write_text(service_content)

    # 启用并启动服务
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "--user", "enable", "hermes-relay"], check=False)
    subprocess.run(["systemctl", "--user", "start", "hermes-relay"], check=False)

    print(f"[relay] ✅ 服务已安装并启动")
    print(f"   查看状态: systemctl --user status hermes-relay")
    print(f"   查看日志: journalctl --user -u hermes-relay -f")


def main():
    parser = argparse.ArgumentParser(description="Hermes 中继客户端")
    parser.add_argument("--relay", default=os.getenv("RELAY_SERVER", ""),
                        help="中继服务器地址")
    parser.add_argument("--token", default=os.getenv("RELAY_TOKEN", ""),
                        help="用户 token")
    parser.add_argument("--port", type=int,
                        default=int(os.getenv("LOCAL_API_PORT", "8650")),
                        help="本地 API Server 端口")
    parser.add_argument("--install", action="store_true",
                        help="安装为 systemd 服务")
    args = parser.parse_args()

    if not args.relay or not args.token:
        parser.print_help()
        print("\n错误: 必须指定 --relay 和 --token")
        print("  或设置环境变量 RELAY_SERVER 和 RELAY_TOKEN")
        sys.exit(1)

    if args.install:
        install_service(args.relay, args.token, args.port)
        return

    client = RelayClient(args.relay, args.token, args.port)
    signal.signal(signal.SIGINT, lambda s, f: client.stop())
    signal.signal(signal.SIGTERM, lambda s, f: client.stop())

    try:
        client.connect()
    except KeyboardInterrupt:
        print("\n[relay] 已停止")


if __name__ == "__main__":
    main()