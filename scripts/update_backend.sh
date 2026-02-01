#!/bin/bash

# 更新后端代码并重启服务

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/lib/common.sh"

require_var "SSH_HOST"

REMOTE_PATH="${REMOTE_PATH:-${REMOTE_BASE}/backend}"

SSH_ARGS=(-o StrictHostKeyChecking=no -p "${SSH_PORT}")
SCP_ARGS=(-P "${SSH_PORT}")
if [ -n "${SSH_KEY}" ]; then
  SSH_ARGS+=(-i "${SSH_KEY}")
  SCP_ARGS+=(-i "${SSH_KEY}")
fi

echo "=========================================="
echo "  更新后端代码"
echo "=========================================="
echo ""

# 检查本地backend目录
if [ ! -d "backend" ]; then
    echo "❌ 错误: 找不到backend目录"
    exit 1
fi

echo "📦 上传更新后的代码..."
# 只上传修改的文件
scp "${SCP_ARGS[@]}" "backend/router/middleware/cors.go" "${SSH_USER}@${SSH_HOST}:${REMOTE_PATH}/router/middleware/cors.go"

echo ""
echo "🔨 在服务器上重新编译..."
ssh "${SSH_ARGS[@]}" "${SSH_USER}@${SSH_HOST}" << 'EOF'
cd /opt/naibao/backend

# 设置Go环境
export PATH=$PATH:/usr/local/go/bin
export GOPROXY=https://goproxy.cn,direct
export GO111MODULE=on

# 停止旧服务
if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "停止旧服务 (PID: $PID)..."
        kill $PID
        sleep 2
    fi
fi

# 重新编译
echo "编译新版本..."
go build -o naibao-server main.go

# 启动新服务
echo "启动新服务..."
nohup ./naibao-server > server.log 2>&1 &
echo $! > server.pid

sleep 2

# 检查服务状态
if ps -p $(cat server.pid) > /dev/null 2>&1; then
    echo "✅ 服务启动成功 (PID: $(cat server.pid))"
else
    echo "❌ 服务启动失败"
    echo "查看错误日志:"
    tail -20 server.log
    exit 1
fi

# 测试健康检查
echo ""
echo "测试健康检查..."
sleep 1
curl -s http://127.0.0.1:8080/health
echo ""
EOF

echo ""
echo "=========================================="
echo "✅ 更新完成！"
echo "=========================================="
echo ""
echo "请测试注册功能是否正常"

