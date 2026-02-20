from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "My FastAPI App"
    admin_email: str
    secret_key: str
    database_url: str

    class Config:
        env_file = ".env"

settings = Settings()