# 企业合同智能助手

智能合同生成系统：上传模板 → AI 识别占位符 → 动态表单填充 → 一键生成合同

## ✨ 核心功能

- **🎯 智能合同生成** - 上传 Word 模板，AI 自动识别 `{{占位符}}`，弹出动态表单，填写后生成合同
- **📄 文档实时预览** - 拖放上传 .docx 文档，右侧即时预览，支持缩放、下载、多文件管理
- **🤖 AI 智能对话** - 基于上下文的连续对话，记忆上传文件和表单数据，工具调用（show_form、generate_document）
- **💾 会话持久化** - JSONL 格式存储，刷新页面不丢失历史对话和文件
- **🎨 动态表单 (A2UI)** - 根据模板占位符自动生成表单界面，支持文本、数字、日期等多种字段类型

## 🏗️ 技术架构

### 后端
- **FastAPI** - 高性能异步 Web 框架
- **ReAct Agent** - OpenAI 原生 function calling 协议
- **python-docx** - Word 文档解析与生成
- **LiteLLM** - 统一 LLM 接口（支持火山引擎、OpenAI、Anthropic 等）
- **JSONL Session** - 轻量级会话持久化

### 前端
- **Vue 3 + TypeScript** - 现代响应式框架，完整类型安全
- **Pinia** - 状态管理（chat、contract stores）
- **@vue-office/docx** - 专业 Word 文档预览
- **DynamicForm** - 动态表单组件（A2UI）

### 工具系统
- **show_form** - 向用户显示动态表单，收集占位符字段
- **generate_document** - 基于模板和表单数据生成合同文档
- **read_file** - 读取文件内容（可选）

## 🚀 一键安装与启动

### 前置要求

- Python 3.10+
- Node.js 18+
- uv（Python 包管理器）：`pip install uv`
- LLM API Key（火山引擎 / OpenAI / Anthropic）

### 步骤 1：克隆项目

```bash
git clone https://github.com/ansatzX/agent_UI_demo.git
cd agent_UI_demo
```

### 步骤 2：配置 LLM API

```bash
cp config.example.toml config.toml
```

编辑 `config.toml`，填入你的 LLM API 配置：

```toml
[llm]
model = "volcengine_coding_plan/doubao-pro-32k"

[providers.volcengine_coding_plan]
api_key = "your-api-key-here"
base_url = "https://ark.cn-beijing.volces.com/api/v3"
```

### 步骤 3：一键启动

```bash
chmod +x start.sh
./start.sh
```

启动脚本会自动：
- ✅ 创建 Python 虚拟环境（`.venv/`）
- ✅ 安装后端依赖（`uv pip install`）
- ✅ 安装前端依赖（`npm install`）
- ✅ 创建必要目录（`uploads/`、`sessions/`、`templates/`）
- ✅ 启动后端服务（http://localhost:8000）
- ✅ 启动前端服务（http://localhost:5173）

### 步骤 4：访问应用

打开浏览器访问：**http://localhost:5173**

## 📖 使用指南

### 智能合同生成流程

1. **上传模板** - 在左侧聊天区拖放 Word 模板文件（`.docx` 格式）
2. **触发识别** - 发送消息如"帮我填写这份模板"或"生成合同"
3. **填写表单** - AI 识别占位符后，会弹出动态表单（如 `{{甲方}}`、`{{乙方}}`、`{{合同编号}}`）
4. **生成合同** - 填写表单并提交，AI 自动生成填充完成的合同文档
5. **预览下载** - 点击 **👁️ 预览** 按钮在右侧查看，或点击 **⬇️ 下载** 按钮下载文件

### 文件管理

- **上传文件**：拖放 `.docx` 文档到聊天区域
- **查看文件**：点击消息中的 📎 文件链接
- **多文件支持**：同一会话可上传多个文件，历史记录保留
- **预览操作**：右侧预览区支持缩放（50%-200%）、下载、删除

### 会话管理

- **历史会话**：左侧面板显示所有历史会话，点击切换
- **新建会话**：点击"+ 新对话"按钮
- **删除会话**：点击会话右侧的 🗑️ 按钮

## 🛠️ 项目结构

