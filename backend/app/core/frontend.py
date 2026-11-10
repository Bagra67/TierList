from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from app.constants.api import (
    API_PREFIX,
    FRONTEND_ASSETS_CACHE_CONTROL,
    FRONTEND_ASSETS_PATH,
    FRONTEND_CLIENT_CONFIG_ELEMENT_ID,
    FRONTEND_HEAD_END,
    FRONTEND_INDEX_FILE,
    FRONTEND_NO_CACHE,
)
from app.schemas.client_config import ClientConfigResponse


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


def _index_with_client_config(index_html: str, client_config: ClientConfigResponse) -> str:
    config_json: str = client_config.model_dump_json().replace("<", "\\u003c")
    config_element: str = (
        f'<script type="application/json" id="{FRONTEND_CLIENT_CONFIG_ELEMENT_ID}">'
        f"{config_json}</script>"
    )
    return index_html.replace(FRONTEND_HEAD_END, config_element + FRONTEND_HEAD_END, 1)


def mount_frontend_after_api(
    app: FastAPI, existing_dist: Path, client_config: ClientConfigResponse
) -> None:
    resolved_dist: Path = existing_dist.resolve()
    index_file: Path = resolved_dist / FRONTEND_INDEX_FILE
    index_html: str = _index_with_client_config(
        index_file.read_text(encoding="utf-8"), client_config
    )
    app.mount(
        FRONTEND_ASSETS_PATH,
        _ImmutableStaticFiles(directory=resolved_dist / FRONTEND_ASSETS_PATH.lstrip("/")),
        name="frontend-assets",
    )

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def frontend(path: str) -> Response:
        if f"/{path}" == API_PREFIX:
            raise HTTPException(status_code=404)
        root_file: Path | None = _root_file(resolved_dist, path)
        if root_file is None or root_file == index_file:
            return HTMLResponse(index_html, headers={"Cache-Control": FRONTEND_NO_CACHE})
        return FileResponse(root_file, headers={"Cache-Control": FRONTEND_NO_CACHE})
