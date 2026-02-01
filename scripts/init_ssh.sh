#!/bin/bash

# SSH密钥初始化脚本

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/lib/common.sh"

require_var "SSH_HOST"

echo "=========================================="
echo "  SSH密钥配置脚本"
echo "=========================================="
echo ""
echo "目标服务器: ${SSH_USER}@${SSH_HOST}:${SSH_PORT}"

# 检查是否已有SSH密钥
if [ ! -f ~/.ssh/id_rsa ]; then
    echo "📦 生成SSH密钥对..."
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N "" -C "naibao-server"
    echo "✅ SSH密钥生成成功"
else
    echo "✅ SSH密钥已存在"
fi

echo ""

# 检查是否已添加到known_hosts
if ! grep -q "$SSH_HOST" ~/.ssh/known_hosts 2>/dev/null; then
    echo "📦 添加服务器到known_hosts..."
    ssh-keyscan -H -p "${SSH_PORT}" "${SSH_HOST}" >> ~/.ssh/known_hosts 2>/dev/null
    echo "✅ 服务器已添加到known_hosts"
else
    echo "✅ 服务器已在known_hosts中"
fi

echo ""

# 复制公钥到服务器（优先非交互；否则回退到交互式 ssh-copy-id）
if command -v sshpass &> /dev/null && [ -n "${SSH_PASSWORD}" ]; then
    echo "📦 使用sshpass复制公钥到服务器..."
    sshpass -p "${SSH_PASSWORD}" ssh-copy-id -o StrictHostKeyChecking=no -p "${SSH_PORT}" "${SSH_USER}@${SSH_HOST}"
    echo "✅ 公钥已复制到服务器"
elif command -v expect &> /dev/null && [ -n "${SSH_PASSWORD}" ]; then
    echo "📦 使用expect复制公钥到服务器..."
    expect << EOF
spawn ssh-copy-id -o StrictHostKeyChecking=no -p ${SSH_PORT} ${SSH_USER}@${SSH_HOST}
expect {
    "password:" {
        send "${SSH_PASSWORD}\r"
        exp_continue
    }
    eof
}
EOF
    echo "✅ 公钥已复制到服务器"
elif command -v ssh-copy-id &> /dev/null; then
    echo "📦 使用 ssh-copy-id（交互式）复制公钥到服务器..."
    echo "   如需自动化，可在 scripts/.env.local 中设置 SSH_PASSWORD（不推荐）。"
    ssh-copy-id -o StrictHostKeyChecking=no -p "${SSH_PORT}" "${SSH_USER}@${SSH_HOST}"
    echo "✅ 公钥已复制到服务器"
else
    echo "⚠️  未找到 ssh-copy-id/sshpass/expect，请手动复制公钥："
    echo ""
    echo "方法1：手动复制"
    echo "  1. 复制公钥内容："
    echo "     cat ~/.ssh/id_rsa.pub"
    echo ""
    echo "  2. SSH连接到服务器："
    echo "     ssh -p ${SSH_PORT} ${SSH_USER}@${SSH_HOST}"
    echo ""
    echo "  3. 在服务器上执行："
    echo "     mkdir -p ~/.ssh"
    echo "     chmod 700 ~/.ssh"
    echo "     echo '你的公钥内容' >> ~/.ssh/authorized_keys"
    echo "     chmod 600 ~/.ssh/authorized_keys"
    echo ""
fi

echo ""
echo "=========================================="
echo "✅ SSH密钥配置完成！"
echo "=========================================="
echo ""
echo "📝 测试连接："
echo "  ssh -p ${SSH_PORT} ${SSH_USER}@${SSH_HOST}"
echo ""
