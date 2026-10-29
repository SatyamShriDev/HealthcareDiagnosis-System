from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    jwt_secret: str  # required: no default on purpose
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    database_url: str = f"sqlite:///{BASE_DIR / 'app.db'}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    model_path: str = str(BASE_DIR / "ml" / "artifacts" / "heart_model.joblib")

    @field_validator("jwt_secret")
    @classmethod
    def _secret_long_enough(cls, v: str) -> str:
        if len(v) < 32 or v.startswith("REPLACE_WITH"):
            raise ValueError("JWT_SECRET must be a real random string of at least 32 characters")
        return v

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
