#!/usr/bin/env bash

# 一键打开“本机托管运营台”：
# - 打开本地网页，查看 docker 服务 / API 健康 / tunnel 状态
# - 提供一键启动与重启能力

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "${ROOT_DIR}/scripts/local_ops_console.py" --open

