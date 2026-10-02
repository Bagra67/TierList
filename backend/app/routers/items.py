from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/items", tags=["items"])


class ItemCreate(BaseModel):
    name: str
    tier: str = "C"


class Item(ItemCreate):
    id: int


# Stockage en mémoire (exemple) : remplacé plus tard par une vraie base de données
_items: dict[int, Item] = {}


@router.get("/")
def list_items() -> list[Item]:
    return list(_items.values())


@router.get("/{item_id}")
def get_item(item_id: int) -> Item:
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item introuvable")
    return _items[item_id]


@router.post("/", status_code=201)
def create_item(payload: ItemCreate) -> Item:
    item = Item(id=len(_items) + 1, **payload.model_dump())
    _items[item.id] = item
    return item
