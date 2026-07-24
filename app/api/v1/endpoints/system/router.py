from fastapi import APIRouter

from app.api.v1.endpoints.system.health import health
from app.api.v1.endpoints.system.sync_instruments import sync_instruments

router = APIRouter(prefix="/system", tags=["system"])
router.add_api_route("/health", health, methods=["GET"])
router.add_api_route("/sync-instruments", sync_instruments, methods=["POST"])
