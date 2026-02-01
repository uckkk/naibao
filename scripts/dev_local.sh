#!/bin/bash

# 本地一键：启动后端依赖（Docker）+ 运行 API 冒烟测试 + 构建前端（H5）

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================="
echo "  naibao 本地验收：启动 + 冒烟测试"
echo "=========================================="
echo ""

command -v docker >/dev/null 2>&1 || { echo "❌ 未找到 docker"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ 未找到 python3"; exit 1; }

echo "📦 启动 docker compose（Postgres/Redis/Backend）..."
docker compose -f "${ROOT_DIR}/docker-compose.yml" up -d --build

echo ""
echo "🧪 运行 API 冒烟测试..."
python3 "${ROOT_DIR}/scripts/smoke_test.py"

echo ""
echo "🏗️  构建前端（H5）..."
(cd "${ROOT_DIR}/frontend" && npm run build:h5)

echo ""
echo "=========================================="
echo "✅ 本地验收（自动化）通过"
echo "=========================================="
echo ""
echo "下一步（手机端手动验收）："
echo "1) 配置 frontend/.env.local（可选）"
echo "2) 启动前端：cd frontend && npm run dev:h5"
echo "3) 手机打开终端输出的 Network 地址"
echo ""

