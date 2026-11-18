import uuid
from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ConfigDict

from app.core.cursor import decode_cursor, encode_cursor, split_page
from app.exceptions.pagination import InvalidCursorError


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")

    at: datetime
    id: uuid.UUID


POSITION = Position(at=datetime(2026, 11, 18, 12, 30, 15, 123456, tzinfo=UTC), id=uuid.uuid4())


def test_a_cursor_gives_back_its_position():
    assert decode_cursor(encode_cursor(POSITION), Position) == POSITION


def test_a_cursor_is_safe_in_an_address():
    cursor: str = encode_cursor(POSITION)

    assert all(character.isalnum() or character in "-_" for character in cursor)


@pytest.mark.parametrize(
    "raw",
    ["not a cursor", "", "e30", encode_cursor(Position.model_construct(at=POSITION.at))],
    ids=["unreadable", "empty", "empty-object", "missing-field"],
)
def test_an_invalid_cursor_is_refused(raw: str):
    with pytest.raises(InvalidCursorError):
        decode_cursor(raw, Position)


def test_a_page_with_more_rows_gives_its_last_row_for_the_cursor():
    assert split_page([1, 2, 3], 2) == ([1, 2], 2)


def test_the_last_page_gives_no_row_for_a_cursor():
    assert split_page([1, 2], 2) == ([1, 2], None)
