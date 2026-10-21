# Préfixe de l'API sur l'origine de l'application : le frontend est servi à la racine, l'API sous
# /api (docs/technical/deployment.md). Les cookies (AUTH_COOKIE_PATH, ROOM_COOKIE_PATH) et
# GOOGLE_REDIRECT_URI le contiennent.
API_PREFIX = "/api"

# Build du frontend servi par FastAPI (app/core/frontend.py)
FRONTEND_ASSETS_PATH = "/assets"
FRONTEND_INDEX_FILE = "index.html"
# Fichiers de /assets : leur nom contient un hash de leur contenu, ils ne changent jamais
FRONTEND_ASSETS_CACHE_CONTROL = "public, max-age=31536000, immutable"
# index.html et les fichiers de la racine (favicon…) : toujours revalidés, pour qu'un déploiement
# soit vu tout de suite (index.html référence les nouveaux fichiers de /assets)
FRONTEND_NO_CACHE = "no-cache"
