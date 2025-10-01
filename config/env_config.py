from typing import List, Optional
from datetime import time, datetime

from pydantic import Field, AnyHttpUrl, field_validator, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

class EnvConfig(BaseSettings):
    """
    Centralized environment configuration.
    Loads from container environment variables first (stack),
    with a fallback to a local `.env` file for development.
    """

    # ---------------------------
    # Supabase
    # ---------------------------
    supabase_url: AnyHttpUrl = Field(..., validation_alias=AliasChoices("SUPABASE_URL"), description="Supabase URL")
    supabase_service_role_key: str = Field(...,validation_alias=AliasChoices("SUPABASE_SERVICE_ROLE_KEY"),description="Supabase service role key")

    # ---------------------------
    # Checkpointer_DB
    # ---------------------------
    db_uri: str = Field(..., validation_alias=AliasChoices("DB_URI"), description="Database URI for checkpointer")

    # ---------------------------
    # Web_Search_Tool
    # ---------------------------
    tavily_search_api_key: Optional[str] = Field(None, validation_alias=AliasChoices("TAVILY_SEARCH_API_KEY"))

    # ---------------------------
    # Summarization parameters
    # ---------------------------
    summary_tokens: int = Field(300, validation_alias=AliasChoices("SUMMARY_TOKENS"))
    starting_summary_index: int = Field(5, validation_alias=AliasChoices("STARTING_SUMMARY_INDEX"))
    summarization_llm: str = Field("gpt-4.1-nano", validation_alias=AliasChoices("SUMMARIZATION_LLM"))
    summarization_llm_temperature: float = Field( 0.15, validation_alias=AliasChoices("SUMMARIZATION_LLM_TEMPERATURE"))
    keep_last: int = Field(4, validation_alias=AliasChoices("KEEP_LAST"))

    # ---------------------------
    # Weaviate
    # ---------------------------
    weaviate_host: str = Field("127.0.0.1", validation_alias=AliasChoices("WEAVIATE_HOST"))
    weaviate_host_port: int = Field(11000, validation_alias=AliasChoices("WEAVIATE_HOST_PORT"))
    weaviate_grpc_port: int = Field(50051, validation_alias=AliasChoices("WEAVIATE_GRPC_PORT"))
    index_name: str = Field("rag_web_data", validation_alias=AliasChoices("INDEX_NAME"))

    # ---------------------------
    # Retriever Parameters
    # ---------------------------
    retriever_score_threshold: float = Field(0.6, validation_alias=AliasChoices("RETRIEVER_SCORE_THRESHOLD"))
    retriever_k: int = Field(10, validation_alias=AliasChoices("RETRIEVER_K"))
    retriever_alpha: float = Field(0.5, validation_alias=AliasChoices("RETRIEVER_ALPHA"))

    # ---------------------------
    # Embeddings Model
    # ---------------------------
    embeddings_model: str = Field("text-embedding-3-small", validation_alias=AliasChoices("EMBEDDINGS_MODEL"))

    # ---------------------------
    # Agents LLM
    # ---------------------------
    llm: str = Field("gpt-4.1-mini", validation_alias=AliasChoices("LLM"))
    llm_temperature: float = Field(0.15, validation_alias=AliasChoices("LLM_TEMPERATURE"))
    max_completion_tokens: int = Field(200, validation_alias=AliasChoices("MAX_COMPLETION_TOKENS"))
    llm_timeout: int = Field(20, validation_alias=AliasChoices("LLM_TIMEOUT"))
    openai_api_key: str = Field(..., validation_alias=AliasChoices("OPENAI_API_KEY"))

    # ---------------------------
    # Rate Limiter Parameters
    # ---------------------------
    requests_per_sec: int = Field(1, validation_alias=AliasChoices("REQUESTS_PER_SEC"))
    checking_sec_interval: int = Field(1, validation_alias=AliasChoices("CHECKING_SEC_INTERVAL"))
    max_bucket_size: int = Field(1, validation_alias=AliasChoices("MAX_BUCKET_SIZE"))

    # ---------------------------
    # Booking rules
    # ---------------------------
    booking_starting_time: time = Field(..., validation_alias=AliasChoices("BOOKING_STARTING_TIME"))
    booking_end_time: time = Field(..., validation_alias=AliasChoices("BOOKING_END_TIME"))
    booking_duration_minutes: int = Field(..., validation_alias=AliasChoices("BOOKINKG_DURATION_MINUTES"))
    booking_step_minutes: int = Field(..., validation_alias=AliasChoices("BOOKING_STEP_MINUTES"))
    available_weekdays: List[str] = Field(..., validation_alias=AliasChoices("AVAILABLE_WEEKDAYS"))
    max_book_ahead_days: int = Field(..., validation_alias=AliasChoices("MAX_BOOK_AHEAD_DAYS"))

    # ---------------------------
    # Validators / Parsers 
    # ---------------------------

    @field_validator("booking_starting_time", mode="before")
    @classmethod
    def _parse_start_time(cls, v):
        # Accepts "HH:MM"
        if isinstance(v, time):
            return v
        return datetime.strptime(str(v).strip(), "%H:%M").time()

    @field_validator("booking_end_time", mode="before")
    @classmethod
    def _parse_end_time(cls, v):
        if isinstance(v, time):
            return v
        return datetime.strptime(str(v).strip(), "%H:%M").time()

    @field_validator("available_weekdays", mode="before")
    @classmethod
    def _parse_weekdays(cls, v):
        """
            Accepts either:
            - a comma-separated string: "monday,tuesday, wednesday"
            - or a list already.
            Normalizes to lowercase trimmed list.
        """
        if isinstance(v, list):
            return [str(x).strip().lower() for x in v]
        parts = str(v).split(",")
        return [p.strip().lower() for p in parts if p.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",           
        env_file_encoding="utf-8",
        case_sensitive=True,       
        extra="ignore",
    )

# Singleton instance to import across the app
env = EnvConfig()