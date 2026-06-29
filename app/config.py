from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AMF_", env_file=".env", extra="ignore")

    api_key: str = Field(..., min_length=16)
    database_url: str = Field(..., min_length=1)
    cookie_name: str = "amf_session"
    cookie_secure: bool = False
    plugins_config: str = "app/plugins.json"


settings = Settings()  # type: ignore[call-arg]
