from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-reasoner"
    llm_timeout_s: float = 60.0
    llm_retries: int = 2

    bert_model_name: str = "all-MiniLM-L6-v2"
    bert_model_path: str = "models/bert_clf.joblib"
    bert_threshold: float = 0.6

    regex_rules_path: str = "config/regex_rules.json"
    database_url: str = "sqlite:///data/logsentinel.db"
    llm_only_sources: str = "LegacyCRM"
    llm_categories: str = "Workflow Error,Deprecation Warning"
    max_workers: int = 4

    # --- security / ops (Dev B) ---
    auth_enabled: bool = True
    api_keys: str = ""                 # comma-separated; required when auth_enabled
    rate_limit_per_min: int = 120      # per API key
    max_csv_bytes: int = 10_000_000
    log_json: bool = True

    @property
    def llm_only_source_set(self) -> set[str]:
        return {s.strip() for s in self.llm_only_sources.split(",") if s.strip()}

    @property
    def api_key_list(self) -> list[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    @property
    def llm_category_list(self) -> list[str]:
        return [c.strip() for c in self.llm_categories.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
