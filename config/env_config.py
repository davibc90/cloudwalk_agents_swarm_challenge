from pydantic import BaseSettings, Field, AnyHttpUrl, validator
from typing import List, Optional
from datetime import time, datetime

class EnvConfig(BaseSettings):
    """
    Centralized environment configuration.
    Loads from container environment variables first (stack),
    with a fallback to a local `.env` file for development.
    """

    # ---------------------------
    # Supabase
    # ---------------------------
    supabase_url: AnyHttpUrl = Field(..., env="SUPABASE_URL")
    supabase_service_role_key: str = Field(..., env="SUPABASE_SERVICE_ROLE_KEY")

    # ---------------------------
    # Checkpointer_DB
    # ---------------------------
    db_uri: str = Field(..., env="DB_URI")

    # ---------------------------
    # Web_Search_Tool
    # ---------------------------
    tavily_search_api_key: Optional[str] = Field(None, env="TAVILY_SEARCH_API_KEY")

    # ---------------------------
    # Summarization parameters
    # ---------------------------
    summary_tokens: int = Field(300, env="SUMMARY_TOKENS")
    starting_summary_index: int = Field(5, env="STARTING_SUMMARY_INDEX")
    summarization_llm: str = Field("gpt-4.1-nano", env="SUMMARIZATION_LLM")
    summarization_llm_temperature: float = Field(0.15, env="SUMMARIZATION_LLM_TEMPERATURE")
    keep_last: int = Field(4, env="KEEP_LAST")

    # ---------------------------
    # Weaviate
    # ---------------------------
    weaviate_host: str = Field("127.0.0.1", env="WEAVIATE_HOST")
    weaviate_host_port: int = Field(11000, env="WEAVIATE_HOST_PORT")
    weaviate_grpc_port: int = Field(50051, env="WEAVIATE_GRPC_PORT")
    index_name: str = Field("rag_web_data", env="INDEX_NAME")

    # ---------------------------
    # Retriever Parameters
    # ---------------------------
    retriever_score_threshold: float = Field(0.6, env="RETRIEVER_SCORE_THRESHOLD")
    retriever_k: int = Field(10, env="RETRIEVER_K")
    retriever_alpha: float = Field(0.5, env="RETRIEVER_ALPHA")

    # ---------------------------
    # Embeddings Model
    # ---------------------------
    embeddings_model: str = Field("text-embedding-3-small", env="EMBEDDINGS_MODEL")

    # ---------------------------
    # Agents LLM
    # ---------------------------
    llm: str = Field("gpt-4.1-mini", env="LLM")
    llm_temperature: float = Field(0.15, env="LLM_TEMPERATURE")
    max_completion_tokens: int = Field(200, env="MAX_COMPLETION_TOKENS")
    llm_timeout: int = Field(20, env="LLM_TIMEOUT")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")

    # ---------------------------
    # Rate Limiter Parameters
    # ---------------------------
    requests_per_sec: int = Field(1, env="REQUESTS_PER_SEC")
    checking_sec_interval: int = Field(1, env="CHECKING_SEC_INTERVAL")
    max_bucket_size: int = Field(1, env="MAX_BUCKET_SIZE")

    # ---------------------------
    # Booking rules
    # ---------------------------
    booking_starting_time: time = Field(..., env="BOOKING_STARTING_TIME")
    booking_end_time: time = Field(..., env="BOOKING_END_TIME")
    booking_duration_minutes: int = Field(..., env="BOOKINKG_DURATION_MINUTES")  # (mantido conforme seu nome)
    booking_step_minutes: int = Field(..., env="BOOKING_STEP_MINUTES")
    available_weekdays: List[str] = Field(..., env="AVAILABLE_WEEKDAYS")
    max_book_ahead_days: int = Field(..., env="MAX_BOOK_AHEAD_DAYS")

    # ---------------------------
    # Validators / Parsers
    # ---------------------------

    @validator("booking_starting_time", pre=True)
    def _parse_start_time(cls, v):
        # Accepts "HH:MM"
        if isinstance(v, time):
            return v
        return datetime.strptime(str(v).strip(), "%H:%M").time()

    @validator("booking_end_time", pre=True)
    def _parse_end_time(cls, v):
        if isinstance(v, time):
            return v
        return datetime.strptime(str(v).strip(), "%H:%M").time()

    @validator("available_weekdays", pre=True)
    def _parse_weekdays(cls, v):
        """
        Accepts either:
        - a comma-separated string: "monday,tuesday, wednesday"
        - or a list already.
        Normalizes to lowercase trimmed list.
        """
        if isinstance(v, list):
            return [str(x).strip().lower() for x in v]
        # string path
        parts = str(v).split(",")
        return [p.strip().lower() for p in parts if p.strip()]

    class Config:
        # Fallback to .env locally; in containers, env vars from the stack take precedence
        env_file = ".env"
        case_sensitive = True


# Singleton instance to import across the app
env = EnvConfig()