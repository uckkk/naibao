#!/bin/bash

# 数据库快速配置脚本

DB_NAME="naibao"
DB_USER="postgres"

echo "=========================================="
echo "  奶宝APP - 数据库配置脚本"
echo "=========================================="
echo ""

# 检查 PostgreSQL 是否运行
echo "📦 检查 PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "❌ 错误: PostgreSQL 未安装或未在 PATH 中"
    echo "   请先安装 PostgreSQL"
    exit 1
fi

# 检查是否可以连接到 PostgreSQL
if ! psql -U $DB_USER -c "SELECT version();" &> /dev/null; then
    echo "❌ 错误: 无法连接到 PostgreSQL"
    echo "   请检查："
    echo "   1. PostgreSQL 是否运行"
    echo "   2. 用户 $DB_USER 是否存在"
    echo "   3. 是否需要密码认证"
    exit 1
fi

echo "✅ PostgreSQL 连接正常"
echo ""

# 创建数据库
echo "📦 创建数据库 $DB_NAME..."
if psql -U $DB_USER -c "CREATE DATABASE $DB_NAME;" 2>/dev/null; then
    echo "✅ 数据库创建成功"
else
    echo "⚠️  数据库已存在，跳过创建"
fi
echo ""

# 导入表结构
echo "📋 导入表结构..."
if psql -U $DB_USER -d $DB_NAME -f database/schema.sql; then
    echo "✅ 表结构导入成功"
else
    echo "❌ 表结构导入失败"
    exit 1
fi
echo ""

# 导入初始化数据
echo "📊 导入初始化数据..."
if psql -U $DB_USER -d $DB_NAME -f database/init_data.sql; then
    echo "✅ 初始化数据导入成功"
else
    echo "❌ 初始化数据导入失败"
    exit 1
fi
echo ""

# 验证数据
echo "🔍 验证数据..."
TABLE_COUNT=$(psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
STANDARD_COUNT=$(psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM health_standards;" | tr -d ' ')

echo "   表数量: $TABLE_COUNT"
echo "   卫健委标准数据: $STANDARD_COUNT 条"
echo ""

echo "=========================================="
echo "✅ 数据库配置完成！"
echo "=========================================="
echo ""
echo "📝 下一步："
echo "1. 配置后端环境变量（backend/.env）："
echo "   DB_HOST=localhost"
echo "   DB_PORT=5432"
echo "   DB_USER=$DB_USER"
echo "   DB_PASSWORD=your_postgres_password"
echo "   DB_NAME=$DB_NAME"
echo "   DB_SSLMODE=disable"
echo ""
echo "2. 启动后端服务："
echo "   cd backend"
echo "   go run main.go"
echo ""

