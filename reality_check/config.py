from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    reality_check_skip_llm: bool = False
    # Cap wait time so the UI never hangs; fallback uses corpus retrieval.
    openai_timeout_seconds: float = 28.0
    openai_max_tokens: int = 2200
    # json_object is faster than full pydantic json_schema on the API.
    openai_use_json_schema: bool = False
    retrieval_object_limit: int = 5

    # --- Deployment / security (Replit) ---
    # development | production | test
    reality_check_env: str = "development"
    # Comma-separated origins, e.g. https://your-app.replit.app
    reality_check_cors_origins: str = ""
    # Set to 0/false to hide /docs (default off in production)
    reality_check_enable_docs: bool | None = None
    # Optional: require X-Reality-Check-Key on stress-test routes (curl/scripts only)
    reality_check_stress_test_api_key: str = ""
    reality_check_rate_limit_enabled: bool = True
    reality_check_rate_limit_stress_test: int = 6
    reality_check_rate_limit_preview: int = 20
    reality_check_rate_limit_feedback: int = 10
    reality_check_custom_philosophy_max_length: int = 500
    reality_check_feedback_enabled: bool = True
    # Hide llm_configured on /api/health in production
    reality_check_expose_health_details: bool | None = None

    @field_validator("reality_check_env")
    @classmethod
    def normalize_env(cls, value: str) -> str:
        return value.strip().lower()

    @property
    def is_production(self) -> bool:
        return self.reality_check_env == "production"

    @property
    def api_docs_enabled(self) -> bool:
        if self.reality_check_enable_docs is not None:
            return self.reality_check_enable_docs
        return not self.is_production

    @property
    def expose_health_details(self) -> bool:
        if self.reality_check_expose_health_details is not None:
            return self.reality_check_expose_health_details
        return not self.is_production

    @property
    def cors_origins(self) -> list[str]:
        raw = self.reality_check_cors_origins.strip()
        if not raw:
            return []
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def stress_test_api_key(self) -> str:
        return self.reality_check_stress_test_api_key

    @property
    def rate_limit_enabled(self) -> bool:
        if self.reality_check_env == "test":
            return False
        return self.reality_check_rate_limit_enabled

    @property
    def rate_limit_stress_test(self) -> int:
        return self.reality_check_rate_limit_stress_test

    @property
    def rate_limit_preview(self) -> int:
        return self.reality_check_rate_limit_preview

    @property
    def rate_limit_feedback(self) -> int:
        return self.reality_check_rate_limit_feedback

    @property
    def custom_philosophy_max_length(self) -> int:
        return self.reality_check_custom_philosophy_max_length

    @property
    def feedback_enabled(self) -> bool:
        return self.reality_check_feedback_enabled


settings = Settings()
