#!/bin/bash

# 停止企业合同智能助手

echo "🛑 停止企业合同智能助手..."

# 读取 PID 并停止服务
if [ -f /tmp/contract_agent_backend.pid ]; then
    BACKEND_PID=$(cat /tmp/contract_agent_backend.pid)
    kill $BACKEND_PID 2>/dev/null && echo "✅ 后端已停止 (PID: $BACKEND_PID)"
    rm /tmp/contract_agent_backend.pid
fi

if [ -f /tmp/contract_agent_frontend.pid ]; then
    FRONTEND_PID=$(cat /tmp/contract_agent_frontend.pid)
    kill $FRONTEND_PID 2>/dev/null && echo "✅ 前端已停止 (PID: $FRONTEND_PID)"
    rm /tmp/contract_agent_frontend.pid
fi

# 额外清理：确保所有相关进程都停止
pkill -f "uvicorn backend.src.main" 2>/dev/null
pkill -f "vite.*frontend" 2>/dev/null

echo "✅ 所有服务已停止"
