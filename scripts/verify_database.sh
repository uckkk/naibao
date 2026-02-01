#!/bin/bash

# 数据库验证脚本
# 用于验证服务器上的数据库是否创建成功

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/lib/common.sh"

require_var "SSH_HOST"

# 兼容旧变量名（优先使用环境变量 SERVER_*，否则使用 SSH_*）
SERVER_IP="${SERVER_IP:-${SSH_HOST}}"
SERVER_USER="${SERVER_USER:-${SSH_USER}}"
SERVER_PORT="${SERVER_PORT:-${SSH_PORT}}"
SERVER_PASSWORD="${SERVER_PASSWORD:-${SSH_PASSWORD}}"

echo "=========================================="
echo "  数据库验证脚本"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SSH_OPTS=(-o StrictHostKeyChecking=no -p "${SERVER_PORT}")

# 检查 sshpass（仅当提供了 SERVER_PASSWORD/SSH_PASSWORD 时才启用非交互）
if command -v sshpass &> /dev/null && [ -n "${SERVER_PASSWORD}" ]; then
    SSH_CMD=(sshpass -p "${SERVER_PASSWORD}" ssh)
else
    if [ -n "${SERVER_PASSWORD}" ]; then
        echo -e "${YELLOW}⚠️  已设置密码但未安装 sshpass：将使用交互式 SSH 输入密码（推荐改用密钥认证）${NC}"
        echo ""
    fi
    SSH_CMD=(ssh)
fi

# 1. 测试SSH连接
echo -e "${YELLOW}[1/6] 测试SSH连接...${NC}"
if "${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" "echo 'SSH连接成功'"; then
    echo -e "${GREEN}✅ SSH连接成功${NC}"
else
    echo -e "${RED}❌ SSH连接失败${NC}"
    echo "请检查："
    echo "1. 服务器IP是否正确: ${SERVER_IP}"
    echo "2. 网络是否可达"
    echo "3. SSH服务是否运行"
    echo "4. 如果服务器只支持密钥认证，请先配置SSH密钥"
    exit 1
fi
echo ""

# 2. 检查PostgreSQL服务
echo -e "${YELLOW}[2/6] 检查PostgreSQL服务...${NC}"
PG_STATUS=$("${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" "systemctl is-active postgresql 2>/dev/null || service postgresql status 2>/dev/null | grep -q 'active' && echo 'active' || echo 'inactive'")
if [ "$PG_STATUS" = "active" ]; then
    echo -e "${GREEN}✅ PostgreSQL服务运行中${NC}"
else
    echo -e "${RED}❌ PostgreSQL服务未运行${NC}"
    echo "尝试启动PostgreSQL..."
    "${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" "systemctl start postgresql 2>/dev/null || service postgresql start 2>/dev/null"
    sleep 2
    PG_STATUS=$("${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" "systemctl is-active postgresql 2>/dev/null || echo 'inactive'")
    if [ "$PG_STATUS" = "active" ]; then
        echo -e "${GREEN}✅ PostgreSQL已启动${NC}"
    else
        echo -e "${RED}❌ PostgreSQL启动失败，请手动检查${NC}"
    fi
fi
echo ""

# 3. 检查数据库是否存在
echo -e "${YELLOW}[3/6] 检查数据库naibao...${NC}"
DB_EXISTS=$("${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" "sudo -u postgres psql -l 2>/dev/null | grep -q 'naibao' && echo 'yes' || echo 'no'")
if [ "$DB_EXISTS" = "yes" ]; then
    echo -e "${GREEN}✅ 数据库naibao存在${NC}"
else
    echo -e "${RED}❌ 数据库naibao不存在${NC}"
    echo "需要创建数据库，运行以下命令："
    echo "  ssh -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP}"
    echo "  sudo -u postgres psql -c 'CREATE DATABASE naibao;'"
    exit 1
fi
echo ""

