from fastapi import FastAPI

from app.routers import items

app = FastAPI(
    title="TierList API",
    description="Backend FastAPI de l'application TierList",
    version="0.1.0",
)

app.include_router(items.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Bienvenue sur l'API TierList"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
