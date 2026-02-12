"""Configuration management for the AI SQL Agent application."""

import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

load_dotenv()


@dataclass
class SnowflakeConfig:
    """Snowflake database configuration."""

    user: str
    password: str
    account: str
    warehouse: str
    database: str
    schema: str

    @staticmethod
    def from_env() -> "SnowflakeConfig":
        """Load Snowflake config from environment variables."""
        required_vars = ["SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD", "SNOWFLAKE_ACCOUNT",
                        "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA"]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return SnowflakeConfig(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
        )


@dataclass
class LLMConfig:
    """Language model configuration."""

    api_key: str
    model: str = "openrouter/auto"
    base_url: str = "https://openrouter.ai/api/v1"
    temperature: float = 0
    max_tokens: Optional[int] = None

    @staticmethod
    def from_env() -> "LLMConfig":
        """Load LLM config from environment variables."""
        api_key = os.getenv("OPEN_ROUTER")
        if not api_key:
            raise ValueError("Missing OPEN_ROUTER environment variable")
        
        return LLMConfig(
            api_key=api_key,
            model=os.getenv("LLM_MODEL", "openrouter/auto"),
            base_url=os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
            temperature=float(os.getenv("LLM_TEMPERATURE", 0)),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS")) if os.getenv("LLM_MAX_TOKENS") else None,
        )


@dataclass
class AppConfig:
    """Application configuration."""

    snowflake: SnowflakeConfig
    llm: LLMConfig
    debug: bool = False
    log_level: str = "INFO"

    @staticmethod
    def from_env() -> "AppConfig":
        """Load all config from environment variables."""
        return AppConfig(
            snowflake=SnowflakeConfig.from_env(),
            llm=LLMConfig.from_env(),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
