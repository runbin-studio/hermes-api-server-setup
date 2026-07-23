---
name: api-server-setup
description: "一键配置 Hermes API Server + 中继客户端，生成连接参数供 App 使用"
version: 2.0.0
author: runbin-studio
license: MIT
metadata:
  hermes:
    tags: [api-server, relay, tunnel, mobile, setup]
    homepage: https://github.com/runbin-studio/hermes-api-server-setup
---

# Hermes API Server + 中继配置

让你的 Hermes 实例可以被手机 App 访问。支持两种场景：

| 场景 | 方案 | 用户需要 |
|------|------|---------|
| **云服务器**（有公网 IP） | API Server 直连 | 开安全组端口 |
| **家里电脑/NAS**（无公网 IP） | 中继模式 | 一个 token |

## 用法

```bash
# 加载技能
/skill api-server-setup

# Agent 会先问你的场景：
# 1. 云服务器 → 配置 API Server，输出连接参数
# 2. 家里电脑 → 配置中继客户端，连接到中继服务器
```

## 场景一：云服务器直连

Agent 自动执行：

1. 检查当前 API Server 配置状态
2. 写入环境变量启用 API Server（端口 8650）
3. 生成随机 64 位 API Key
4. 重启 Gateway
5. 获取公网 IP
6. 检测端口是否对外开放
7. 输出连接参数（含二维码文本）

## 场景二：家里电脑中继

Agent 自动执行：

1. 检查 API Server 是否运行
2. 提示用户在 App 上注册获取 token
3. 下载中继客户端 `relay-client.py`
4. 安装为 systemd 服务，开机自启
5. 输出 App 连接地址

## 输出示例

### 云服务器模式

```
┌─────────────────────────────────────────────┐
│  ✅ API Server 已启动                        │
│                                              │
│  地址    118.196.76.18                       │
│  端口    8650                                │
│  Key     d20c...1b7d                         │
│                                              │
│  ⚠️ 别忘了去云服务器安全组开放 8650 端口！     │
└─────────────────────────────────────────────┘
```

### 中继模式

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

## 相关文件

| 文件 | 用途 |
|------|------|
| `setup.sh` | 云服务器模式一键脚本 |
| `relay-client.py` | 中继客户端（Python） |
| `relay-setup.md` | 中继模式技能描述 |

## 依赖

- Hermes Agent 已安装并运行
- `curl`、`openssl`
- 中继模式需要 `websocket-client`（`pip install websocket-client`）