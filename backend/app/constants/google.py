"""Valeurs fixées par Google (OpenID Connect).

Référence : https://developers.google.com/identity/openid-connect/openid-connect
"""

GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
GOOGLE_SCOPES = "openid email profile"
GOOGLE_ID_TOKEN_ALGORITHM = "RS256"
PKCE_CHALLENGE_METHOD = "S256"
# Laisse choisir le compte quand plusieurs sont ouverts dans le navigateur
GOOGLE_PROMPT = "select_account"
