from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "My FastAPI App"
    admin_email: str = ""
    secret_key: str = ""
    database_url: str = ""
    external_api_url: str = ""  # URL of the external image-processing API
    external_api_key: str = ""  # Optional API key for the external service

    class Config:
        env_file = ".env"

settings = Settings()