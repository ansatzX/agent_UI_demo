# AI 智能助手

基于 ReAct Agent 框架的通用智能对话系统 — 合同生成、智能写作、热点选题巡检、深度研究。

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
```

自定义端口：
```bash
uv run agent-demo serve --port 7860
```

## 核心功能

### 深度研究
- **约束分解** — 复杂问题自动拆解为可验证的子约束
- **多源搜索** — DuckDuckGo + Wikipedia 并行搜索，LLM 相关性过滤
- **证据分级** — 每个发现标注证据等级（95% 官方文件 → 10% 猜测）
- **交叉验证** — 关键事实至少 2-3 个独立来源
- **知识缺口驱动** — 识别未验证的约束，针对性补充搜索

### 智能合同生成
- 上传 Word 模板 → AI 识别占位符 → 表单填充 → 生成合同

### 智能写作
- 多源素材 → 报告/新闻稿/公众号文章 → 导出 Word

### 热点选题巡检
- 知乎 MCP + Jina DeepSearch 双源采集
- LLM 选题分析（角度、标题、思维导图、风险提示）
- 巡检历史持久化

## 工具系统

| 工具 | 功能 |
|------|------|
| `deep_research` | 问题约束分解 → 验证清单 |
| `web_search` | 多源并行搜索 + LLM 相关性过滤 + 源分类 |
| `read_webpage` | URL 分类 + preview/full 两阶段读取 |
| `read_file` | 文件读取 |
| `write_article` | 文章/报告生成 |
| `generate_document` | 合同文档生成 |
| `save_document` | Word 文档导出 |
| `show_form` | 动态表单 |

## 项目结构

```
agent-ui-demo/
├── pyproject.toml              # 项目配置 + [project.scripts] 入口
├── config.example.toml          # 配置模板
├── backend/
│   └── src/
│       ├── cli.py               # CLI 入口 (agent-demo serve)
│       ├── main.py              # 统一运行时 (FastAPI + Gradio)
│       ├── agent_framework/     # ReAct Agent, LLM, Tool Registry, MCP
│       ├── services/
│       │   └── tools/           # 8 个工具
│       ├── gradio_app/          # Gradio 界面
│       ├── hotspots/            # 热点巡检子系统
│       └── api/                 # FastAPI 路由
└── backend/tests/               # 测试
```

## 测试

```bash
uv run python -m pytest backend/tests/ -v
```

## 技术栈

- **Agent**: ReAct (推理-行动循环)
- **LLM**: LiteLLM (DeepSeek, 火山引擎, Anthropic, AIHubMix)
- **前端**: Gradio 6.x
- **后端**: FastAPI + Uvicorn
- **搜索**: httpx + BeautifulSoup (DuckDuckGo, Wikipedia)
- **MCP**: 多服务器管理器 (知乎等)
- **包管理**: uv + Hatchling
