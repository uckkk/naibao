#!/usr/bin/env bash

# 一次性初始化 Cloudflare Named Tunnel（固定域名 api.naibao.me）
#
# 目标：
# - 让后端在本机跑（Docker），但外网稳定通过 https://api.naibao.me 访问
# - 不污染 ~/.cloudflared/config.yml：把本项目配置写入 .naibao_runtime/cloudflared_named.yml
#
# 你需要手动完成的事情（无法自动化）：
# 1) 在 Cloudflare 添加域名 naibao.me
# 2) 在 Spaceship 把 Nameserver 改成 Cloudflare 给你的两条 NS
#
# 运行方式：
# - 终端：bash scripts/setup_named_tunnel.sh
# - macOS：双击 “奶宝固定外网域名初始化.command”

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="$ROOT_DIR/deploy/.env.home"
PUBLIC_DOMAIN="naibao.me"
TUNNEL_NAME="naibao-api"
HOSTNAME="api.naibao.me"
BACKEND_PORT="18080"
SERVICE_URL="http://127.0.0.1:${BACKEND_PORT}"

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
  PUBLIC_DOMAIN="${NB_PUBLIC_DOMAIN:-$PUBLIC_DOMAIN}"
  TUNNEL_NAME="${NB_TUNNEL_NAME:-$TUNNEL_NAME}"
  HOSTNAME="${NB_TUNNEL_HOSTNAME:-$HOSTNAME}"
  BACKEND_PORT="${NB_BACKEND_HOST_PORT:-$BACKEND_PORT}"
  SERVICE_URL="http://127.0.0.1:${BACKEND_PORT}"
fi

echo ""
echo "[0/4] 预检查：域名 NS（${PUBLIC_DOMAIN}）"
if command -v dig >/dev/null 2>&1; then
  NS="$(dig +short NS "$PUBLIC_DOMAIN" 2>/dev/null || true)"
  echo "$NS" | sed '/^$/d' || true
  if echo "$NS" | grep -qi "cloudflare"; then
    echo "✅ 已检测到 Cloudflare NS"
  else
    echo "⚠️  未检测到 Cloudflare NS（当前仍可能在 Spaceship）。"
    echo "   你需要先在 Cloudflare 添加域名，并把 Spaceship 的 NS 改为 Cloudflare 提供的两条 NS。"
  fi
else
  echo "（未找到 dig，跳过 NS 检查）"
fi

echo ""
echo "[1/4] 准备 cloudflared"
CLOUDFLARED_BIN="$(command -v cloudflared 2>/dev/null || true)"
if [ -z "$CLOUDFLARED_BIN" ]; then
  BIN_DIR="$ROOT_DIR/scripts/bin"
  LOCAL_BIN="$BIN_DIR/cloudflared"
  mkdir -p "$BIN_DIR"

  OS="$(uname -s)"
  ARCH="$(uname -m)"
  if [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
    ASSET="cloudflared-darwin-arm64"
  elif [ "$OS" = "Darwin" ] && [ "$ARCH" = "x86_64" ]; then
    ASSET="cloudflared-darwin-amd64"
  elif [ "$OS" = "Linux" ] && [ "$ARCH" = "x86_64" ]; then
    ASSET="cloudflared-linux-amd64"
  elif [ "$OS" = "Linux" ] && [ "$ARCH" = "aarch64" ]; then
    ASSET="cloudflared-linux-arm64"
  else
    echo "ERROR: cloudflared auto-download unsupported for $OS/$ARCH" >&2
    exit 1
  fi

  if [ -x "$LOCAL_BIN" ] && ! "$LOCAL_BIN" --version >/dev/null 2>&1; then
    echo "local cloudflared is invalid. re-downloading..."
    rm -f "$LOCAL_BIN" || true
  fi

  if [ ! -x "$LOCAL_BIN" ]; then
    echo "cloudflared not found. downloading $ASSET..."
    curl -L --http1.1 -o "$LOCAL_BIN.download" "https://github.com/cloudflare/cloudflared/releases/latest/download/$ASSET"
    chmod +x "$LOCAL_BIN.download"
    mv "$LOCAL_BIN.download" "$LOCAL_BIN"
  fi
  CLOUDFLARED_BIN="$LOCAL_BIN"
fi

echo "cloudflared: $CLOUDFLARED_BIN"
"$CLOUDFLARED_BIN" --version | head -n 1 || true

echo ""
echo "[2/4] Cloudflare 授权（会打开浏览器）"
echo "提示：如果你还没把 ${PUBLIC_DOMAIN} 接入 Cloudflare，也可以先完成 login；后面 route dns 可能会失败，但可在接入后重跑本脚本。"
CERT_PATH="$HOME/.cloudflared/cert.pem"
if [ -f "${CERT_PATH}" ]; then
  # NOTE: 必须用 ${VAR} 包住，否则紧跟中文全角括号时 bash 可能会把括号吞进变量名（set -u 下会直接报 unbound）。
  echo "✅ 已检测到授权凭据：${CERT_PATH}（跳过登录）"
else
  "$CLOUDFLARED_BIN" tunnel login
fi

echo ""
echo "[3/4] 创建/复用 Tunnel：${TUNNEL_NAME}"
TUN_ID="$(
  "$CLOUDFLARED_BIN" tunnel list -o json 2>/dev/null | python3 -c '
import json, sys

name = sys.argv[1]
try:
    data = json.load(sys.stdin)
except Exception:
    data = []
if isinstance(data, dict) and isinstance(data.get("tunnels"), list):
    data = data.get("tunnels")

tid = next(
    (t.get("id") for t in (data or []) if isinstance(t, dict) and t.get("name") == name and t.get("id")),
    "",
)
print(tid)
' "$TUNNEL_NAME"
)"

