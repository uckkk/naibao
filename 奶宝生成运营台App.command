#!/bin/bash

# macOS 双击即可运行：生成“奶宝 App 合集”（无终端）
#
# 生成后，把这些 .app 保持放在仓库根目录（与 scripts/ 同级），即可直接双击运行（无需终端）：
# - 奶宝运营台.app / 停止奶宝运营台.app
# - 奶宝手机验收.app / 停止奶宝手机验收.app

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo ""
echo "奶宝 · 生成运营台 App 中..."
echo ""

bash "$ROOT_DIR/scripts/macos/build_ops_apps.sh"

echo ""
echo "✅ 已完成。"
echo ""
