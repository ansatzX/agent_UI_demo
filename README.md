# 企业合同智能助手

一个基于AI的合同智能助手，支持多文件上传、智能对话和合同审查。

## 功能特性

- 📄 **文件上传与预览** - 支持 Word 文档上传、拖放，实时预览
- 🤖 **AI智能助手** - 基于 LiteLLM 的多模型支持（支持火山引擎等）
- 📎 **多文件管理** - 同一会话支持多个文件上传和管理
- 💬 **会话持久化** - JSONL 格式存储对话历史，刷新不丢失
- 🔍 **智能审查** - AI 分析合同风险，提供专业建议
- 📋 **流程引导** - 引导用户完成合同创建和审查流程
- 💾 **本地存储** - 数据本地保存，保护隐私安全

## 技术栈

### 后端
- **Python 3.10+**
- **FastAPI** - 高性能 Web 框架
- **SQLModel** - 现代 ORM（SQLite 数据库）
- **python-docx** - Word 文档解析
- **LiteLLM** - 统一 LLM 接口（支持 OpenAI、Anthropic、火山引擎等）
- **uv** - 快速 Python 包管理

### 前端
- **Vue 3 + TypeScript** - 现代前端框架
- **Pinia** - 状态管理
- **Vite** - 快速构建工具
- **@vue-office/docx** - Word 文档预览
- **Axios** - HTTP 客户端

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- uv (Python 包管理器)
- LLM API Key（支持火山引擎、OpenAI、Anthropic 等）

### 一键启动

1. 克隆项目
```bash
cd cuhksz_demo
```

2. 配置 LLM API
```bash
cp config.example.toml config.toml
# 编辑 config.toml，填入你的 LLM API 配置
```

配置示例：
```toml
[llm]
model = "volcengine_coding_plan/doubao-pro-32k"  # 火山引擎模型

[providers.volcengine_coding_plan]
api_key = "your-api-key"
base_url = "https://ark.cn-beijing.volces.com/api/v3"
```

3. 启动应用
```bash
./start.sh
```

脚本会自动：
- 创建 Python 虚拟环境
- 安装所有依赖（前端+后端）
- 启动后端服务（http://localhost:8000）
- 启动前端服务（http://localhost:5173）

4. 访问应用
打开浏览器访问：http://localhost:5173

### 停止服务

```bash
./stop.sh
```

或者按 `Ctrl+C` 停止启动脚本

## 使用说明

1. 打开浏览器访问 http://localhost:5173
2. 在左侧聊天区域拖放 Word 文档上传
3. 与 AI 助手对话，询问合同相关问题
4. 点击消息中的文件链接查看文档
5. 右侧预览区支持缩放、下载等操作

### 文件管理

- **上传文件**：拖放 Word 文档到聊天区域
- **查看文件**：点击消息中的📎文件链接
- **多文件**：同一会话可上传多个文件
- **历史记录**：切换会话或刷新页面，文件链接依然保留

## 项目结构

```
cuhksz_demo/
├── backend/                 # Python 后端
│   ├── src/
│   │   ├── api/            # FastAPI 路由
│   │   │   ├── chat.py     # 聊天 API
│   │   │   ├── files.py    # 文件上传
│   │   │   ├── contracts.py # 合同管理
│   │   │   └── templates.py # 模板管理
│   │   ├── services/       # 业务逻辑层
│   │   │   ├── agent_service.py    # AI Agent
│   │   │   ├── llm_service.py      # LLM 调用
│   │   │   ├── session_service.py  # 会话管理
│   │   │   ├── file_service.py     # 文件处理
│   │   │   ├── contract_service.py # 合同业务
│   │   │   └── template_service.py # 模板业务
│   │   ├── models/         # SQLModel 数据模型
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── config.py       # 配置管理
│   │   └── main.py         # 应用入口
│   └── tests/              # 测试文件
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── views/
│   │   │   └── ContractWorkspace.vue  # 主界面
│   │   ├── stores/         # Pinia 状态管理
│   │   │   ├── chat.ts     # 聊天状态
│   │   │   └── contract.ts # 合同状态
│   │   ├── api/
│   │   │   └── client.ts   # API 客户端
│   │   ├── types/          # TypeScript 类型
│   │   └── main.ts         # 入口文件
│   └── ...
├── sessions/                # 会话数据（JSONL）
├── uploads/                 # 上传文件存储
├── config.example.toml      # 配置示例
├── start.py                 # 启动脚本
└── pyproject.toml           # Python 项目配置
```

## 开发指南

### 后端开发

```bash
# 安装开发依赖
uv pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black .

# 代码检查
ruff check .
```

### 前端开发

```bash
# 类型检查
npm run build

# 预览生产构建
npm run preview
```

## 主要功能

### 1. 文件上传与管理
- 支持 `.doc` 和 `.docx` 格式
- 拖放上传，实时解析
- 多文件管理
- 文件预览（支持缩放）

### 2. 智能对话
- 基于上下文的连续对话
- 文件内容智能分析
- 风险审查和建议
- 流程引导

### 3. 会话管理
- 会话持久化（JSONL 格式）
- 历史记录保留
- 多会话切换

## 技术亮点

- **LiteLLM 集成**：支持多种 LLM 提供商
- **JSONL 存储**：轻量级会话持久化
- **Vue Office**：专业文档预览
- **TypeScript**：完整类型安全
- **Pinia**：响应式状态管理

## 许可证

MIT

## 贡献

欢迎提交 Issue 和 Pull Request！
