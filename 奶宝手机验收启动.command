#!/bin/bash

# macOS 双击即可启动：手机外网验收（前端 dev + 后端 docker + Cloudflare 临时域名）
#
# 结束方式：
# - 双击运行 `奶宝手机验收停止.command`

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo ""
echo "奶宝 · 手机外网验收启动中..."
echo ""

bash "$ROOT_DIR/scripts/start_mobile_preview.sh" | tee "/tmp/naibao_mobile_preview.log"

URL_FILE="$ROOT_DIR/frontend/mobile-preview.url"
if [ -f "$URL_FILE" ]; then
  URL="$(cat "$URL_FILE" | head -n 1 | tr -d '[:space:]')"
  if [ -n "$URL" ]; then
    echo ""
    echo "✅ 外网验收链接：$URL"
    if command -v pbcopy >/dev/null 2>&1; then
      printf "%s" "$URL" | pbcopy
      echo "（已复制到剪贴板）"
    fi
  fi
fi

