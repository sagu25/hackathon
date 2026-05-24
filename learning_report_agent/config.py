from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MOCK_DIR = DATA_DIR / "mock"
DB_PATH = DATA_DIR / "learning_agent.db"
CHROMA_DIR = DATA_DIR / "chroma"
MEMORY_DIR = DATA_DIR / "memory"

for _d in (DATA_DIR, MOCK_DIR, CHROMA_DIR, MEMORY_DIR):
    _d.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-02-01"
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-large"

    # App
    app_env: str = "development"
    app_secret_key: str = "dev-secret-key"
    log_level: str = "INFO"

    @property
    def is_azure_configured(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)


settings = Settings()
