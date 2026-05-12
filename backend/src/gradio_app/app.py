"""Gradio UI — 对话 / 合同 / 热点巡检 / 设置"""

from __future__ import annotations

import logging

import gradio as gr

from .gradio_chat import GradioChatHandler, DEFAULT_HOTSPOT_SOURCES

logger = logging.getLogger(__name__)


def create_gradio_blocks(app_state) -> gr.Blocks:
    handler = GradioChatHandler(app_state)

    with gr.Blocks(title="AI 智能助手") as demo:
        gr.Markdown("# AI 智能助手")

        with gr.Tabs():
            # ── 对话 ───────────────────────────────────────────────────
            with gr.Tab("对话"):
                chatbot = gr.Chatbot(label="对话", height=450)
                with gr.Row():
                    msg = gr.Textbox(label="输入消息", placeholder="输入你的问题...", scale=8)
                    send_btn = gr.Button("发送", variant="primary", scale=1)
                with gr.Row():
                    file_input = gr.File(label="上传文件", file_types=[".docx", ".txt", ".pdf"])
                state = gr.State("")

                send_btn.click(fn=handler.chat, inputs=[msg, chatbot, file_input], outputs=[chatbot, state])
                msg.submit(fn=handler.chat, inputs=[msg, chatbot, file_input], outputs=[chatbot, state])

            # ── 合同生成 ──────────────────────────────────────────────
            with gr.Tab("合同"):
                gr.Markdown("### 上传 Word 模板，AI 自动识别占位符并生成合同")
                with gr.Row():
                    contract_file = gr.File(label="上传合同模板 (.docx)", file_types=[".docx"])
                with gr.Row():
                    contract_btn = gr.Button("分析模板", variant="primary")

                contract_output = gr.Markdown(
                    value="上传一个 .docx 模板开始。模板中使用 `{{字段名}}` 标记占位符。",
                    label="结果"
                )

                contract_btn.click(
                    fn=handler.handle_contract,
                    inputs=[contract_file],
                    outputs=[contract_output],
                )

            # ── 热点巡检 ──────────────────────────────────────────────
            with gr.Tab("热点巡检"):
                with gr.Row():
                    keywords = gr.Textbox(label="巡检关键词", value="社会热点 科技产业 国际关系", scale=6)
                    limit = gr.Number(label="结果数量", value=10, precision=0, scale=1)
                    days = gr.Number(label="天数", value=1, precision=0, scale=1)
                scan_btn = gr.Button("开始巡检", variant="primary")
                output = gr.Markdown(label="巡检进度与候选选题")
                gr.Markdown("### 巡检历史")
                history_md = gr.Markdown(value="加载中...", label="最近巡检记录")
                refresh_btn = gr.Button("刷新历史", variant="secondary", size="sm")
                with gr.Row():
                    run_id = gr.Textbox(label="输入 run_id 查看详情", scale=4)
                    load_btn = gr.Button("查看历史详情", variant="secondary", size="sm", scale=1)
                detail = gr.Markdown(label="历史详情")

                scan_btn.click(
                    fn=handler.scan_hotspots, inputs=[keywords, limit, days],
                    outputs=[output, history_md],
                )
                refresh_btn.click(fn=lambda: handler._history_markdown(), outputs=history_md)
                load_btn.click(fn=handler.history_detail, inputs=run_id, outputs=detail)

            # ── 设置 ───────────────────────────────────────────────────
            with gr.Tab("设置"):
                gr.Markdown("## 设置\n配置通过 `config.toml` 和 `.env` 管理。\n\n"
                           "### LLM\n`config.toml` → `[llm]` default_model\n\n"
                           "### API 密钥\n`.env` 文件或环境变量\n\n"
                           "### 热点巡检\n`backend/config/hotspot_profile.toml`")

    return demo
