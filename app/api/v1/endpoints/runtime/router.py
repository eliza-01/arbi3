from fastapi import APIRouter

from app.api.v1.endpoints.runtime.get_settings import get_runtime_settings
from app.api.v1.endpoints.runtime.update_interval import update_runtime_interval
from app.api.v1.endpoints.runtime.update_mode import update_runtime_mode

router = APIRouter(prefix="/runtime", tags=["runtime"])
router.add_api_route("/settings", get_runtime_settings, methods=["GET"])
router.add_api_route("/mode", update_runtime_mode, methods=["PUT"])
router.add_api_route("/interval", update_runtime_interval, methods=["PUT"])
