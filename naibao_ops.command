#!/bin/bash

# macOS 双击即可启动：奶宝 · 本机托管运营台
# - 会在终端中启动运营台（保持运行），并自动打开浏览器页面
# - 若你想停止：在终端窗口按 Ctrl+C

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo ""
echo "奶宝 · 本机托管运营台启动中..."
echo "提示：关闭此终端窗口会停止运营台。"
echo ""

bash "$ROOT_DIR/scripts/local_ops.sh"

