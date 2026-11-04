from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://kapaat:kapaat@localhost:5432/kapaat"
    secret_key: str = Field(min_length=32)
    base_url: str = "http://localhost:8080"
    photos_dir: str = "/data/photos"
    max_upload_mb: int = 15

    cookie_secure: bool = False
    session_days: int = 30
    open_signup: bool = False
    admin_email: str = ""  # if set, only this address can claim the first (admin) account

    mail_backend: str = "log"  # log | smtp
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Kapaat <kapaat@localhost>"
    smtp_starttls: bool = True

    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_name: str = "Single sign-on"
    oidc_admin_group: str = ""

    webauthn_rp_id: str = ""
    webauthn_rp_name: str = "Kapaat"

    webhook_worker: bool = True

    @property
    def public_url(self) -> str:
        return self.base_url.rstrip("/")

    @property
    def oidc_enabled(self) -> bool:
        return bool(self.oidc_issuer and self.oidc_client_id and self.oidc_client_secret)

    @property
    def passkeys_enabled(self) -> bool:
        return bool(self.webauthn_rp_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
