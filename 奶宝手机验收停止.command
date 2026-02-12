#!/bin/bash

# macOS 双击即可停止：手机外网验收（停止 cloudflared + 前端 dev server；不动 docker 后端）

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo ""
echo "奶宝 · 手机外网验收停止中..."
echo ""

bash "$ROOT_DIR/scripts/stop_mobile_preview.sh"

echo ""
echo "✅ 已停止。"
echo ""

