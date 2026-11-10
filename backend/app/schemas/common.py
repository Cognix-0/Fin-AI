from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, PlainSerializer

T = TypeVar("T")

# Money is stored as Decimal for exact arithmetic but sent to clients as a JSON number.
Money = Annotated[
    Decimal,
    PlainSerializer(lambda v: float(v), return_type=float, when_used="json"),
]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


def ok(data=None, message: str | None = None) -> dict:
    """Standard success envelope used by every endpoint."""
    body: dict = {"success": True, "data": data}
    if message:
        body["message"] = message
    return body
