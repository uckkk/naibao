#!/bin/bash

# 启动后端服务脚本

cd /opt/naibao/backend

# 设置Go环境
export PATH=$PATH:/usr/local/go/bin
export GOPROXY=https://goproxy.cn,direct
export GO111MODULE=on

# 检查服务是否已运行
if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "服务已在运行 (PID: $PID)"
        exit 0
    fi
fi

# 启动服务
echo "启动后端服务..."
nohup ./naibao-server > server.log 2>&1 &
echo $! > server.pid

sleep 2

# 检查服务状态
if ps -p $(cat server.pid) > /dev/null 2>&1; then
    echo "✅ 服务启动成功 (PID: $(cat server.pid))"
    echo "查看日志: tail -f server.log"
else
    echo "❌ 服务启动失败"
    echo "查看错误日志:"
    tail -20 server.log
    exit 1
fi