# 4. 检查表数量
echo -e "${YELLOW}[4/6] 检查数据库表...${NC}"
TABLE_COUNT=$("${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" "sudo -u postgres psql -d naibao -t -c 'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '\''public'\'';' 2>/dev/null" | tr -d ' ')
if [ -n "$TABLE_COUNT" ] && [ "$TABLE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ 找到 $TABLE_COUNT 个表${NC}"
else
    echo -e "${RED}❌ 数据库中没有表，需要导入schema.sql${NC}"
    echo "运行以下命令导入表结构："
    echo "  scp -P ${SERVER_PORT} database/schema.sql ${SERVER_USER}@${SERVER_IP}:/tmp/"
    echo "  ssh -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP} 'sudo -u postgres psql -d naibao -f /tmp/schema.sql'"
    exit 1
fi
echo ""

# 5. 检查关键表
echo -e "${YELLOW}[5/6] 检查关键表...${NC}"
KEY_TABLES=("formula_brands" "health_standards" "feeding_settings" "users" "babies" "feedings")
MISSING_TABLES=()

for table in "${KEY_TABLES[@]}"; do
    EXISTS=$("${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" "sudo -u postgres psql -d naibao -t -c 'SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '\''${table}'\'';' 2>/dev/null" | tr -d ' ')
    if [ "$EXISTS" = "1" ]; then
        echo -e "${GREEN}  ✅ ${table}${NC}"
    else
        echo -e "${RED}  ❌ ${table} 不存在${NC}"
        MISSING_TABLES+=("$table")
    fi
done

if [ ${#MISSING_TABLES[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}缺少以下表: ${MISSING_TABLES[*]}${NC}"
    echo "需要导入schema.sql"
fi
echo ""

# 6. 检查初始化数据
echo -e "${YELLOW}[6/6] 检查初始化数据...${NC}"

# 检查奶粉品牌数据
BRAND_COUNT=$("${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" "sudo -u postgres psql -d naibao -t -c 'SELECT COUNT(*) FROM formula_brands;' 2>/dev/null" | tr -d ' ')
if [ -n "$BRAND_COUNT" ] && [ "$BRAND_COUNT" -gt 0 ]; then
    echo -e "${GREEN}  ✅ 奶粉品牌数据: $BRAND_COUNT 条${NC}"
else
    echo -e "${RED}  ❌ 奶粉品牌数据为空，需要导入init_data.sql${NC}"
fi

# 检查卫健委标准数据
STANDARD_COUNT=$("${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" "sudo -u postgres psql -d naibao -t -c 'SELECT COUNT(*) FROM health_standards;' 2>/dev/null" | tr -d ' ')
if [ -n "$STANDARD_COUNT" ] && [ "$STANDARD_COUNT" -gt 0 ]; then
    echo -e "${GREEN}  ✅ 卫健委标准数据: $STANDARD_COUNT 条${NC}"
else
    echo -e "${RED}  ❌ 卫健委标准数据为空，需要导入init_data.sql${NC}"
fi
echo ""

# 总结
echo "=========================================="
if [ "$DB_EXISTS" = "yes" ] && [ -n "$TABLE_COUNT" ] && [ "$TABLE_COUNT" -gt 0 ] && [ ${#MISSING_TABLES[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ 数据库验证通过！${NC}"
    echo ""
    echo "数据库状态："
    echo "  - 数据库: naibao ✅"
    echo "  - 表数量: $TABLE_COUNT ✅"
    echo "  - 奶粉品牌: ${BRAND_COUNT:-0} 条"
    echo "  - 卫健委标准: ${STANDARD_COUNT:-0} 条"
    echo ""
    if [ -z "$BRAND_COUNT" ] || [ "$BRAND_COUNT" -eq 0 ] || [ -z "$STANDARD_COUNT" ] || [ "$STANDARD_COUNT" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  建议导入初始化数据：${NC}"
        echo "  scp -P ${SERVER_PORT} database/init_data.sql ${SERVER_USER}@${SERVER_IP}:/tmp/"
        echo "  ssh -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP} 'sudo -u postgres psql -d naibao -f /tmp/init_data.sql'"
    fi
else
    echo -e "${RED}❌ 数据库验证失败${NC}"
    echo ""
    echo "需要执行的操作："
    if [ "$DB_EXISTS" != "yes" ]; then
        echo "1. 创建数据库"
    fi
    if [ -z "$TABLE_COUNT" ] || [ "$TABLE_COUNT" -eq 0 ]; then
        echo "2. 导入表结构 (schema.sql)"
    fi
    if [ ${#MISSING_TABLES[@]} -gt 0 ]; then
        echo "3. 导入缺失的表"
    fi
    if [ -z "$BRAND_COUNT" ] || [ "$BRAND_COUNT" -eq 0 ] || [ -z "$STANDARD_COUNT" ] || [ "$STANDARD_COUNT" -eq 0 ]; then
        echo "4. 导入初始化数据 (init_data.sql)"
    fi
fi
echo "=========================================="
