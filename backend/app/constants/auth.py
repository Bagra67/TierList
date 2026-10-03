from typing import Literal

# --- Cookies -------------------------------------------------------------------------------
REFRESH_TOKEN_COOKIE = "refresh_token"
# Tentative de connexion Google en cours (state, nonce, vérificateur PKCE)
GOOGLE_LOGIN_COOKIE = "google_login"
# Sous-chemin du cookie google_login, sous AUTH_COOKIE_PATH
GOOGLE_COOKIE_SUBPATH = "/google"

# --- Tokens --------------------------------------------------------------------------------
# HS256 : access tokens et cookie google_login, signés avec JWT_SECRET_KEY
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
GOOGLE_LOGIN_TOKEN_TYPE = "google_login"
# Longueur minimale de JWT_SECRET_KEY : 256 bits pour HS256
JWT_SECRET_KEY_MIN_LENGTH = 32
# Octets aléatoires des secrets générés (secrets.token_urlsafe)
REFRESH_TOKEN_BYTES = 32
# Mot de passe aléatoire du hash factice (égalise le temps de réponse d'un email inconnu)
DUMMY_PASSWORD_BYTES = 16
GOOGLE_STATE_BYTES = 32
GOOGLE_NONCE_BYTES = 32
# RFC 7636 : le vérificateur PKCE fait de 43 à 128 caractères (64 octets → 86 caractères)
PKCE_VERIFIER_BYTES = 64

# --- Fournisseurs d'identité ---------------------------------------------------------------
GOOGLE_PROVIDER = "google"

# --- Longueurs (liées au schéma de la base : les changer demande une migration) ------------
EMAIL_MAX_LENGTH = 320
DISPLAY_NAME_MAX_LENGTH = 50
# Borne haute du mot de passe : limite le coût du hachage Argon2 sur des entrées démesurées
PASSWORD_MAX_LENGTH = 128
PASSWORD_HASH_MAX_LENGTH = 255
# Hash SHA-256 en hexadécimal
REFRESH_TOKEN_HASH_LENGTH = 64
PROVIDER_MAX_LENGTH = 20
PROVIDER_SUBJECT_MAX_LENGTH = 255

# --- Retour vers le frontend (même origine, via le proxy) ----------------------------------
FRONTEND_HOME = "/"
FRONTEND_LOGIN = "/login"
# Paramètre de requête qui transmet une erreur à la page de connexion
LOGIN_ERROR_PARAM = "error"
# Paramètre de requête qui demande à la page d'accueil de reprendre une étape
CONFIRM_PARAM = "confirm"

# Seule étape qu'on peut reprendre après Google : une liste fermée évite toute redirection ouverte
DELETE_ACCOUNT_STEP = "delete-account"
GoogleNextStep = Literal["delete-account"]

# Codes d'erreur du retour de Google, expliqués par la page de connexion du frontend
GOOGLE_ERROR_CANCELLED = "google_cancelled"
GOOGLE_ERROR_EMAIL_NOT_VERIFIED = "google_email_not_verified"
GOOGLE_ERROR_UNAVAILABLE = "google_unavailable"
GOOGLE_ERROR_FAILED = "google_failed"
# Erreur OAuth renvoyée par Google quand l'utilisateur refuse ou ferme sa page
GOOGLE_ACCESS_DENIED = "access_denied"
