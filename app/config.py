import os

# Thresholds for server load classification
CPU_THRESHOLDS = {
    'low': 20,
    'high': 70
}

MEMORY_THRESHOLDS = {
    'low': 30,
    'high': 80
}

# LLM Configuration
LLM_URL = os.getenv("LLM_URL", "http://llama-server:8080/completion")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "90"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "500"))
LLAMA_UI_URL_HEALTH = "http://llama-server:8080"
LLAMA_UI_URL = "http://localhost"