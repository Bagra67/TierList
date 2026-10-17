"""Build du frontend (Vite) servi par FastAPI, sur la même origine que l'API
(docs/technical/deployment.md).

- /assets/* : fichiers hashés, cache long ;
- un fichier de la racine du build (favicon…) est servi s'il existe ;
- toute autre route renvoie index.html : le routeur du frontend affiche la page (SPA).

Les routes /api/* n'arrivent jamais ici : l'API est montée sous /api avant ce fallback, et répond
elle-même 404 (JSON) à une route inconnue.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from app.constants.api import (
    API_PREFIX,
    FRONTEND_ASSETS_CACHE_CONTROL,
    FRONTEND_ASSETS_PATH,
    FRONTEND_INDEX_FILE,
    FRONTEND_NO_CACHE,
)


class _ImmutableStaticFiles(StaticFiles):
    """Fichiers de /assets, avec un cache long : un nouveau build leur donne un nouveau nom."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response: Response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = FRONTEND_ASSETS_CACHE_CONTROL
        return response


def _root_file(dist: Path, path: str) -> Path | None:
    """Fichier de la racine du build demandé par `path`, ou None. Le chemin résolu doit rester
    dans le build : « ../ » ou un lien symbolique ne permettent pas d'en sortir."""
    if not path:
        return None
    candidate: Path = (dist / path).resolve()
    if not candidate.is_relative_to(dist) or not candidate.is_file():
        return None
    return candidate


def mount_frontend(app: FastAPI, dist: Path) -> None:
    """Sert le build `dist` (doit exister). À appeler après le montage de l'API."""
    resolved_dist: Path = dist.resolve()
    index_file: Path = resolved_dist / FRONTEND_INDEX_FILE
    app.mount(
        FRONTEND_ASSETS_PATH,
        _ImmutableStaticFiles(directory=resolved_dist / FRONTEND_ASSETS_PATH.lstrip("/")),
        name="frontend-assets",
    )

    # HEAD aussi : sondes de disponibilité et vérifications de lien ne demandent que les en-têtes
    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if f"/{path}" == API_PREFIX:
            # /api seul n'est pas une page : 404 JSON, comme une route inconnue de l'API
            raise HTTPException(status_code=404)
        root_file: Path | None = _root_file(resolved_dist, path)
        return FileResponse(
            root_file if root_file is not None else index_file,
            headers={"Cache-Control": FRONTEND_NO_CACHE},
        )
