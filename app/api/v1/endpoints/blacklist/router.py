from fastapi import APIRouter

from app.api.v1.endpoints.blacklist.add_blacklisted_asset import add_blacklisted_asset
from app.api.v1.endpoints.blacklist.delete_blacklisted_asset import delete_blacklisted_asset
from app.api.v1.endpoints.blacklist.list_blacklisted_assets import list_blacklisted_assets

router = APIRouter(prefix="/blacklist", tags=["blacklist"])
router.add_api_route("", list_blacklisted_assets, methods=["GET"])
router.add_api_route("/{asset_id}", add_blacklisted_asset, methods=["POST"])
router.add_api_route("/{asset_id}", delete_blacklisted_asset, methods=["DELETE"])
