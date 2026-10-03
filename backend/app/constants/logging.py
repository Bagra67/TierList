# Seuls les loggers de l'application (« app » et ses enfants : app.main, app.db…) sont
# configurés ; uvicorn garde sa propre configuration (option --log-level).
APP_LOGGER = "app"
