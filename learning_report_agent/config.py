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

    # Power BI
    powerbi_tenant_id: str = ""
    powerbi_client_id: str = ""
    powerbi_client_secret: str = ""
    powerbi_workspace_id: str = ""

    # SMTP / Email delivery
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""

    # App
    app_env: str = "development"
    app_secret_key: str = "dev-secret-key"
    log_level: str = "INFO"

    @property
    def is_azure_configured(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def is_smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    @property
    def is_powerbi_configured(self) -> bool:
        return bool(
            self.powerbi_tenant_id and self.powerbi_client_id
            and self.powerbi_client_secret and self.powerbi_workspace_id
        )


settings = Settings()
