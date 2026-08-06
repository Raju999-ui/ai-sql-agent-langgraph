"""Configuration management for the AI SQL Agent application."""

import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

load_dotenv()


def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve environment variable, checking Streamlit secrets first then os.environ."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            # Check exact key
            if key in st.secrets:
                val = st.secrets[key]
                if val is not None and str(val).strip() != "":
                    return str(val).strip()
            # Case-insensitive check
            for s_key in st.secrets:
                if s_key.upper() == key.upper():
                    val = st.secrets[s_key]
                    if val is not None and str(val).strip() != "":
                        return str(val).strip()
    except Exception:
        pass
    val = os.getenv(key)
    if val is not None and str(val).strip() != "":
        return str(val).strip()
    return default


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
        """Load Snowflake config from environment variables or Streamlit secrets."""
        return SnowflakeConfig(
            user=get_env_var("SNOWFLAKE_USER", ""),
            password=get_env_var("SNOWFLAKE_PASSWORD", ""),
            account=get_env_var("SNOWFLAKE_ACCOUNT", ""),
            warehouse=get_env_var("SNOWFLAKE_WAREHOUSE", ""),
            database=get_env_var("SNOWFLAKE_DATABASE", ""),
            schema=get_env_var("SNOWFLAKE_SCHEMA", "PUBLIC"),
        )


@dataclass
class LLMConfig:
    """Language model configuration."""

    api_key: str
    model: str = "openrouter/auto"
    base_url: str = "https://openrouter.ai/api/v1"
    temperature: float = 0.0
    max_tokens: Optional[int] = None

    @staticmethod
    def from_env() -> "LLMConfig":
        """Load LLM config from environment variables or Streamlit secrets."""
        api_key = get_env_var("OPEN_ROUTER") or get_env_var("OPENAI_API_KEY") or get_env_var("GROQ_API_KEY") or ""
        
        # Determine appropriate base URL depending on key/provider
        base_url = get_env_var("LLM_BASE_URL")
        if not base_url:
            if get_env_var("GROQ_API_KEY") and not get_env_var("OPEN_ROUTER") and not get_env_var("OPENAI_API_KEY"):
                base_url = "https://api.groq.com/openai/v1"
            elif get_env_var("OPENAI_API_KEY") and not get_env_var("OPEN_ROUTER"):
                base_url = "https://api.openai.com/v1"
            else:
                base_url = "https://openrouter.ai/api/v1"

        model = get_env_var("LLM_MODEL")
        if not model:
            if get_env_var("GROQ_API_KEY") and not get_env_var("OPEN_ROUTER") and not get_env_var("OPENAI_API_KEY"):
                model = "llama-3.3-70b-versatile"
            elif get_env_var("OPENAI_API_KEY") and not get_env_var("OPEN_ROUTER"):
                model = "gpt-4o-mini"
            else:
                model = "openrouter/auto"

        max_tokens_val = get_env_var("LLM_MAX_TOKENS")
        max_tokens = int(max_tokens_val) if max_tokens_val else None

        temp_val = get_env_var("LLM_TEMPERATURE", "0")
        try:
            temperature = float(temp_val) if temp_val else 0.0
        except ValueError:
            temperature = 0.0

        return LLMConfig(
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
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
        """Load all config from environment variables or Streamlit secrets."""
        debug_val = get_env_var("DEBUG", "false")
        return AppConfig(
            snowflake=SnowflakeConfig.from_env(),
            llm=LLMConfig.from_env(),
            debug=str(debug_val).lower() == "true",
            log_level=get_env_var("LOG_LEVEL", "INFO"),
        )
