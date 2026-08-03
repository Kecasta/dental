import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "Smile Aesthetic & Dental Clinic - Agendador IA"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8050

    HOST: str = "0.0.0.0"

    # Gemini Model
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    
    # Google Calendar
    GOOGLE_CALENDAR_ID: str = "primary"

    # Configuración de Correo (Alertas de Administrador)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ADMIN_EMAIL: str = "admin@smileclinic.com"
    ADMIN_PASSWORD: str = "SmileClinic2026!"

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/smile_clinic.db"

    # WhatsApp / Webhooks
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "kinexus_smile_verify_token"
    N8N_WEBHOOK_URL: str = "http://localhost:5678/webhook/appointment"

    # Directorios de datos y logs
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Asegurar existencia de directorios necesarios
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
