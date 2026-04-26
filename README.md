# AI 智能助手

通用 AI Agent 框架 + 企业合同智能 + 信息采集 多引擎系统

##  核心功能

###  场景一：智能合同生成

**完整流程**：上传模板 → AI 识别占位符 → 动态表单填充 → 一键生成合同 → 主动引导下一步

- **智能识别** - 上传 Word 模板，AI 自动识别 `{{占位符}}` 并生成动态表单
- **一键生成** - 填写表单后自动生成合同文档，支持预览和下载
- **主动引导** - 完成后主动询问："您是否需要了解合同审批流程？是否需要我为您填充合同？"
- **流程解释** - 提供合同审批、签署、立项、资金到账等流程的智能解释

###  场景二：智能写作助手

**完整流程**：收集素材 → 调用写作工具 → 生成文章 → 支持多种输出格式

- **多源素材** - 支持用户上传文档、提供 URL（自动爬取网页）、直接输入信息
- **写作类型** - 项目总结报告、产研合作新闻稿、公众号推文、通用文章
- **风格定制** - 正式、轻松、学术、活泼四种风格可选
- **多格式输出** - Markdown 文章、纯文本、幻灯片大纲（Slide Outline）

###  文档管理与预览

- **实时预览** - 拖放上传 .docx 文档，右侧即时预览，支持缩放（50%-200%）
- **多文件管理** - 同一会话支持多个文件上传和管理
- **会话持久化** - JSONL 格式存储，刷新页面不丢失历史对话和文件

###  信息采集（即将上线）

- **知乎信息收集** - 通过 MCP 协议接入知乎平台，支持关键词搜索、热门内容采集
- **网页信息获取** - 直接在对话中使用 read_webpage 工具爬取网页内容
- **信息汇总报告** - 自动整理归纳采集信息，生成结构化报告

## ️ 技术架构

### 通用 Agent 框架（agent_framework）
- **ReAct Agent** - 可配置 system prompt 的通用推理-行动循环
- **LLM Service** - 基于 LiteLLM 的多 Provider 抽象（火山引擎、OpenAI、Anthropic 等）
- **Tool Registry** - 通用工具注册与执行引擎
- **Session Service** - JSONL 轻量级会话持久化
- **MCP Bridge** - 多 MCP 服务器管理器（预留知乎、文档处理等扩展）

### 后端（合同领域）
- **FastAPI** - 高性能异步 Web 框架
- **ReAct Agent** - OpenAI 原生 function calling 协议
- **python-docx** - Word 文档解析与生成
- **JSONL Session** - 轻量级会话持久化
- **MCP Bridge** - 多 MCP 服务器连接管理

### 前端
- **Vue 3 + TypeScript** - 现代响应式框架，完整类型安全（Web 端）
- **Gradio** - Python 原生交互界面（快速原型端）
- **Pinia** - 状态管理（chat、contract stores）
- **@vue-office/docx** - 专业 Word 文档预览
- **DynamicForm** - 动态表单组件（A2UI）

### 工具系统
- **show_form** - 向用户显示动态表单，收集占位符字段
- **generate_document** - 基于模板和表单数据生成合同文档
- **read_file** - 读取文件内容（可选）
- **read_webpage** - 爬取网页内容，提取文本用于写作素材
- **write_article** - 根据主题和素材生成文章、报告、新闻稿等

##  一键安装与启动

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

### 步骤 3：安装依赖

```bash
# Python 依赖
uv pip install -e ". 

# 前端依赖（Vue）
cd frontend && npm install && cd ..
```

### 步骤 4：启动

**方式一：Vue 前端 + FastAPI 后端（合同功能全量）**

```bash
make install
make start
```
访问 **http://localhost:5173**

**方式二：Gradio 前端（通用 Agent + 预留信息采集）**

```bash
make start-gradio
```
访问 **http://localhost:7860**

**方式三：一键启动脚本**

```bash
chmod +x start.sh
./start.sh
```

##  使用指南

### 场景一：智能合同生成

#### 流程步骤

1. **上传模板** - 在左侧聊天区拖放 Word 模板文件（`.docx` 格式）
2. **触发识别** - 发送消息如"我要与企业签订技术合同"或"帮我填写这份模板"
3. **填写表单** - AI 识别占位符后，弹出动态表单（如 `{{甲方}}`、`{{乙方}}`、`{{合同编号}}`）
4. **生成合同** - 填写表单并提交，AI 自动生成合同文档
5. **预览下载** - 点击 ** 预览** 在右侧查看，或点击 ** 下载** 下载文件
6. **主动引导** - AI 会主动询问："您是否需要了解合同审批流程？是否需要合同签署、立项、资金到账等流程解释？"

#### 示例对话

