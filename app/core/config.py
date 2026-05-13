from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ─── Database ───
    database_url: str = "postgresql+asyncpg://oriox:oriox@localhost:5432/oriox"
    redis_url: str = "redis://localhost:6379/0"

    # ─── Exchange Keys ───
    binance_api_key: str = ""
    binance_api_secret: str = ""
    bybit_api_key: str = ""
    bybit_api_secret: str = ""
    mexc_api_key: str = ""
    mexc_api_secret: str = ""

    # ─── AI ───
    openai_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    ai_provider: str = "openai"

    # ─── Alerting ───
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""

    # ─── Sentiment ───
    cryptopanic_api_key: str = ""

    # ─── Application ───
    log_level: str = "INFO"
    scanner_interval_seconds: int = 300
    min_setup_confidence: int = 65
    min_rr_ratio: float = 2.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
