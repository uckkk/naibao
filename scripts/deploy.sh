#!/bin/bash

# 部署脚本
# 支持SSH密钥认证和密码认证

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/lib/common.sh"

require_var "SSH_HOST"

SERVER_IP="${SERVER_IP:-${SSH_HOST}}"
SERVER_USER="${SERVER_USER:-${SSH_USER}}"
SERVER_PATH="${SERVER_PATH:-${REMOTE_BASE}}"

SSH_ARGS=(-o StrictHostKeyChecking=no -p "${SSH_PORT}")
SCP_ARGS=(-P "${SSH_PORT}")
if [ -n "${SSH_KEY}" ]; then
  SSH_ARGS+=(-i "${SSH_KEY}")
  SCP_ARGS+=(-i "${SSH_KEY}")
fi

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "  奶宝APP - 部署脚本"
echo "=========================================="
echo ""

# 检查本地文件
if [ ! -d "backend" ]; then
    echo "错误: 找不到backend目录"
    exit 1
fi

if [ ! -d "database" ]; then
echo "错误: 找不到database目录"
    exit 1
fi

echo -e "${YELLOW}准备部署到服务器: ${SERVER_IP}${NC}"
echo ""

# 1. 上传代码
echo -e "${YELLOW}[1/4] 上传代码到服务器...${NC}"
scp "${SCP_ARGS[@]}" -r "backend" "${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/"
scp "${SCP_ARGS[@]}" -r "database" "${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/"
echo -e "${GREEN}✓ 代码上传完成${NC}"
echo ""

# 2. 在服务器上执行初始化
echo -e "${YELLOW}[2/4] 在服务器上初始化...${NC}"
ssh "${SSH_ARGS[@]}" "${SERVER_USER}@${SERVER_IP}" << 'EOF'
cd /opt/naibao/backend
go mod download
EOF
echo -e "${GREEN}✓ 依赖安装完成${NC}"
echo ""

# 3. 初始化数据库
echo -e "${YELLOW}[3/4] 初始化数据库...${NC}"
read -p "是否初始化数据库? (y/n): " init_db
if [ "$init_db" = "y" ]; then
    ssh "${SSH_ARGS[@]}" "${SERVER_USER}@${SERVER_IP}" << 'EOF'
cd /opt/naibao
psql -U naibao_user -d naibao -f database/schema.sql
psql -U naibao_user -d naibao -f database/init_data.sql
EOF
    echo -e "${GREEN}✓ 数据库初始化完成${NC}"
else
    echo -e "${YELLOW}跳过数据库初始化${NC}"
fi
echo ""

# 4. 编译和启动服务
echo -e "${YELLOW}[4/4] 编译和启动服务...${NC}"
read -p "是否编译和启动服务? (y/n): " build_service
if [ "$build_service" = "y" ]; then
    ssh "${SSH_ARGS[@]}" "${SERVER_USER}@${SERVER_IP}" << 'EOF'
cd /opt/naibao/backend
go build -o naibao-server main.go
systemctl restart naibao || echo "服务未配置，请手动启动: ./naibao-server"
EOF
    echo -e "${GREEN}✓ 服务启动完成${NC}"
else
    echo -e "${YELLOW}跳过编译和启动${NC}"
fi
echo ""

echo "=========================================="
echo -e "${GREEN}✓ 部署完成！${NC}"
echo "=========================================="
echo ""
echo "服务器地址: http://${SERVER_IP}:8080"
echo ""
