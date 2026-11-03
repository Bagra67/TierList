from typing import Annotated

from pydantic import StringConstraints

from app.constants.auth import DISPLAY_NAME_MAX_LENGTH

DisplayName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=DISPLAY_NAME_MAX_LENGTH),
]
