import base64

from pydantic import BaseModel

from app.exceptions.pagination import InvalidCursorError

BASE64_BLOCK = 4


def encode_cursor(position: BaseModel) -> str:
    return base64.urlsafe_b64encode(position.model_dump_json().encode()).decode().rstrip("=")


def decode_cursor[Position: BaseModel](raw: str, position_type: type[Position]) -> Position:
    padded: str = raw + "=" * (-len(raw) % BASE64_BLOCK)
    try:
        return position_type.model_validate_json(base64.urlsafe_b64decode(padded))
    except ValueError as exc:
        raise InvalidCursorError(raw) from exc