```
用户：我要与企业签订技术合同
AI：好的，我为您提供技术合同模板。请上传您的合同模板文件，或使用我们的标准模板。
[AI 提供"上传模板"和"选择模板"选项]

用户：[上传模板]
AI：我已识别到模板中的占位符，请填写以下信息：
[动态表单：甲方、乙方、合同编号、签订日期等]

用户：[填写并提交表单]
AI：合同已生成完成！点击下方按钮下载。
[下载/预览按钮]
AI：您是否需要了解合同审批流程？是否需要我为您解释合同签署、立项、资金到账等后续步骤？
```

### 场景二：智能写作助手

#### 流程步骤

1. **描述需求** - 告诉 AI 你要写什么类型的文章
2. **提供素材** - 上传文档、提供 URL 或直接输入信息
3. **选择风格** - 正式/轻松/学术/活泼
4. **生成文章** - AI 根据素材和风格生成文章
5. **多格式输出** - Markdown/纯文本/幻灯片大纲

#### 示例对话

**示例 1：产研合作新闻稿**

```
用户：我要写一个关于我们公司与XX大学产研合作的新闻稿，这是我们活动的介绍：
      XX公司与XX大学于2024年4月15日签署了产学研合作协议，共同开展人工智能领域的研究...

AI：好的，我来为您撰写产研合作新闻稿。您希望采用什么风格？
[选项：正式、轻松、学术、活泼]

用户：正式风格
AI：调用工具生成新闻稿...

# XX公司与XX大学签署产学研合作协议，共启AI研究新篇章

**导语**：2024年4月15日，XX公司与XX大学在XX大学学术报告厅正式签署产学研合作协议...

**主体内容**：双方将围绕人工智能、大数据等领域开展深度合作...

[完整新闻稿内容]
```

**Example 2: Academic Profile (from webpage source)**

```
User: Help me write an academic profile introduction based on this webpage: https://ansatz.work/

AI: Let me fetch the webpage content first...
[Calling read_webpage tool]
Fetched webpage content (Title: README, Word count: ~2000 words)

Now generating academic profile in academic style:

# Cunxi Gong (ansatz) - Academic Profile

## Background
Cunxi Gong is a PhD student in Physics at The Chinese University of Hong Kong, Shenzhen, under the supervision of Prof. Weitang Li. His research explores the intersection of Quantum Computing, Tensor Networks, and Machine Learning.

## Research Interests
- Quantum Computing
- Tensor Networks
- Machine Learning
- Computational Chemistry

## Education
- PhD Student in Physics, The Chinese University of Hong Kong, Shenzhen

## Contact
- Email: ansatzMe@outlook.com

[Full academic profile content]
```

**示例 3：幻灯片大纲**

```
用户：帮我写一个公众号推文，主题是"大学生创新创业大赛"，要求活泼风格，并生成幻灯片大纲

AI：好的，我来为您撰写公众号推文和幻灯片大纲。

#  大学生创新创业大赛：点燃梦想，创造未来！

[公众号推文内容...]

---

# 幻灯片大纲

## Slide 1: 大赛背景
- 创新创业教育的重要性
- 历届大赛成果回顾
- 本届大赛亮点

## Slide 2: 参赛要求
- 参赛对象：全日制在校大学生
- 团队规模：3-5人
- 项目要求：创新性、可行性、市场前景

## Slide 3: 赛程安排
- 报名阶段：2024年3-4月
- 初赛阶段：2024年5月
- 决赛阶段：2024年6月

...
```

### 文件管理

- **上传文件**：拖放 `.docx` 文档到聊天区域
- **查看文件**：点击消息中的  文件链接
- **多文件支持**：同一会话可上传多个文件，历史记录保留
- **预览操作**：右侧预览区支持缩放（50%-200%）、下载、删除

### 会话管理

- **历史会话**：左侧面板显示所有历史会话，点击切换
- **新建会话**：点击"+ 新对话"按钮
- **删除会话**：点击会话右侧的  按钮

## ️ 项目结构

