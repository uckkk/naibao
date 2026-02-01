#!/bin/bash

# 测试服务器连接脚本
# 支持SSH密钥认证和密码认证

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/lib/common.sh"

require_var "SSH_HOST"

SERVER_IP="${SERVER_IP:-${SSH_HOST}}"
SERVER_USER="${SERVER_USER:-${SSH_USER}}"

SSH_ARGS=(-o ConnectTimeout=5 -o StrictHostKeyChecking=no -p "${SSH_PORT}")
if [ -n "${SSH_KEY}" ]; then
  SSH_ARGS+=(-i "${SSH_KEY}")
fi

echo "=========================================="
echo "  测试服务器连接"
echo "=========================================="
echo ""

# 测试SSH连接
echo "测试SSH连接..."
if ssh "${SSH_ARGS[@]}" "${SERVER_USER}@${SERVER_IP}" "echo '连接成功'"; then
    echo "✅ SSH连接成功"
else
    echo "❌ SSH连接失败"
    echo "请检查："
    echo "1. 服务器IP是否正确: ${SERVER_IP}"
    echo "2. 网络是否可达"
    echo "3. SSH服务是否运行"
    exit 1
fi
echo ""

# 测试服务器基本信息
echo "服务器信息："
ssh "${SSH_ARGS[@]}" "${SERVER_USER}@${SERVER_IP}" << 'EOF'
echo "操作系统: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "内核版本: $(uname -r)"
echo "CPU核心数: $(nproc)"
echo "内存: $(free -h | grep Mem | awk '{print $2}')"
echo "磁盘: $(df -h / | tail -1 | awk '{print $4}') 可用"
EOF

echo ""
echo "=========================================="
echo "✅ 连接测试完成"
echo "=========================================="
