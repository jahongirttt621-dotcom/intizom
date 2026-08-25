from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loyiha sozlamalari. .env fayldan o'qiladi."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # BotFather'dan olingan token
    BOT_TOKEN: str

    # Mini App ochiladigan URL (https bo'lishi shart, GitHub Pages yoki VPS)
    WEBAPP_URL: str = "https://example.com"

    # Ma'lumotlar bazasi
    DATABASE_URL: str = "sqlite+aiosqlite:///./intizom.db"

    # API server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Check-in vaqt oynasi (soatlarda, 24h format). None bo'lsa istalgan vaqt.
    CHECKIN_START_HOUR: int | None = None
    CHECKIN_END_HOUR: int | None = None

    # Vaqt mintaqasi (streak hisoblash uchun)
    TIMEZONE: str = "Asia/Tashkent"


settings = Settings()
