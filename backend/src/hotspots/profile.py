from __future__ import annotations

from pathlib import Path

import tomlkit

from .models import CreatorProfile


def default_creator_profile() -> CreatorProfile:
    return CreatorProfile(
        name="热点选题",
        goal="从热点新闻中筛选适合做视频选题的事件，并提供独特分析角度",
        focus_domains=["社会热点", "国际关系", "科技产业", "财经商业", "公共政策", "舆论争议"],
        analysis_lens=["普通人视角", "利益结构", "舆论分裂", "长期趋势", "反常识解释", "可故事化表达"],
        avoid=["纯搬运", "证据不足的阴谋论", "低价值情绪煽动", "纯娱乐八卦"],
    )


def load_creator_profile(path: str | Path | None = None) -> CreatorProfile:
    if not path:
        return default_creator_profile()
    p = Path(path)
    if not p.exists():
        return default_creator_profile()
    data = tomlkit.loads(p.read_text(encoding="utf-8"))
    default = default_creator_profile()
    return CreatorProfile(
        name=data.get("name", default.name),
        goal=data.get("goal", default.goal),
        focus_domains=list(data.get("focus_domains", default.focus_domains)),
        analysis_lens=list(data.get("analysis_lens", default.analysis_lens)),
        avoid=list(data.get("avoid", default.avoid)),
    )
