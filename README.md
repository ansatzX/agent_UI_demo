# agent-ui-demo

ReAct Agent 演示项目。集成 Gradio UI + FastAPI 后端，支持对话、合同生成、写作、热点选题巡检、深度研究五个场景。

## 快速启动

```bash
# 安装依赖
uv sync

# 配置
cp config.example.toml config.toml
# 编辑 config.toml，api_key 填环境变量名
# 创建 .env 文件写入真实密钥

# 启动
uv run agent-demo serve
# → http://localhost:8000

# 自定义端口
uv run agent-demo serve --port 7860
```

## 已验证的能力

| 场景 | 状态 | 说明 |
|------|------|------|
| 多轮对话 | 可用 | ReAct Agent + function calling，支持工具自动调用 |
| 合同生成 | 可用 | 上传 .docx 模板 → AI 识别 `{{占位符}}` → 表单 → 生成文档 |
| 智能写作 | 可用 | 选择文章类型/风格 → 生成内容 → 导出 .docx |
| 热点巡检 | 可用 | LLM 生成热点 → 约束分解 → 证据验证 → 选题评分 |
| 深度研究 | 可用 | 约束分解 → web_search → read_webpage → check_state 循环 |

### 深度研究

遵循 LDR（Long-Document Research）方法论：

1. `deep_research` 将问题分解为带权重和类型的约束清单
2. Agent 循环：`check_state` → `web_search` → `read_webpage` → `check_state` 更新进度
3. 每个发现标注证据等级（`direct_statement` 95% → `speculation` 10%）
4. 反面证据 >25% 或正面 <40% 时不采信
5. 所有关键约束验证完成后综合输出

### 热点选题巡检

支持 4 个采集器（可组合）：

| 采集器 | 数据源 | 依赖 |
|--------|--------|------|
| `LLMCollector` | LLM 训练数据 | 任意 LLM |
| `JinaDeepSearchCollector` | Jina DeepSearch API | AIHubMix API Key |
| `WebSearchCollector` | DuckDuckGo + Wikipedia | 本地可达的搜索服务 |
| `ZhihuMCPCollector` | 知乎 MCP | MCP Server 运行中 |

默认启用 `LLMCollector`。`web_search` 已切换为 Bing + Sogou，结果更稳定。

### 搜索源配置

`web_search` 工具支持以下搜索引擎（按优先级排列）：

| 搜索源 | 状态 | 配置 | 说明 |
|--------|------|------|------|
| **Bing API** | ✅ 推荐 | `.env` 配置 `BING_API_KEY` | 官方 API，免费 1000 次/月，结果质量高 |
| **Bing HTML** | ✅ 默认 | 无需配置 | `cn.bing.com/search` 抓取，API 不可用时自动降级 |
| **Sogou** | ✅ 默认 | 无需配置 | 中文搜索结果丰富，与 Bing 并行 |
| **SearXNG** | ✅ 可选 | 本地部署 | `docker run -d -p 8080:8080 searxng/searxng` |
| DuckDuckGo | ❌ 受限 | — | 网络环境无法访问 |
| Wikipedia | ❌ 受限 | — | 网络环境无法访问 |

**工作流程**：Bing API（有 key 时）→ Bing HTML + Sogou 并行 → SearXNG（本地部署时）→ LLM 降级兜底

**申请 Bing API Key**：
1. 注册 Azure 账号：https://portal.azure.com
2. 搜索 "Bing Search v7" → 创建资源
3. 免费层 F1：每月 1,000 次调用免费
4. 将 key 写入 `.env`：`BING_API_KEY=your_key_here`

## 工具系统

| 工具 | 功能 | 说明 |
|------|------|------|
| `deep_research` | 约束分解 | 将复杂问题拆解为可验证的子约束清单 |
| `check_state` | 研究状态 | 查看/更新约束验证进度，找下一个目标 |
| `web_search` | 多源搜索 | Bing API / Bing HTML / Sogou 并行，LLM 相关性过滤，源分类 |
| `read_webpage` | 网页爬取 | URL 分类 + preview/full 两阶段读取 |
| `read_file` | 文件读取 | 读取本地文件内容 |
| `write_article` | 写作辅助 | 生成文章结构模板和风格指南 |
| `generate_document` | 合同生成 | 基于 .docx 模板填充字段生成文档 |
| `save_document` | 文档导出 | Markdown 内容 → .docx 导出 |
| `show_form` | 动态表单 | 将占位符转为前端表单字段 |

