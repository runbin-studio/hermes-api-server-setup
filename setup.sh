#!/usr/bin/env bash
# Hermes API Server 一键配置脚本
# 用法: bash setup.sh
# 或: chmod +x setup.sh && ./setup.sh
set -e

# ── 颜色 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── 配置 ──
ENV_FILE="$HOME/.hermes/.env"
PORT="${API_SERVER_PORT:-8650}"

echo -e "${CYAN}┌─────────────────────────────────────┐${NC}"
echo -e "${CYAN}│  Hermes API Server 一键配置           │${NC}"
echo -e "${CYAN}└─────────────────────────────────────┘${NC}"
echo ""

# ── 检查依赖 ──
for cmd in curl openssl; do
  if ! command -v $cmd &>/dev/null; then
    echo -e "${RED}✗ 缺少依赖: $cmd${NC}"
    exit 1
  fi
done

# ── 检查 Hermes 是否安装 ──
if ! command -v hermes &>/dev/null; then
  echo -e "${RED}✗ 未检测到 Hermes，请先安装 Hermes Agent${NC}"
  exit 1
fi

# ── 检查 .env 文件是否存在 ──
if [ ! -f "$ENV_FILE" ]; then
  echo -e "${YELLOW}! 未找到 .env 文件，创建中...${NC}"
  touch "$ENV_FILE"
fi

# ── 检查是否已配置 ──
if grep -q "API_SERVER_ENABLED=true" "$ENV_FILE" 2>/dev/null; then
  echo -e "${YELLOW}! API Server 已启用，将重新生成配置${NC}"
  echo ""
fi

# ── 生成 API Key ──
API_KEY=$(openssl rand -hex 32)
echo -e "${GREEN}✓ 已生成 API Key${NC}"

# ── 写入环境变量 ──
# 清理旧的 API Server 配置
sed -i '/^API_SERVER_ENABLED=/d' "$ENV_FILE" 2>/dev/null || true
sed -i '/^API_SERVER_PORT=/d' "$ENV_FILE" 2>/dev/null || true
sed -i '/^API_SERVER_HOST=/d' "$ENV_FILE" 2>/dev/null || true
sed -i '/^API_SERVER_KEY=/d' "$ENV_FILE" 2>/dev/null || true

# 写入新配置
cat >> "$ENV_FILE" << EOF

# API Server (由 api-server-setup 配置)
API_SERVER_ENABLED=true
API_SERVER_PORT=$PORT
API_SERVER_HOST=0.0.0.0
API_SERVER_KEY=$API_KEY
EOF

echo -e "${GREEN}✓ 环境变量已写入 $ENV_FILE${NC}"

# ── 重启 Gateway ──
echo -e "${YELLOW}⏳ 重启 Gateway...${NC}"
if hermes gateway restart 2>/dev/null; then
  echo -e "${GREEN}✓ Gateway 已重启${NC}"
else
  echo -e "${YELLOW}⚠ 重启失败，请手动执行: hermes gateway restart${NC}"
fi

# ── 等待端口监听 ──
sleep 3

# ── 获取公网 IP ──
PUBLIC_IP=""
for src in "https://ifconfig.me" "https://ip.sb" "https://api.ipify.org"; do
  PUBLIC_IP=$(curl -s --max-time 5 "$src" 2>/dev/null) && [ -n "$PUBLIC_IP" ] && break
done

if [ -z "$PUBLIC_IP" ]; then
  PUBLIC_IP="无法获取"
  echo -e "${YELLOW}⚠ 无法获取公网 IP${NC}"
else
  echo -e "${GREEN}✓ 公网 IP: $PUBLIC_IP${NC}"
fi

# ── 检查端口是否开放 ──
PORT_OPEN=false
if [ "$PUBLIC_IP" != "无法获取" ]; then
  if curl -s --max-time 5 "http://$PUBLIC_IP:$PORT/v1/chat/completions" \
    -H "Authorization: Bearer $API_KEY" \
    -d '{"model":"default","messages":[{"role":"user","content":"ping"}],"stream":false}' >/dev/null 2>&1; then
    PORT_OPEN=true
    echo -e "${GREEN}✓ 端口 $PORT 已对外开放${NC}"
  else
    echo -e "${RED}⚠ 端口 $PORT 未对外开放${NC}"
    echo -e "${YELLOW}  请去云服务器安全组添加入站规则: TCP/$PORT${NC}"
  fi
fi

# ── 输出连接信息 ──
echo ""
echo -e "${CYAN}┌─────────────────────────────────────────────┐${NC}"
echo -e "${CYAN}│  ✅ API Server 已启动                        │${NC}"
echo -e "${CYAN}├─────────────────────────────────────────────┤${NC}"
echo -e "${CYAN}│                                              │${NC}"
echo -e "│  连接信息（在 App 中输入）：                   │"
echo -e "│                                              │"
printf "│  %-8s %-35s │\n" "地址" "$PUBLIC_IP"
printf "│  %-8s %-35s │\n" "端口" "$PORT"
printf "│  %-8s %-35s │\n" "Key" "${API_KEY:0:16}...${API_KEY: -4}"
echo -e "│                                              │"
echo -e "│  二维码文本（App 扫码解析）：                  │"
echo -e "│  ${GREEN}hermes://$PUBLIC_IP:$PORT?key=$API_KEY${NC}   │"
echo -e "│                                              │"
if [ "$PORT_OPEN" = false ]; then
  echo -e "│  ${RED}⚠ 端口未开放，请检查安全组配置${NC}          │"
fi
echo -e "${CYAN}└─────────────────────────────────────────────┘${NC}"
echo ""
echo -e "完整 API Key: ${YELLOW}$API_KEY${NC}"
echo ""