---
name: relay-setup
description: "一键配置中继客户端，让无公网 IP 的 Hermes 可通过中继被 App 访问"
version: 1.0.0
author: runbin-studio
license: MIT
metadata:
  hermes:
    tags: [relay, tunnel, mobile, setup]
    homepage: https://github.com/runbin-studio/hermes-api-server-setup
---

# Relay Setup

让你的 Hermes 通过中继服务器被 App 访问，适用于家里电脑 / NAS 等无公网 IP 的场景。

## 原理

```
家里 Hermes → 中继客户端（主动连接）→ 中继服务器（有公网 IP）→ 手机 App
```

用户不需要公网 IP、不需要路由器端口转发、不需要配置防火墙。

## 用法

```bash
# 安装技能
hermes skills install https://raw.githubusercontent.com/runbin-studio/hermes-api-server-setup/main/relay-setup.md

# 加载技能
/skill relay-setup

# Agent 会引导你完成：
# 1. 在 App 上注册账号，获取 token
# 2. 输入中继服务器地址和 token
# 3. 自动下载并启动中继客户端
# 4. 验证连接是否正常
```

## 执行流程

1. 检查 API Server 是否运行（`:8650`）
2. 提示用户输入中继地址和 token
3. 下载 `relay-client.py` 到本地
4. `pip install websocket-client`
5. 安装为 systemd 用户服务（开机自启）
6. 启动并验证连接
7. 输出 App 连接地址

## 输出示例

```
┌─────────────────────────────────────────────┐
│  ✅ 中继连接已建立                           │
│                                              │
│  App 连接地址：                               │
│  https://relay.example.com/relay/user-xxx    │
│                                              │
│  管理命令：                                   │
│  systemctl --user status hermes-relay        │
│  journalctl --user -u hermes-relay -f       │
└─────────────────────────────────────────────┘
```

## 依赖

- Hermes Agent 已安装
- API Server 已启用（端口 8650）
- `websocket-client`（`pip install websocket-client`）
- systemd（Linux）
- 中继服务器已部署