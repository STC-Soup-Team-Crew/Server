from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "STC Hackathon API"
    openai_api_key: str = ""
    model_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()