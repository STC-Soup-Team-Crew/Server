from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "STC Hackathon API"
    openai_api_key: str = ""
    model_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_api_version: str = "2024-06-20"
    billing_default_amount_cents: int = 199
    billing_default_currency: str = "usd"
    billing_merchant_display_name: str = "MealMaker"
    billing_return_url: str = ""
    billing_sqlite_path: str = "/tmp/stc_billing.sqlite3"
    clerk_secret_key: str = ""
    clerk_jwt_issuer: str = ""
    clerk_jwt_audience: str = ""
    clerk_api_url: str = "https://api.clerk.com/v1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
