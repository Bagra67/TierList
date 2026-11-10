from pydantic import BaseModel, Field


class ClientConfigResponse(BaseModel):
    """Réglages publics lus par le frontend au démarrage.

    Le même build du frontend sert tous les environnements.
    """

    sentry_dsn: str | None = Field(
        description="DSN Sentry du navigateur ; null quand le suivi des erreurs est désactivé."
    )
    environment: str = Field(description="Environnement transmis à Sentry (staging, production…).")
    release: str = Field(description="Version qui tourne, la même que celle de /health.")
