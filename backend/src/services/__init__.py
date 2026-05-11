# Lazy imports — avoid hard dependency chain at import time.
# Tools and hot-deployable modules should not require sqlmodel at import.

def __getattr__(name: str):
    if name == "LLMService":
        from .llm_service import LLMService as _LLM
        return _LLM
    if name == "AgentService":
        from .agent_service import AgentService as _AS
        return _AS
    if name == "ContractService":
        from .contract_service import ContractService as _CS
        return _CS
    if name == "TemplateService":
        from .template_service import TemplateService as _TS
        return _TS
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["LLMService", "TemplateService", "ContractService", "AgentService"]