```
agent-ui-demo/
├── backend/                    # Python 后端
│   ├── src/
│   │   ├── agent_framework/   # 通用 Agent 框架
│   │   │   ├── agent.py       # ReAct Agent（可配置 system prompt）
│   │   │   ├── llm.py         # LLM 服务（LiteLLM 封装）
│   │   │   ├── tool_registry.py     # 工具注册与执行
│   │   │   ├── session.py     # JSONL 会话管理
│   │   │   ├── mcp_bridge.py  # MCP 服务器管理器
│   │   │   └── tools/base.py  # Tool/ToolResult 基类
│   │   ├── gradio_app/        # Gradio 前端
│   │   │   └── app.py         # Blocks 界面（对话/信息收集/设置）
│   │   ├── api/               # FastAPI 路由
│   │   │   ├── chat.py        # 聊天 API + /submit-form
│   │   │   ├── files.py       # 文件上传/下载/预览
│   │   │   ├── contracts.py   # 合同管理
│   │   │   └── templates.py   # 模板管理
│   │   ├── services/          # 业务逻辑层（继承 agent_framework）
│   │   │   ├── agent_service.py       # Agent 主服务
│   │   │   ├── react_agent.py         # 合同领域 ReAct Agent
│   │   │   ├── llm_service.py         # 扩展 LLM（合同审查、模板分析）
│   │   │   ├── session_service.py     # 扩展会话（文件元数据）
│   │   │   ├── file_service.py        # 文件解析（python-docx）
│   │   │   ├── doc_generator.py       # 文档生成
│   │   │   └── tools/                 # 工具系统
│   │   │       ├── base.py            # 框架导入桥接
│   │   │       ├── show_form.py       # 动态表单
│   │   │       ├── generate_document.py  # 文档生成
│   │   │       ├── read_webpage.py    # 网页爬取
│   │   │       └── write_article.py   # 智能写作
│   │   ├── models/            # SQLModel 数据模型
│   │   ├── schemas/           # Pydantic schemas
│   │   └── main.py            # FastAPI 入口
│   └── tests/                 # 测试文件
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── views/
│   │   │   └── ContractWorkspace.vue  # 主界面
│   │   ├── components/
│   │   │   └── DynamicForm.vue        # 动态表单（A2UI）
│   │   ├── stores/
│   │   │   ├── chat.ts        # 聊天状态
│   │   │   └── contract.ts    # 合同状态
│   │   ├── api/
│   │   │   └── client.ts      # API 客户端
│   │   └── types/             # TypeScript 类型
│   └── ...
├── sessions/                   # JSONL 会话数据
├── uploads/                    # 上传和生成的文件
├── config.example.toml         # LLM API 配置示例
├── start.py                    # FastAPI 启动入口
├── start_gradio.py             # Gradio 启动入口
├── Makefile                    # 构建/启动命令
└── pyproject.toml              # Python 项目配置
```

##  开发指南

### Makefile 命令

```bash
make start           # 启动 Vue 前端 + FastAPI 后端
make start-backend   # 仅启动 FastAPI 后端（前台）
make start-frontend  # 仅启动 Vue 前端（前台）
make start-gradio    # 启动 Gradio 前端（前台）
make stop            # 停止所有服务
make status          # 查看服务状态
make logs            # 查看日志
make clean           # 清理临时文件
```

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

# 启动 Gradio（开发模式）
python start_gradio.py
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

##  核心工作流

### 场景一：智能合同生成

#### 1. 意图识别与模板提供

```
用户：我要与企业签订技术合同
AI：识别意图 → 提供"上传模板"和"选择模板"选项
```

#### 2. 上传模板 → AI 识别占位符

```
用户：拖放 "合同模板.docx"（包含 {{甲方}}、{{乙方}}、{{合同编号}}）
AI：识别到合同模板，调用 show_form 工具
前端：渲染动态表单
```

#### 3. 填写表单 → 生成合同

```
用户：填写表单字段（甲方="ABC公司"，乙方="XYZ公司"，合同编号="2024-001"）
AI：接收表单数据，调用 generate_document 工具
后端：使用 python-docx 替换占位符，生成唯一文件名（20260417_061830_abc123_合同.docx）
前端：显示下载/预览按钮
```

#### 4. 主动引导下一步

```
AI：合同已生成完成！
    您是否需要了解合同审批流程？
    是否需要我为您解释合同签署、立项、资金到账等后续步骤？
    是否需要其他合同相关的帮助？
```

### 场景二：智能写作助手

#### 1. Collect Source Material

```
User: Help me write an academic profile based on this webpage: https://ansatz.work/
AI: Calling read_webpage tool to fetch webpage content
    Fetched 2000 words of content
```

#### 2. Call Writing Tool

```
AI: Calling write_article tool
    article_type: "general"
    topic: "Academic Profile"
    style: "academic"
    source_material: <webpage content>
    output_format: "markdown"
```

#### 3. Generate Article

```
AI: Generating complete article based on structure template and style guide
    - Background
    - Research Interests
    - Education
    - Contact Information
```

#### 4. Multiple Output Formats

```
User: Can you also generate a slide outline?
AI: Re-calling write_article with output_format="slide_outline"
    Generating:
    # Slide 1: Background
    - Key point 1
    - Key point 2
    ...

##  技术亮点

### agent_framework — 通用 Agent 框架

- **可配置 ReAct Agent**：system prompt 可自定义，适配合同、写作、信息采集等任意场景
- **多 Provider LLM**：通过 LiteLLM 统一接口（火山引擎、OpenAI、Anthropic）
- **插件式 Tool**：注册任意工具，自动生成 OpenAI function calling 定义
- **MCP Bridge**：多 MCP 服务器管理器，标准 JSON-RPC 协议，预留知乎扩展

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

### Gradio 前端

- **Python 原生 UI**：无需 Node.js 环境，适合快速原型
- **三标签页布局**：对话 / 信息收集（预留）/ 设置
- **同一 Agent 后端**：与 Vue 前端共享 agent_framework 核心

##  配置说明

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

##  停止服务

```bash
./stop.sh
```

或按 `Ctrl+C` 停止启动脚本

##  许可证

MIT

##  贡献

欢迎提交 Issue 和 Pull Request！

---

**Made with  for enterprise contract automation**
