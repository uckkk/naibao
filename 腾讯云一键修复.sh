#!/bin/bash

# 腾讯云 Cloud Shell 一键修复脚本
# 直接在腾讯云控制台的 Cloud Shell 中执行此脚本

echo "=========================================="
echo "  奶宝后端服务一键修复"
echo "=========================================="
echo ""

# 检查是否在服务器上
if [ ! -d "/opt/naibao/backend" ]; then
    echo "❌ 错误：未找到后端目录"
    echo "请确保在服务器上执行此脚本"
    exit 1
fi

cd /opt/naibao/backend

# 1. 停止服务
echo "📦 [1/5] 停止服务..."
if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        sleep 2
        echo "✅ 服务已停止 (PID: $PID)"
    else
        echo "⚠️  进程不存在，尝试查找..."
        pkill -f naibao-server 2>/dev/null && echo "✅ 已停止" || echo "⚠️  未找到运行中的服务"
    fi
else
    echo "⚠️  未找到PID文件，尝试停止进程..."
    pkill -f naibao-server 2>/dev/null && echo "✅ 已停止" || echo "⚠️  未找到运行中的服务"
fi

# 2. 备份并修复CORS配置
echo ""
echo "🔧 [2/5] 修复CORS配置..."
if [ -f router/middleware/cors.go ]; then
    # 备份原文件
    cp router/middleware/cors.go router/middleware/cors.go.bak.$(date +%Y%m%d_%H%M%S)
    echo "✅ 已备份原文件"
    
    # 修复CORS配置 - 多种方式尝试
    sed -i 's/Access-Control-Allow-Credentials", "true"/Access-Control-Allow-Credentials", "false"/' router/middleware/cors.go
    
    # 验证修改
    if grep -q 'Access-Control-Allow-Credentials", "false"' router/middleware/cors.go; then
        echo "✅ CORS配置已修复"
    else
        # 如果sed失败，尝试直接替换
        echo "⚠️  尝试其他方式修复..."
        sed -i 's/true/false/' router/middleware/cors.go
        if grep -q 'Access-Control-Allow-Credentials", "false"' router/middleware/cors.go; then
            echo "✅ CORS配置已修复（方式2）"
        else
            echo "❌ 自动修复失败"
            echo "请手动编辑：nano router/middleware/cors.go"
            echo "将第17行的 true 改为 false"
            exit 1
        fi
    fi
else
    echo "❌ 找不到CORS配置文件"
    exit 1
fi

# 3. 设置Go环境
echo ""
echo "⚙️  [3/5] 设置Go环境..."
export PATH=$PATH:/usr/local/go/bin
export GOPROXY=https://goproxy.cn,direct
export GO111MODULE=on

# 检查Go是否可用
if ! command -v go &> /dev/null; then
    echo "❌ Go未安装或不在PATH中"
    echo "尝试查找Go..."
    if [ -f "/usr/local/go/bin/go" ]; then
        export PATH=$PATH:/usr/local/go/bin
    else
        echo "❌ 找不到Go，请先安装Go"
        exit 1
    fi
fi

echo "✅ Go环境已设置 (版本: $(go version | awk '{print $3}'))"

# 4. 重新编译
echo ""
echo "🔨 [4/5] 重新编译..."
if go build -o naibao-server main.go; then
    echo "✅ 编译成功"
    ls -lh naibao-server
else
    echo "❌ 编译失败"
    echo "查看错误信息："
    go build -o naibao-server main.go 2>&1 | head -20
    exit 1
fi

# 5. 启动服务
echo ""
echo "🚀 [5/5] 启动服务..."
nohup ./naibao-server > server.log 2>&1 &
NEW_PID=$!
echo $NEW_PID > server.pid

sleep 3

# 检查服务状态
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "✅ 服务启动成功 (PID: $NEW_PID)"
else
    echo "❌ 服务启动失败"
    echo "查看错误日志："
    tail -30 server.log
    exit 1
fi

# 6. 测试服务
echo ""
echo "🧪 测试服务..."
sleep 2

# 测试健康检查
HEALTH_RESPONSE=$(curl -s http://127.0.0.1:8080/health 2>&1)
if echo "$HEALTH_RESPONSE" | grep -q "ok"; then
    echo "✅ 健康检查通过"
    echo "   响应: $HEALTH_RESPONSE"
else
    echo "⚠️  健康检查异常"
    echo "   响应: $HEALTH_RESPONSE"
fi

# 检查CORS头
echo ""
echo "🔍 检查CORS配置..."
CORS_HEADERS=$(curl -s -I http://127.0.0.1:8080/health 2>&1 | grep -i "access-control")
echo "$CORS_HEADERS"

if echo "$CORS_HEADERS" | grep -q "Access-Control-Allow-Credentials: false"; then
    echo "✅ CORS配置正确"
else
    echo "⚠️  CORS配置可能仍有问题"
fi

# 7. 检查端口监听
echo ""
echo "🔍 检查端口监听..."
netstat -tlnp | grep 8080 || ss -tlnp | grep 8080

# 8. 检查防火墙
echo ""
echo "🔍 检查防火墙..."
if command -v ufw &> /dev/null; then
    echo "UFW状态："
    ufw status | grep 8080 || echo "⚠️  8080端口未在UFW规则中"
elif command -v firewall-cmd &> /dev/null; then
    echo "Firewalld状态："
    firewall-cmd --list-ports | grep 8080 || echo "⚠️  8080端口未在Firewalld规则中"
else
    echo "⚠️  未找到防火墙管理工具"
fi

echo ""
echo "=========================================="
echo "✅ 修复完成！"
echo "=========================================="
echo ""
echo "📝 重要提醒："
echo ""
echo "1. ✅ 服务器端修复已完成"
echo ""
echo "2. ⚠️  如果外部仍无法访问，请配置腾讯云安全组："
echo "   - 登录腾讯云控制台"
echo "   - 云服务器 → 实例 → 找到您的服务器"
echo "   - 点击「安全组」标签"
echo "   - 点击安全组名称"
echo "   - 「入站规则」→「添加规则」"
echo "   - 类型：自定义"
echo "   - 来源：0.0.0.0/0"
echo "   - 协议端口：TCP:8080"
echo "   - 策略：允许"
echo "   - 点击「完成」"
echo ""
echo "3. 🧪 测试外部访问："
echo "   在浏览器打开：http://<API_HOST>:8080/health"
echo "   应该看到：{\"status\":\"ok\"}"
echo ""
echo "4. 📋 常用命令："
echo "   查看日志：tail -f /opt/naibao/backend/server.log"
echo "   查看进程：ps aux | grep naibao-server"
echo "   停止服务：cd /opt/naibao/backend && ./stop_server.sh"
echo "   重启服务：cd /opt/naibao/backend && ./start_server.sh"
echo ""

