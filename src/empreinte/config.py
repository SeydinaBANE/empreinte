"""Configuration applicative chargee depuis l'environnement (12-factor)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parametres applicatifs, prefixes ``EMPREINTE_`` et charges depuis ``.env``."""

    model_config = SettingsConfigDict(
        env_prefix="EMPREINTE_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    env: str = "local"
    log_level: str = "INFO"

    llm_model_primary: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    llm_model_fallback: str = "llama3.2-vision"
    llm_api_base: str = ""
    llm_api_key: str = ""
    llm_timeout_sec: float = 60.0

    sovereign_mode: bool = True

    pdf_render_dpi: int = 150

    qdrant_url: str = ""
    qdrant_collection: str = "empreinte_esrs"

    sql_dsn: str = ""
    object_store_endpoint: str = ""
    object_store_bucket: str = "empreinte"
    object_store_access_key: str = ""
    object_store_secret_key: str = ""
    object_store_region: str = "us-east-1"

    reporting_year: int = 2025

    api_keys: tuple[str, ...] = Field(
        default=("dev-key-analyst:analyst", "dev-key-auditor:auditor"),
        description="colon-separated key:role pairs",
    )

    @property
    def api_key_mapping(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for entry in self.api_keys:
            if ":" in entry:
                key, role = entry.split(":", 1)
                mapping[key] = role
        return mapping

    rate_limit_max_requests: int = 60
    rate_limit_window_sec: int = 60


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retourne l'instance unique de configuration (mise en cache)."""
    return Settings()
