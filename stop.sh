#!/bin/bash

# 停止 AI 智能助手

echo " 停止 AI 智能助手..."

if [ -f /tmp/ai_agent_backend.pid ]; then
    PID=$(cat /tmp/ai_agent_backend.pid)
    kill $PID 2>/dev/null && echo "  后端已停止 (PID: $PID)"
    rm /tmp/ai_agent_backend.pid
fi

if [ -f /tmp/ai_agent_frontend.pid ]; then
    PID=$(cat /tmp/ai_agent_frontend.pid)
    kill $PID 2>/dev/null && echo "  Vue 前端已停止 (PID: $PID)"
    rm /tmp/ai_agent_frontend.pid
fi

# 兼容旧版 PID 文件
rm -f /tmp/contract_agent_backend.pid /tmp/contract_agent_frontend.pid

# 额外清理
pkill -f "uvicorn backend.src.main" 2>/dev/null
pkill -f "vite.*frontend" 2>/dev/null
pkill -f "start_gradio" 2>/dev/null

echo "  所有服务已停止"
