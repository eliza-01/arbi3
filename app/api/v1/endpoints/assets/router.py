from fastapi import APIRouter

from app.api.v1.endpoints.assets.list_assets import list_assets

router = APIRouter(prefix="/assets", tags=["assets"])
router.add_api_route("", list_assets, methods=["GET"])