```
cuhksz_demo/
├── backend/                    # Python 后端
│   ├── src/
│   │   ├── api/               # FastAPI 路由
│   │   │   ├── chat.py        # 聊天 API + /submit-form
│   │   │   ├── files.py       # 文件上传/下载/预览
│   │   │   ├── contracts.py   # 合同管理
│   │   │   └── templates.py   # 模板管理
│   │   ├── services/          # 业务逻辑层
│   │   │   ├── agent_service.py       # Agent 主服务（handle_message, handle_form_submission）
│   │   │   ├── react_agent.py         # ReAct Agent（OpenAI function calling）
│   │   │   ├── llm_service.py         # LLM 调用（generate_react_response）
│   │   │   ├── session_service.py     # JSONL 会话管理
│   │   │   ├── file_service.py        # 文件解析（python-docx）
│   │   │   ├── doc_generator.py       # 文档生成（fill_template_simple）
│   │   │   └── tools/                 # 工具系统
│   │   │       ├── show_form.py       # 动态表单工具
│   │   │       └── generate_document.py # 文档生成工具
│   │   ├── models/            # SQLModel 数据模型
│   │   ├── schemas/           # Pydantic schemas
│   │   └── main.py            # 应用入口（lifespan 初始化）
│   └── tests/                 # 测试文件
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── views/
│   │   │   └── ContractWorkspace.vue  # 主界面（聊天 + 预览 + 会话列表）
│   │   ├── components/
│   │   │   └── DynamicForm.vue        # 动态表单组件（A2UI）
│   │   ├── stores/
│   │   │   ├── chat.ts        # 聊天状态（sendMessage, submitForm）
│   │   │   └── contract.ts    # 合同状态
│   │   ├── api/
│   │   │   └── client.ts      # API 客户端（chatApi, fileApi）
│   │   └── types/             # TypeScript 类型
│   │       ├── index.ts       # Message 联合类型
│   │       └── form.ts        # FormDefinition, FormField
│   └── ...
├── sessions/                   # JSONL 会话数据
├── uploads/                    # 上传和生成的文件
├── config.example.toml         # LLM API 配置示例
├── start.sh                    # 一键启动脚本
├── stop.sh                     # 停止服务脚本
└── pyproject.toml              # Python 项目配置
```

## 🔧 开发指南

### 后端开发

```bash
# 安装开发依赖
uv pip install -e ".[dev]"

# 激活虚拟环境
source .venv/bin/activate

# 运行测试
pytest

# 代码格式化
black .

# 代码检查
ruff check .

# 手动启动后端（开发模式）
uvicorn backend.src.main:app --reload
```

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 类型检查
npm run build

# 预览生产构建
npm run preview
```

## 🎯 核心工作流

### 1. 上传模板 → AI 识别占位符

```
用户：拖放 "合同模板.docx"（包含 {{甲方}}、{{乙方}}、{{合同编号}}）
AI：识别到合同模板，调用 show_form 工具
前端：渲染动态表单
```

### 2. 填写表单 → 生成合同

```
用户：填写表单字段（甲方="ABC公司"，乙方="XYZ公司"，合同编号="2024-001"）
AI：接收表单数据，调用 generate_document 工具
后端：使用 python-docx 替换占位符，生成唯一文件名（20260417_061830_abc123_合同.docx）
前端：显示下载/预览按钮
```

### 3. 预览/下载生成的合同

```
用户：点击 "👁️ 预览" 按钮
前端：右侧文档预览区渲染生成的 .docx 文件
用户：点击 "⬇️ 下载" 按钮
浏览器：下载文件（友好名："合同.docx"）
```

## 🔍 技术亮点

### ReAct Agent + OpenAI Function Calling

- **原生协议**：直接使用 `message.tool_calls`，无需 regex 解析
- **工具累积**：多轮工具调用后保留所有 `tool_results`
- **上下文记忆**：从 session 恢复文件 + 传入历史消息

### 动态表单 (A2UI)

- **自动识别**：从 `{{占位符}}` 自动生成表单字段
- **类型推断**：文本、数字、日期、下拉选择
- **必填校验**：`required` 字段标记

### 文档生成

- **python-docx**：直接替换占位符，无需模板引擎
- **唯一文件名**：时间戳 + UUID 前缀，避免覆盖
- **双按钮**：预览（VueOfficeDocx）+ 下载（URL 下载）

## 📝 配置说明

### LLM API 配置（config.toml）

```toml
[llm]
model = "volcengine_coding_plan/doubao-pro-32k"  # 火山引擎豆包模型

[providers.volcengine_coding_plan]
api_key = "your-api-key"
base_url = "https://ark.cn-beijing.volces.com/api/v3"
```

支持其他提供商：
- OpenAI: `model = "openai/gpt-4"`
- Anthropic: `model = "anthropic/claude-3-sonnet"`

### 文件上传限制

- 仅支持 `.docx` 格式（不支持 `.doc`）
- 最大文件大小：200MB
- 存储位置：`uploads/` 目录

## 🛑 停止服务

```bash
./stop.sh
```

或按 `Ctrl+C` 停止启动脚本

## 📄 许可证

MIT

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**Made with ❤️ for enterprise contract automation**
