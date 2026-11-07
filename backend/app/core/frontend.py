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
    async def get_response(self, path: str, scope: Scope) -> Response:
        response: Response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = FRONTEND_ASSETS_CACHE_CONTROL
        return response


def _root_file(dist: Path, path: str) -> Path | None:
    if not path:
        return None
    candidate: Path = (dist / path).resolve()
    if not candidate.is_relative_to(dist) or not candidate.is_file():
        return None
    return candidate


def mount_frontend_after_api(app: FastAPI, existing_dist: Path) -> None:
    resolved_dist: Path = existing_dist.resolve()
    index_file: Path = resolved_dist / FRONTEND_INDEX_FILE
    app.mount(
        FRONTEND_ASSETS_PATH,
        _ImmutableStaticFiles(directory=resolved_dist / FRONTEND_ASSETS_PATH.lstrip("/")),
        name="frontend-assets",
    )

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if f"/{path}" == API_PREFIX:
            raise HTTPException(status_code=404)
        root_file: Path | None = _root_file(resolved_dist, path)
        return FileResponse(
            root_file if root_file is not None else index_file,
            headers={"Cache-Control": FRONTEND_NO_CACHE},
        )
