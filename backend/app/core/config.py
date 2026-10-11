from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from app.constants.auth import JWT_SECRET_KEY_MIN_LENGTH, PASSWORD_MAX_LENGTH


class Settings(BaseSettings):
    # backend/.env est aussi lu par le conteneur PostgreSQL (compose.yaml) :
    # les identifiants ne sont définis qu'à un seul endroit.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    # Sans délai, une connexion vers une base arrêtée peut bloquer la requête très longtemps
    database_connect_timeout_seconds: int = Field(default=3, gt=0)

    # Authentification (docs/technical/authentication.md)
    jwt_secret_key: SecretStr = Field(min_length=JWT_SECRET_KEY_MIN_LENGTH)
    access_token_ttl_minutes: int = Field(default=15, gt=0)
    refresh_token_ttl_days: int = Field(default=30, gt=0)
    password_min_length: int = Field(default=8, gt=0, le=PASSWORD_MAX_LENGTH)
    # Compte sans mot de passe (Google) : âge maximal de la connexion pour supprimer le compte
    recent_authentication_max_age_minutes: int = Field(default=5, gt=0)
    # Durée de validité du lien de vérification de l'adresse email
    email_verification_ttl_hours: int = Field(default=24, gt=0)
    # Durée de validité du lien de réinitialisation du mot de passe
    password_reset_ttl_minutes: int = Field(default=30, gt=0)
    # Délai minimal entre deux emails du même type pour un compte : empêche d'inonder une boîte
    email_cooldown_seconds: int = Field(default=60, ge=0)
    # True en production (HTTPS) ; false en développement local, servi en HTTP
    auth_cookie_secure: bool = True
    # Chemin vu par le navigateur, qui passe par le proxy Vite (/api/auth/... → /auth/...)
    auth_cookie_path: str = "/api/auth"

    # Templates (docs/technical/templates.md) : durée pendant laquelle un template supprimé
    # reste en base avant d'être purgé définitivement
    deleted_template_retention_days: int = Field(default=30, gt=0)

    # Images des tuiles (docs/technical/images.md) : taille maximale du fichier envoyé, à garder
    # alignée sur la limite de corps du reverse proxy (10 Mio)
    image_upload_max_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    # Nombre maximal de pixels de l'image décodée : protège contre les bombes de décompression
    image_max_source_pixels: int = Field(default=40_000_000, gt=0)
    # Nombre maximal d'images envoyées par un compte sur une heure glissante (contre les abus)
    image_uploads_per_hour_max: int = Field(default=120, gt=0)
    # Jours pendant lesquels une image qu'aucune tuile n'utilise est gardée avant d'être effacée
    # par le ramasse-miettes (scripts/purge_unused_images.py)
    unused_image_retention_days: int = Field(default=7, gt=0)
    # Stockage S3 des images. En développement, SeaweedFS (compose.yaml) : ses valeurs sont dans
    # .env.example. Sans adresse, boto3 vise AWS S3 ; sans clés, il cherche ses identifiants
    # habituels (variables AWS_*, rôle de la machine).
    image_s3_endpoint_url: str | None = None
    image_s3_bucket: str = "tierlist-images"
    image_s3_region: str = "us-east-1"
    image_s3_access_key_id: str | None = None
    image_s3_secret_access_key: SecretStr | None = None
    # Délai des appels au stockage (connexion, puis lecture de la réponse)
    image_s3_timeout_seconds: int = Field(default=10, gt=0)
    # Adresse publique des images (CDN ou bucket) : l'URL d'une image est cette adresse suivie
    # de sa clé. 127.0.0.1 plutôt que localhost : le port de SeaweedFS n'est publié qu'en IPv4.
    image_public_base_url: str = "http://127.0.0.1:8333/tierlist-images"

    # Connexion avec Google (client OAuth « Application Web » de la Google Cloud Console).
    # Sans identifiants, le bouton Google renvoie vers /login avec une erreur explicite.
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    # Doit figurer à l'identique dans les « URI de redirection autorisés » du client Google
    google_redirect_uri: str = "http://localhost:5173/api/auth/google/callback"
    # Temps laissé à l'utilisateur sur la page de Google avant que la tentative expire
    google_login_attempt_ttl_minutes: int = Field(default=10, gt=0)
    # Délai des appels vers Google (échange du code, clés publiques)
    google_http_timeout_seconds: int = Field(default=10, gt=0)

    # Envoi des emails (docs/technical/emails.md). Sans SMTP_HOST, aucun email ne part : l'envoi est
    # seulement journalisé. En développement, Mailpit (compose.yaml) les reçoit sur le port 1025.
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, gt=0)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    # STARTTLS : chiffre la connexion (port 587). false seulement pour Mailpit en local.
    smtp_starttls: bool = True
    smtp_timeout_seconds: int = Field(default=10, gt=0)
    # Expéditeur, ex. "TierList <no-reply@example.com>" : son domaine doit être autorisé (SPF/DKIM)
    email_from: str = "TierList <no-reply@localhost>"
    # Adresse du frontend vue par l'utilisateur : base des liens envoyés par email
    frontend_base_url: str = "http://localhost:5173"

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    # Les champs obligatoires sont lus depuis l'environnement / .env par pydantic-settings,
    # ce que Pyright ne peut pas savoir statiquement.
    return Settings()  # pyright: ignore[reportCallIssue]
