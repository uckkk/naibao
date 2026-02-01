#!/bin/bash

# 停止后端服务脚本

cd /opt/naibao/backend

if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "停止服务 (PID: $PID)..."
        kill $PID
        sleep 1
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID
        fi
        rm -f server.pid
        echo "✅ 服务已停止"
    else
        echo "服务未运行"
        rm -f server.pid
    fi
else
    echo "PID文件不存在，服务可能未运行"
fi


