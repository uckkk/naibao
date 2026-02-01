#!/bin/bash

# 服务器初始化脚本
# 用于快速配置服务器环境

set -e

echo "=========================================="
echo "  奶宝APP - 服务器初始化脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}错误: 请使用root用户运行此脚本${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 开始初始化服务器...${NC}"
echo ""

# 1. 更新系统
echo -e "${YELLOW}[1/8] 更新系统包...${NC}"
apt update && apt upgrade -y
echo -e "${GREEN}✓ 系统更新完成${NC}"
echo ""

# 2. 安装PostgreSQL
echo -e "${YELLOW}[2/8] 安装PostgreSQL...${NC}"
apt install postgresql postgresql-contrib -y
systemctl start postgresql
systemctl enable postgresql
echo -e "${GREEN}✓ PostgreSQL安装完成${NC}"
echo ""

# 3. 配置PostgreSQL
echo -e "${YELLOW}[3/8] 配置PostgreSQL...${NC}"
read -sp "请输入数据库密码: " DB_PASSWORD
echo ""

sudo -u postgres psql <<EOF
CREATE DATABASE naibao;
CREATE USER naibao_user WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE naibao TO naibao_user;
\q
EOF

echo -e "${GREEN}✓ PostgreSQL配置完成${NC}"
echo ""

# 4. 安装Redis
echo -e "${YELLOW}[4/8] 安装Redis...${NC}"
apt install redis-server -y
systemctl start redis
systemctl enable redis
echo -e "${GREEN}✓ Redis安装完成${NC}"
echo ""

# 5. 安装Go
echo -e "${YELLOW}[5/8] 安装Go...${NC}"
if ! command -v go &> /dev/null; then
    wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
    tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
    echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
    export PATH=$PATH:/usr/local/go/bin
    rm go1.21.5.linux-amd64.tar.gz
    echo -e "${GREEN}✓ Go安装完成${NC}"
else
    echo -e "${GREEN}✓ Go已安装${NC}"
fi
echo ""

# 6. 安装Node.js（可选）
echo -e "${YELLOW}[6/8] 安装Node.js...${NC}"
read -p "是否安装Node.js? (y/n): " install_node
if [ "$install_node" = "y" ]; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt install -y nodejs
    echo -e "${GREEN}✓ Node.js安装完成${NC}"
else
    echo -e "${YELLOW}跳过Node.js安装${NC}"
fi
echo ""

# 7. 配置防火墙
echo -e "${YELLOW}[7/8] 配置防火墙...${NC}"
apt install ufw -y
ufw allow 22/tcp
ufw allow 8080/tcp
ufw --force enable
echo -e "${GREEN}✓ 防火墙配置完成${NC}"
echo ""

# 8. 创建项目目录
echo -e "${YELLOW}[8/8] 创建项目目录...${NC}"
mkdir -p /opt/naibao/{backend,frontend,database}
chmod 755 /opt/naibao
echo -e "${GREEN}✓ 项目目录创建完成${NC}"
echo ""

echo "=========================================="
echo -e "${GREEN}✓ 服务器初始化完成！${NC}"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 上传代码到 /opt/naibao/"
echo "2. 配置 .env 文件"
echo "3. 初始化数据库"
echo "4. 编译和运行后端服务"
echo ""

