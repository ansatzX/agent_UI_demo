#!/bin/bash

# 企业合同智能助手一键启动脚本（python-docx 模式）

set -e

echo "🚀 启动企业合同智能助手（python-docx 解析模式）..."
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查是否在项目根目录
if [ ! -f "pyproject.toml" ] || [ ! -d "frontend" ]; then
    echo "❌ 请在项目根目录运行此脚本"
    exit 1
fi

# 创建必要的目录
mkdir -p uploads processed templates sessions

# 检查 Python 虚拟环境
if [ ! -d ".venv" ]; then
    echo "📦 创建 Python 虚拟环境..."
    uv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source .venv/bin/activate

# 安装后端依赖
echo "📦 检查后端依赖..."
uv pip install -e . -q

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 安装前端依赖..."
    cd frontend && npm install && cd ..
fi

# 启动后端（后台运行）
echo "${BLUE}🔧 启动后端服务（python-docx 解析模式）...${NC}"
uvicorn backend.src.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"

# 等待后端启动
echo "⏳ 等待后端启动..."
sleep 3

# 检查后端是否成功启动
if ! curl -s http://localhost:8000/docs > /dev/null; then
    echo "❌ 后端启动失败，请检查日志: /tmp/backend.log"
    cat /tmp/backend.log
    exit 1
fi

echo "${GREEN}✅ 后端启动成功: http://localhost:8000${NC}"

# 启动前端（后台运行）
echo "${BLUE}🎨 启动前端服务...${NC}"
cd frontend && npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "前端 PID: $FRONTEND_PID"

# 等待前端启动
echo "⏳ 等待前端启动..."
sleep 5

# 检查前端是否成功启动
if ! curl -s http://localhost:5173 > /dev/null; then
    echo "❌ 前端启动失败，请检查日志: /tmp/frontend.log"
    cat /tmp/frontend.log
    kill $BACKEND_PID
    exit 1
fi

echo "${GREEN}✅ 前端启动成功: http://localhost:5173${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "${GREEN}🎉 启动完成（python-docx 解析模式）！${NC}"
echo ""
echo "📱 访问地址:"
echo "   前端: http://localhost:5173"
echo "   后端: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo ""
echo "📝 日志位置:"
echo "   后端: /tmp/backend.log"
echo "   前端: /tmp/frontend.log"
echo ""
echo "🛑 停止服务: kill $BACKEND_PID $FRONTEND_PID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 保存 PID 到文件
echo "$BACKEND_PID" > /tmp/contract_agent_backend.pid
echo "$FRONTEND_PID" > /tmp/contract_agent_frontend.pid

# 保持脚本运行，显示日志
echo "按 Ctrl+C 停止所有服务..."
trap "echo ''; echo '🛑 停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '✅ 已停止'; exit 0" SIGINT SIGTERM

# 实时显示后端日志
tail -f /tmp/backend.log
