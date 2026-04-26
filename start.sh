#!/bin/bash

# AI 智能助手 — 一键启动脚本

set -e

MODE="${1:-full}"  # full | gradio | backend

GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ ! -f "pyproject.toml" ]; then
    echo " 请在项目根目录运行此脚本"
    exit 1
fi

mkdir -p uploads processed templates sessions

# 虚拟环境
if [ ! -d ".venv" ]; then
    echo " 创建 Python 虚拟环境..."
    uv venv
fi
source .venv/bin/activate

# 安装依赖
echo " 检查后端依赖..."
uv pip install -e . -q

start_full() {
    # Vue 前端 + FastAPI 后端
    if [ ! -d "frontend/node_modules" ]; then
        echo " 安装前端依赖..."
        cd frontend && npm install && cd ..
    fi

    echo "${BLUE} 启动后端服务...${NC}"
    uvicorn backend.src.main:app --host 0.0.0.0 --port 8000 > /tmp/ai_agent_backend.log 2>&1 &
    BACKEND_PID=$!
    sleep 3

    if ! curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        echo " 后端启动失败"; cat /tmp/ai_agent_backend.log; exit 1
    fi
    echo "${GREEN} 后端启动成功: http://localhost:8000${NC}"

    echo "${BLUE} 启动前端服务...${NC}"
    cd frontend && npm run dev > /tmp/ai_agent_frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    sleep 5

    echo "${GREEN} 前端启动成功: http://localhost:5173${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "${GREEN} 启动完成${NC}"
    echo "  前端: http://localhost:5173"
    echo "  后端: http://localhost:8000"
    echo "  API文档: http://localhost:8000/docs"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    echo "$BACKEND_PID" > /tmp/ai_agent_backend.pid
    echo "$FRONTEND_PID" > /tmp/ai_agent_frontend.pid

    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '已停止'" SIGINT SIGTERM
    tail -f /tmp/ai_agent_backend.log
}

start_gradio() {
    echo "${BLUE} 启动 Gradio 前端...${NC}"
    python start_gradio.py
}

start_backend() {
    echo "${BLUE} 启动后端服务（仅 API）...${NC}"
    uvicorn backend.src.main:app --host 0.0.0.0 --port 8000 --reload
}

case "$MODE" in
    full)     start_full ;;
    gradio)   start_gradio ;;
    backend)  start_backend ;;
    *)
        echo "用法: $0 [full|gradio|backend]"
        echo "  full    默认：Vue 前端 + FastAPI 后端"
        echo "  gradio  启动 Gradio 前端"
        echo "  backend 仅启动后端 API"
        exit 1
        ;;
esac
