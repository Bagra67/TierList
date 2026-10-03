from collections.abc import Mapping

from fastapi import HTTPException

from app.constants.error_codes import ErrorCode

ErrorParamValue = str | int | float


class AppHTTPException(HTTPException):
    """Erreur HTTP de l'API, identifiée par un code stable que le frontend traduit.

    detail reste un texte anglais destiné aux développeurs ; params alimente la traduction.
    """

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        detail: str,
        params: Mapping[str, ErrorParamValue] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=dict(headers) if headers is not None else None,
        )
        self.code = code
        self.params = dict(params) if params is not None else None
