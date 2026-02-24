from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "STC Hackathon API"
    openai_api_key: str = ""
    model_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_api_version: str = "2025-01-27.acacia"
    billing_default_currency: str = "usd"
    billing_default_amount_cents: int = 999
    billing_merchant_display_name: str = "STC Hackathon"
    billing_return_url: str = ""
    billing_portal_return_url: str = ""
    clerk_secret_key: str = ""
    clerk_api_base_url: str = "https://api.clerk.com/v1"
    clerk_issuer: str = ""
    clerk_jwks_url: str = ""
    clerk_audience: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
