---
name: api-server-setup
description: "一键配置 Hermes API Server，生成连接参数供 App 使用"
version: 1.0.0
author: runbin-studio
license: MIT
metadata:
  hermes:
    tags: [api-server, setup, mobile, gateway]
    homepage: https://github.com/runbin-studio/hermes-api-server-setup
---

# API Server Setup

一键在你的 Hermes 实例上启用 API Server，生成 App 连接所需的地址和密钥。

## 用法

```bash
# 加载技能
/skill api-server-setup

# 或直接运行
hermes -s api-server-setup -q "帮我配置 API Server"
```

## 功能

1. 检查当前 API Server 配置状态
2. 自动写入环境变量启用 API Server
3. 生成随机 64 位 API Key
4. 重启 Gateway 使配置生效
5. 获取公网 IP
6. 输出连接参数（含二维码文本）
7. 检测端口是否对外开放

## 输出示例

```
┌─────────────────────────────────────────────┐
│  ✅ API Server 已启动                        │
├─────────────────────────────────────────────┤
│                                              │
│  连接信息（在 App 中输入）：                   │
│                                              │
│  地址    118.196.76.18                       │
│  端口    8650                                │
│  Key     d20cfd6f99d30190eee505fb8972ea6b    │
│                                              │
│  二维码文本（App 扫码解析）：                  │
│  hermes://118.196.76.18:8650?key=...         │
│                                              │
│  ⚠️ 别忘了去云服务器安全组开放 8650 端口！     │
│  检测结果：端口未开放 → 请检查安全组配置       │
└─────────────────────────────────────────────┘
```

## 环境变量

技能会自动设置以下环境变量到 `~/.hermes/.env`：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_SERVER_ENABLED` | `true` | 启用 API Server |
| `API_SERVER_PORT` | `8650` | 监听端口 |
| `API_SERVER_HOST` | `0.0.0.0` | 监听地址（允许外部访问） |
| `API_SERVER_KEY` | `随机生成` | 认证密钥，64 位十六进制 |

## 依赖

- Hermes Agent 已安装并运行
- `curl`（用于获取公网 IP）
- `openssl`（用于生成随机密钥）
- `hermes gateway restart` 可用