if [ -z "$TUN_ID" ]; then
  OUT="$("$CLOUDFLARED_BIN" tunnel create "$TUNNEL_NAME" 2>&1 || true)"
  echo "$OUT"
  TUN_ID="$(printf \"%s\" \"$OUT\" | python3 -c 'import re,sys; s=sys.stdin.read(); m=re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", s); print(m.group(1) if m else "")')"
fi

if [ -z "$TUN_ID" ]; then
  echo "ERROR: 无法获取 tunnel id（请检查 cloudflared 输出/权限）" >&2
  exit 2
fi

echo "tunnel id: $TUN_ID"

echo ""
echo "[3.5/4] 绑定域名：${HOSTNAME}"
set +e
"$CLOUDFLARED_BIN" tunnel route dns --overwrite-dns "$TUNNEL_NAME" "$HOSTNAME"
ROUTE_RC="$?"
set -e
if [ "$ROUTE_RC" -eq 0 ]; then
  echo "✅ 已创建 DNS 路由（Cloudflare）"
else
  echo "⚠️  route dns 失败（很可能是 ${PUBLIC_DOMAIN} 还未切到 Cloudflare NS）。"
  echo "   你可以先把 NS 切到 Cloudflare，生效后再重跑本脚本。"
fi

echo ""
echo "[4/4] 写入本项目 Tunnel 配置（不覆盖 ~/.cloudflared/config.yml）"
RUNTIME_DIR="$ROOT_DIR/.naibao_runtime"
mkdir -p "$RUNTIME_DIR"
CFG="$RUNTIME_DIR/cloudflared_named.yml"
CRED="$HOME/.cloudflared/$TUN_ID.json"
if [ ! -f "$CRED" ]; then
  # 兜底：查找任意同 ID 的 json
  FOUND="$(ls -1 "$HOME/.cloudflared/"*.json 2>/dev/null | grep -F "$TUN_ID" | head -n 1 || true)"
  if [ -n "$FOUND" ]; then
    CRED="$FOUND"
  fi
fi

cat > "$CFG" <<YAML
tunnel: $TUN_ID
credentials-file: $CRED

ingress:
  - hostname: $HOSTNAME
    service: $SERVICE_URL
  - service: http_status:404
YAML

echo "✅ 已生成：$CFG"
echo ""
echo "下一步："
echo "1) 打开运营台（双击 奶宝运营台.command）"
echo "2) 在运营台里点：启动 Tunnel"
echo ""
echo "验证："
echo "curl -fsSL \"https://${HOSTNAME}/api/health\""
echo ""
