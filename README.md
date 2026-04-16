# 企业技术合同智能助手

一个基于AI的合同智能助手，帮助甲方用户完成服务采购和框架协议的全流程管理。

## 功能特性

- 📄 **Word模板解析** - 自动识别合同模板中的可填写字段
- 🤖 **AI智能助手** - 自然语言对话，提供专业建议
- ✏️ **智能填充** - 对话式引导填写合同内容
- 🔍 **风险审查** - AI分析合同风险，提供修改建议
- 📋 **流程解释** - 详细说明合同审批流程
- 💾 **本地存储** - 数据本地保存，保护隐私

## 技术栈

### 后端
- Python 3.10+
- FastAPI - Web框架
- SQLModel - ORM
- SQLite - 数据库
- python-docx/docxtpl - Word处理
- LiteLLM - 统一LLM接口
- uv - 包管理

### 前端
- Vue 3 + TypeScript
- Pinia - 状态管理
- Vite - 构建工具
- Axios - HTTP客户端

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- uv (Python包管理)
- Anthropic API Key

### 后端设置

1. 克隆项目并进入目录
```bash
cd cuhksz_demo
```

2. 使用uv创建虚拟环境并安装依赖
```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 ANTHROPIC_API_KEY
```

4. 启动后端服务
```bash
cd backend
uv run python -m backend.src.main
```

后端将在 http://localhost:8000 启动

### 前端设置

1. 打开新终端，进入frontend目录
```bash
cd frontend
```

2. 安装依赖
```bash
npm install
```

3. 启动开发服务器
```bash
npm run dev
```

前端将在 http://localhost:5173 启动

## 使用说明

1. 打开浏览器访问 http://localhost:5173
2. AI助手会主动问候并提供操作选项
3. 与AI对话开始使用合同管理功能

## 项目结构

```
cuhksz_demo/
├── backend/                 # Python后端
│   ├── src/
│   │   ├── api/            # API路由
│   │   ├── services/       # 业务逻辑
│   │   ├── models/         # 数据模型
│   │   └── schemas/        # Pydantic schemas
│   └── tests/              # 测试
├── frontend/                # Vue前端
│   ├── src/
│   │   ├── components/     # Vue组件
│   │   ├── stores/         # Pinia状态管理
│   │   ├── views/          # 页面视图
│   │   └── api/            # API客户端
│   └── ...
├── docs/                    # 文档
│   └── superpowers/
│       ├── specs/          # 设计文档
│       └── plans/          # 实施计划
└── ...
```

## 开发

### 后端开发

```bash
# 安装开发依赖
uv pip install -e ".[dev]"

# 运行测试
uv run pytest
```

### 前端开发

```bash
# 类型检查
npm run build

# 预览生产构建
npm run preview
```

## License

MIT
