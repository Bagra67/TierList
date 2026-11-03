# Préfixe de l'API sur l'origine de l'application : le frontend est servi à la racine, l'API sous
# /api (docs/technical/deployment.md). Les cookies (AUTH_COOKIE_PATH, ROOM_COOKIE_PATH) et
# GOOGLE_REDIRECT_URI le contiennent.
API_PREFIX = "/api"

FRONTEND_ASSETS_PATH = "/assets"
FRONTEND_INDEX_FILE = "index.html"
FRONTEND_ASSETS_CACHE_CONTROL = "public, max-age=31536000, immutable"
FRONTEND_NO_CACHE = "no-cache"
