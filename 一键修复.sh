#!/bin/bash

# 一键修复脚本 - 自动修复CORS配置并重启服务
# 使用方法：在服务器上运行此脚本

echo "=========================================="
echo "  一键修复后端服务"
echo "=========================================="
echo ""

cd /opt/naibao/backend

# 1. 停止服务
echo "📦 [1/4] 停止服务..."
if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        sleep 2
        echo "✅ 服务已停止"
    fi
else
    echo "⚠️  未找到PID文件，尝试查找进程..."
    pkill -f naibao-server || echo "未找到运行中的服务"
fi

# 2. 修复CORS配置
echo ""
echo "🔧 [2/4] 修复CORS配置..."
if [ -f router/middleware/cors.go ]; then
    # 备份原文件
    cp router/middleware/cors.go router/middleware/cors.go.bak
    
    # 修复CORS配置
    sed -i 's/Access-Control-Allow-Credentials", "true"/Access-Control-Allow-Credentials", "false"/' router/middleware/cors.go
    
    # 验证修改
    if grep -q 'Access-Control-Allow-Credentials", "false"' router/middleware/cors.go; then
        echo "✅ CORS配置已修复"
    else
        echo "⚠️  自动修复失败，需要手动编辑"
        echo "请编辑文件：nano router/middleware/cors.go"
        echo "将第17行的 true 改为 false"
        exit 1
    fi
else
    echo "❌ 找不到CORS配置文件"
    exit 1
fi

# 3. 重新编译
echo ""
echo "🔨 [3/4] 重新编译..."
export PATH=$PATH:/usr/local/go/bin
export GOPROXY=https://goproxy.cn,direct
export GO111MODULE=on

if go build -o naibao-server main.go; then
    echo "✅ 编译成功"
else
    echo "❌ 编译失败"
    exit 1
fi

# 4. 启动服务
echo ""
echo "🚀 [4/4] 启动服务..."
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

# 5. 测试服务
echo ""
echo "🧪 测试服务..."
sleep 1
if curl -s http://127.0.0.1:8080/health | grep -q "ok"; then
    echo "✅ 服务运行正常"
else
    echo "⚠️  服务可能有问题，请检查日志"
fi

echo ""
echo "=========================================="
echo "✅ 修复完成！"
echo "=========================================="
echo ""
echo "📝 重要提醒："
echo "   如果外部仍无法访问，请检查腾讯云安全组："
echo "   1. 登录腾讯云控制台"
echo "   2. 云服务器 → 安全组"
echo "   3. 添加入站规则：TCP:8080，来源：0.0.0.0/0"
echo ""
echo "📋 查看日志：tail -f server.log"
echo "📋 查看进程：ps aux | grep naibao-server"
echo ""


