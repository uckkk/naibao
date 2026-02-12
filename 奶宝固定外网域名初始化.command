#!/bin/bash

# macOS 双击即可运行：初始化固定外网域名（Cloudflare Named Tunnel）
#
# 说明：
# - 会打开浏览器进行 Cloudflare 授权（login）
# - 会在仓库的 .naibao_runtime/ 生成 cloudflared_named.yml（不覆盖 ~/.cloudflared/config.yml）
#
# 运行完成后：打开运营台，点击“启动 Tunnel”即可。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo ""
echo "奶宝 · 固定外网域名初始化中..."
echo ""

bash "$ROOT_DIR/scripts/setup_named_tunnel.sh"

