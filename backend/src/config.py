"""Configuration management for the Contract Assistant application.

This module provides a centralized configuration system using TOML files.
It handles loading configuration from config.toml and provides type-safe
access to application settings.

Attributes:
    settings: Global Settings instance for application-wide configuration access.

Example:
    >>> from backend.src.config import settings
    >>> api_key = settings.get_provider_api_key('volcengine')
    >>> app_name = settings.app_name
"""

import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import tomlkit

logger = logging.getLogger(__name__)


class Settings:
    """Application settings manager with TOML configuration support.

    Manages application-wide settings including database connections,
    LLM provider configurations, and CORS settings. Settings are loaded
    from a TOML configuration file and cached for the application lifetime.

    Attributes:
        project_root: Root directory of the project (Path object).
        app_name: Name of the application from config.
        app_host: Host address for the FastAPI server.
        app_port: Port number for the FastAPI server.
        database_url: SQLite database connection URL.
        llm_model: Default LLM model identifier string.
        cors_origins: Comma-separated list of allowed CORS origins.
        _providers: Dictionary mapping provider names to configurations.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Settings with optional custom config path.

        Args:
            config_path: Optional path to TOML configuration file.
                If not provided, defaults to config.toml in project root.
        """
        # Project root directory (where start.py is located)
        self.project_root = Path(__file__).parent.parent.parent

        if config_path is None:
            config_path = self.project_root / "config.toml"

        self._config = self._load_config(config_path)

        # App settings
        app_config = self._config.get("app", {})
        self.app_name: str = app_config.get("name", "合同智能助手")
        self.app_host: str = app_config.get("host", "0.0.0.0")
        self.app_port: int = int(app_config.get("port", 8000))

        # Ensure database is in project root directory
        db_url = app_config.get("database_url", "sqlite:///./contracts.db")
        if db_url.startswith("sqlite:///./"):
            db_path = self.project_root / db_url.replace("sqlite:///./", "")
            self.database_url: str = f"sqlite:///{db_path}"
        else:
            self.database_url: str = db_url

        # LLM settings
        llm_config = self._config.get("llm", {})
        self.llm_model: str = llm_config.get(
            "default_model", "deepseek/deepseek-chat"
        )

        # Provider settings
        self._providers: Dict[str, Dict[str, Any]] = self._config.get(
            "providers", {}
        )

        # CORS settings
        cors_config = self._config.get("cors", {})
        self.cors_origins: str = ",".join(
            cors_config.get(
                "origins", ["http://localhost:5173", "http://localhost:3000"]
            )
        )

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load and parse TOML configuration file.

        Attempts to load the configuration from the specified TOML file.
        If the file doesn't exist or parsing fails, returns an empty dict
        and logs the error.

        Args:
            config_path: Path object pointing to the TOML configuration file.

        Returns:
            Dictionary containing parsed configuration data.
            Returns an empty dict if file doesn't exist or parsing fails.
        """
        if not config_path.exists():
            logger.error(
                f"Configuration file not found: {config_path}\n"
                f"Please copy config.example.toml to config.toml and "
                f"configure the parameters"
            )
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = tomlkit.load(f)
                logger.info(f"Successfully loaded config: {config_path}")
                return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return {}

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list.

        Returns:
            List of CORS origin strings parsed from comma-separated value.
        """
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def get_provider_config(
        self, provider_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific provider.

        Args:
            provider_name: Name of the LLM provider (e.g., 'volcengine').

        Returns:
            Dictionary containing provider configuration, or None if not found.
        """
        return self._providers.get(provider_name)

    def get_provider_api_key(self, provider_name: str) -> Optional[str]:
        """Get API key for a specific provider from config.toml.

        Args:
            provider_name: Name of the LLM provider.

        Returns:
            API key string if found and not empty, None otherwise.

        Note:
            Logs a warning if the API key is empty or provider not found.
        """
        provider = self.get_provider_config(provider_name)
        if provider and "api_key" in provider:
            api_key = provider.get("api_key")
            if not api_key:
                logger.warning(
                    f"API key for {provider_name} is empty, "
                    f"please configure it in config.toml"
                )
            return api_key

        logger.warning(
            f"Configuration for {provider_name} not found, "
            f"please check config.toml"
        )
        return None

    def get_provider_api_base(self, provider_name: str) -> Optional[str]:
        """Get API base URL for a specific provider.

        Args:
            provider_name: Name of the LLM provider.

        Returns:
            API base URL string if found, None otherwise.
        """
        provider = self.get_provider_config(provider_name)
        return provider.get("api_base") if provider else None

    # Backward compatibility properties
    @property
    def deepseek_api_key(self) -> Optional[str]:
        """Get DeepSeek API key (backward compatibility)."""
        return self.get_provider_api_key("deepseek")

    @property
    def deepseek_base_url(self) -> Optional[str]:
        """Get DeepSeek API base URL (backward compatibility)."""
        return self.get_provider_api_base("deepseek")

    @property
    def volc_api_key(self) -> Optional[str]:
        """Get Volcano Engine API key (backward compatibility)."""
        return self.get_provider_api_key("volcengine")

    @property
    def volc_base_url(self) -> Optional[str]:
        """Get Volcano Engine API base URL (backward compatibility)."""
        return self.get_provider_api_base("volcengine")

    @property
    def anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key (backward compatibility)."""
        return self.get_provider_api_key("anthropic")

    @property
    def anthropic_base_url(self) -> Optional[str]:
        """Get Anthropic API base URL (backward compatibility)."""
        return self.get_provider_api_base("anthropic")


# Global settings instance
settings = Settings()
