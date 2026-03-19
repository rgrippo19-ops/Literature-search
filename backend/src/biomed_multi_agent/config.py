from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.4")
    openai_reasoning_effort: str = os.getenv("OPENAI_REASONING_EFFORT", "medium")
    planner_model: str = os.getenv("PLANNER_MODEL", os.getenv("OPENAI_MODEL", "gpt-5.4"))
    extraction_model: str = os.getenv("EXTRACTION_MODEL", os.getenv("OPENAI_MODEL", "gpt-5.4"))
    synthesis_model: str = os.getenv("SYNTHESIS_MODEL", os.getenv("OPENAI_MODEL", "gpt-5.4"))
    openai_timeout_sec: int = int(os.getenv("OPENAI_TIMEOUT_SEC", "120"))
    openai_max_retries: int = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
    openai_store: bool = _bool("OPENAI_STORE", False)

    ncbi_email: str = os.getenv("NCBI_EMAIL", "")
    ncbi_api_key: str | None = os.getenv("NCBI_API_KEY")
    ncbi_tool: str = os.getenv("NCBI_TOOL", "biomed_multi_agent_analyst")
    http_timeout_sec: int = int(os.getenv("HTTP_TIMEOUT_SEC", "45"))
    sleep_between_requests_sec: float = float(os.getenv("SLEEP_BETWEEN_REQUESTS_SEC", "0.34"))
    http_user_agent: str = os.getenv("HTTP_USER_AGENT", "biomed-multi-agent-analyst/0.3")

    max_papers: int = int(os.getenv("MAX_PAPERS", "8"))
    max_papers_per_query: int = int(os.getenv("MAX_PAPERS_PER_QUERY", "12"))
    search_window_years: int = int(os.getenv("SEARCH_WINDOW_YEARS", "10"))
    enable_pmc_fulltext: bool = _bool("ENABLE_PMC_FULLTEXT", True)
    fulltext_char_limit: int = int(os.getenv("FULLTEXT_CHAR_LIMIT", "16000"))
    fulltext_paragraph_limit: int = int(os.getenv("FULLTEXT_PARAGRAPH_LIMIT", "24"))

    # Public app defaults + hard caps
    default_max_papers: int = int(os.getenv("DEFAULT_MAX_PAPERS", os.getenv("MAX_PAPERS", "8")))
    max_allowed_papers: int = int(os.getenv("MAX_ALLOWED_PAPERS", "12"))

    default_search_years: int = int(os.getenv("DEFAULT_SEARCH_YEARS", os.getenv("SEARCH_WINDOW_YEARS", "10")))
    max_allowed_search_years: int = int(os.getenv("MAX_ALLOWED_SEARCH_YEARS", "15"))

    allow_fulltext: bool = _bool("ALLOW_FULLTEXT", _bool("ENABLE_PMC_FULLTEXT", True))
    max_question_length: int = int(os.getenv("MAX_QUESTION_LENGTH", "2000"))


SETTINGS = Settings()

import os
print("CONFIG FILE:", __file__)
print("CWD:", os.getcwd())
print("OPENAI KEY PREFIX:", SETTINGS.openai_api_key[:16] if SETTINGS.openai_api_key else None)

def validate_required_settings() -> None:
    missing: list[str] = []
    if not SETTINGS.openai_api_key:
        missing.append("OPENAI_API_KEY")
    if not SETTINGS.ncbi_email:
        missing.append("NCBI_EMAIL")
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing) + ". "
            "Copy .env.example to .env and fill them in before running."
        )