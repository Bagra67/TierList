from typing import Literal

REFRESH_TOKEN_COOKIE = "refresh_token"
GOOGLE_LOGIN_COOKIE = "google_login"
GOOGLE_BAN_NOTICE_COOKIE = "google_ban_notice"
GOOGLE_COOKIE_SUBPATH = "/google"

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
GOOGLE_LOGIN_TOKEN_TYPE = "google_login"
GOOGLE_BAN_NOTICE_TOKEN_TYPE = "google_ban_notice"
EMAIL_VERIFICATION_TOKEN_TYPE = "email_verification"
PASSWORD_RESET_TOKEN_TYPE = "password_reset"
EMAIL_FINGERPRINT_LENGTH = 16
PASSWORD_FINGERPRINT_LENGTH = 16
# Longueur minimale de JWT_SECRET_KEY : 256 bits pour HS256
JWT_SECRET_KEY_MIN_LENGTH = 32
REFRESH_TOKEN_BYTES = 32
DUMMY_PASSWORD_BYTES = 16
GOOGLE_STATE_BYTES = 32
GOOGLE_NONCE_BYTES = 32
# RFC 7636 : le vérificateur PKCE fait de 43 à 128 caractères (64 octets → 86 caractères)
PKCE_VERIFIER_BYTES = 64

GOOGLE_PROVIDER = "google"

EMAIL_MAX_LENGTH = 320
DISPLAY_NAME_MAX_LENGTH = 50
PASSWORD_MAX_LENGTH = 128
PASSWORD_HASH_MAX_LENGTH = 255
REFRESH_TOKEN_HASH_LENGTH = 64
PROVIDER_MAX_LENGTH = 20
PROVIDER_SUBJECT_MAX_LENGTH = 255
# Borne haute d'un token reçu par email : rejette une entrée démesurée avant tout décodage
EMAIL_TOKEN_MAX_LENGTH = 2048

FRONTEND_HOME = "/"
FRONTEND_LOGIN = "/login"
FRONTEND_VERIFY_EMAIL = "/verify-email"
FRONTEND_RESET_PASSWORD = "/reset-password"
TOKEN_PARAM = "token"
LOGIN_ERROR_PARAM = "error"
CONFIRM_PARAM = "confirm"

DELETE_ACCOUNT_STEP = "delete-account"
GoogleNextStep = Literal["delete-account"]

GOOGLE_ERROR_CANCELLED = "google_cancelled"
GOOGLE_ERROR_EMAIL_NOT_VERIFIED = "google_email_not_verified"
GOOGLE_ERROR_UNAVAILABLE = "google_unavailable"
GOOGLE_ERROR_FAILED = "google_failed"
GOOGLE_ERROR_ACCOUNT_BANNED = "google_account_banned"
GOOGLE_ACCESS_DENIED = "access_denied"
