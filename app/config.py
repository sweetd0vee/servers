# app/config.py
import os
from typing import Optional


class Config:
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "server_metrics")

    # Thresholds
    CPU_THRESHOLDS = {
        'low': int(os.getenv("CPU_LOW_THRESHOLD", "20")),
        'high': int(os.getenv("CPU_HIGH_THRESHOLD", "70"))
    }

    MEM_THRESHOLDS = {
        'low': int(os.getenv("CPU_LOW_THRESHOLD", "30")),
        'high': int(os.getenv("CPU_HIGH_THRESHOLD", "80"))
    }

    # LLM
    LLM_URL: str = os.getenv("LLM_URL", "http://llama-server:8080/completion")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "90"))

    @classmethod
    def validate(cls) -> None:
        """Validate configuration."""
        required = ["DB_USER", "DB_PASSWORD"]
        missing = [var for var in required if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required env vars: {missing}")