## 项目结构

```
agent-ui-demo/
├── pyproject.toml
├── config.toml / config.example.toml
├── .env                         # API Keys（不入 git）
├── backend/
│   └── src/
│       ├── cli.py               # CLI: agent-demo serve
│       ├── main.py              # FastAPI + Gradio 统一入口
│       ├── agent_framework/     # ReAct Agent, LLM, Tool Registry, MCP Bridge
│       ├── config.py            # TOML 配置 + provider 解析
│       ├── database.py          # SQLite + SQLModel
│       ├── gradio_app/          # Gradio UI
│       ├── services/
│       │   ├── llm_service.py   # Provider 注册表 + LiteLLM 封装
│       │   └── tools/           # 9 个 Agent 工具
│       ├── hotspots/            # 热点巡检子系统
│       │   ├── collectors/      # 4 个采集器
│       │   ├── analyzer.py      # LLM 选题分析
│       │   ├── workflow.py      # 采集 → 评分 → 渲染管线
│       │   └── history.py       # JSONL 巡检历史
│       ├── api/                 # FastAPI REST 路由
│       ├── models/              # SQLModel 数据模型
│       └── schemas/             # Pydantic 请求/响应 schema
└── backend/tests/               # 77 个测试
```

## 配置

### Provider 路由

`config.toml` 中 `[llm] default_model` 的前缀决定使用哪个 provider：

| 模型前缀 | Provider | 环境变量 |
|----------|----------|----------|
| `openai/` | AIHubMix | `AIHUBMIX_API_KEY`, `AIHUBMIX_BASE_URL` |
| `deepseek/` | DeepSeek | `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` |
| `volcengine/` | 火山引擎 | `VOLC_API_KEY`, `VOLC_BASE_URL` |
| `doubao/` | 火山引擎 | `VOLC_API_KEY`, `VOLC_BASE_URL` |
| `anthropic/` | Anthropic | `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL` |

`config.toml` 中 `api_key` 字段填环境变量名（全大写+下划线），运行时从 `os.getenv()` 解析。`.env` 文件存放真实密钥。

### MCP 服务器

在 `backend/mcp_config.json` 中配置（Claude 格式或列表格式）：

```json
{
  "mcpServers": {
    "zhihu": {
      "command": "node",
      "args": ["path/to/zhihu-mcp/build/index.js"],
      "env": { "ZHIHU_COOKIE": "..." }
    }
  }
}
```

### Bing API（可选）

配置 `BING_API_KEY` 后自动使用官方 Bing Web Search API，免费额度每月 1,000 次。
未配置时用 HTML 抓取（`cn.bing.com/search`）。

```bash
# .env
BING_API_KEY=your_azure_key_here
```

申请地址：https://portal.azure.com → 搜索 "Bing Search v7" → 创建资源

## 测试

```bash
uv run python -m pytest backend/tests/ -v   # 77 tests
```

测试使用 venv 内的 pytest（`uv run python -m pytest`），不要用 `uv run pytest`（可能解析到系统 Python）。

## 技术栈

| 层 | 技术 |
|---|---|
| Agent | ReAct (推理-行动循环) + LiteLLM function calling |
| LLM | LiteLLM — DeepSeek, 火山引擎, Anthropic, AIHubMix |
| UI | Gradio 6.x（挂载在 FastAPI `/` 路径） |
| API | FastAPI + Uvicorn |
| 搜索 | httpx + BeautifulSoup（Bing API / HTML, Sogou, DuckDuckGo, Wikipedia, SearXNG） |
| MCP | 自实现 JSON-RPC 2.0 桥接，支持多服务器并发 |
| 数据 | SQLite + SQLModel；会话 JSONL 持久化 |
| 包管理 | uv + Hatchling |

## 已知限制

- DuckDuckGo/Wikipedia 在当前网络环境下不可达，已用 Bing + Sogou 替代
- 无用户认证（所有 API 端点裸奔）
- 会话管理基于文件系统 JSONL，不适合多实例部署
- MCP 连接重启后需手动重连
