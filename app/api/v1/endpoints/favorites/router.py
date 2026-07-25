from fastapi import APIRouter

from app.api.v1.endpoints.favorites.add_favorite import add_favorite
from app.api.v1.endpoints.favorites.delete_favorite import delete_favorite
from app.api.v1.endpoints.favorites.list_favorites import list_favorites

router = APIRouter(prefix="/favorites", tags=["favorites"])
router.add_api_route("", list_favorites, methods=["GET"])
router.add_api_route(
    "/{asset_id}/{exchange_a}/{exchange_b}", add_favorite, methods=["POST"]
)
router.add_api_route(
    "/{asset_id}/{exchange_a}/{exchange_b}", delete_favorite, methods=["DELETE"]
)
