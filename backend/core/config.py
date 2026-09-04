from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Kasira POS API"
    API_V1_STR: str = "/api/v1"
    
    # Identitas produk + URL kanonik. Rebrand Kasira → Selaris 2026-09-02.
    # SITE_URL = yang DITAMPILIN ke user (link storefront di struk WA, link
    # referral, redirect Xendit). API tetap dilayani di kasira.online juga —
    # APK lama + webhook Xendit tenant nunjuk ke sana. Flip env sesudah DNS.
    BRAND_NAME: str = "Selaris"
    SITE_URL: str = "https://selaris.id"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "kasira"
    POSTGRES_PORT: str = "5432"
    # Non-superuser role for runtime (RLS enforced). Falls back to POSTGRES_USER if not set.
    POSTGRES_APP_USER: str = ""
    POSTGRES_APP_PASSWORD: str = ""

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        user = self.POSTGRES_APP_USER or self.POSTGRES_USER
        password = self.POSTGRES_APP_PASSWORD or self.POSTGRES_PASSWORD
        return f"postgresql+asyncpg://{user}:{password}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Fonnte WA
    FONNTE_TOKEN: str = ""
    # Google Maps kunci SERVER (Places, Geocoding, Static Maps). Kunci yang
    # sama dengan Sefrekuensi (GOOGLE_STATIC_KEY di sana). Kosong = fitur
    # peta di storefront mati, alamat antar jadi textarea biasa.
    GOOGLE_MAPS_SERVER_KEY: str = ""
    # Pintu notifikasi merchant ke Sefrekuensi (strategi akuisisi user Ivan).
    # Kosong = belum dicolok. Diisi URL webhook + token, semua pesan pemilik
    # (pesanan online, reservasi) ikut dikirim ke sana selain WA.
    SEFREKUENSI_NOTIFY_URL: str = ""
    SEFREKUENSI_NOTIFY_TOKEN: str = ""

    # Xendit Master Keys
    XENDIT_API_KEY: str = ""
    XENDIT_WEBHOOK_TOKEN: str = ""
    XENDIT_IS_PRODUCTION: bool = False

    # JWT Security
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7" # Change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Encryption
    ENCRYPTION_KEY: str = ""

    # App Environment
    ENVIRONMENT: str = "development"

    # Superadmin — comma-separated phone numbers
    SUPERADMIN_PHONES: str = ""

    # Claude AI — Sonnet (pricing coach) + invoice OCR (vision)
    ANTHROPIC_API_KEY: str = ""

    # DeepSeek — pengganti Haiku untuk chat/insight/menu/resep/WA bot.
    # Kosongin buat rollback: semua task balik ke Anthropic tanpa deploy kode.
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_CHAT_MODEL: str = "deepseek-v4-flash"

    # Chat publik di landing page. 0 = tanpa batas per IP (keputusan Ivan:
    # pantau dulu). Isi angka > 0 buat nyalain rem tanpa ubah kode.
    LANDING_CHAT_MAX_PER_IP: int = 0

    # Akun demo: satu nomor + satu OTP tetap, buat dipamerin ke calon pelanggan
    # tanpa perlu OTP WhatsApp beneran. SENGAJA dua-duanya harus diisi dan
    # dicocokkan persis — kalau salah satu kosong, jalur ini mati total.
    DEMO_PHONE: str = ""
    DEMO_OTP: str = ""

    # Voyage AI (embeddings for Layer 4)
    VOYAGE_API_KEY: str = ""

    # Sentry Error Tracking
    SENTRY_DSN: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
