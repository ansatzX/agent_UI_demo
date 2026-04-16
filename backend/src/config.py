from typing import List, Optional, Dict, Any
from pathlib import Path
import tomlkit
import sys


class Settings:
    def __init__(self, config_path: Optional[Path] = None):
        # 项目根目录（start.py所在目录）
        self.project_root = Path(__file__).parent.parent.parent

        if config_path is None:
            config_path = self.project_root / "config.toml"

        self._config = self._load_config(config_path)

        # App settings
        app_config = self._config.get("app", {})
        self.app_name: str = app_config.get("name", "合同智能助手")
        self.app_host: str = app_config.get("host", "0.0.0.0")
        self.app_port: int = int(app_config.get("port", 8000))

        # 确保数据库在项目根目录
        db_url = app_config.get("database_url", "sqlite:///./contracts.db")
        if db_url.startswith("sqlite:///./"):
            db_path = self.project_root / db_url.replace("sqlite:///./", "")
            self.database_url: str = f"sqlite:///{db_path}"
        else:
            self.database_url: str = db_url

        # LLM settings
        llm_config = self._config.get("llm", {})
        self.llm_model: str = llm_config.get("default_model", "deepseek/deepseek-chat")

        # Provider settings
        self._providers: Dict[str, Dict[str, Any]] = self._config.get("providers", {})

        # CORS settings
        cors_config = self._config.get("cors", {})
        self.cors_origins: str = ",".join(cors_config.get("origins", ["http://localhost:5173", "http://localhost:3000"]))

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load and parse TOML config file"""
        if not config_path.exists():
            return {}

        with open(config_path, "r", encoding="utf-8") as f:
            return tomlkit.load(f)

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def get_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific provider"""
        return self._providers.get(provider_name)

    def get_provider_api_key(self, provider_name: str) -> Optional[str]:
        """Get API key for a specific provider"""
        provider = self.get_provider_config(provider_name)
        return provider.get("api_key") if provider else None

    def get_provider_api_base(self, provider_name: str) -> Optional[str]:
        """Get API base URL for a specific provider"""
        provider = self.get_provider_config(provider_name)
        return provider.get("api_base") if provider else None

    # Backward compatibility properties
    @property
    def deepseek_api_key(self) -> Optional[str]:
        return self.get_provider_api_key("deepseek")

    @property
    def deepseek_base_url(self) -> Optional[str]:
        return self.get_provider_api_base("deepseek")

    @property
    def volc_api_key(self) -> Optional[str]:
        return self.get_provider_api_key("volcengine")

    @property
    def volc_base_url(self) -> Optional[str]:
        return self.get_provider_api_base("volcengine")

    @property
    def anthropic_api_key(self) -> Optional[str]:
        return self.get_provider_api_key("anthropic")

    @property
    def anthropic_base_url(self) -> Optional[str]:
        return self.get_provider_api_base("anthropic")


# Global settings instance
settings = Settings()
