from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as api_v1_router
from app.api.ws.quotes import quotes_websocket
from app.core.config import settings
from app.core.logging import configure_logging
from app.lifespan import lifespan

configure_logging()

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_v1_router)
app.add_api_websocket_route("/ws/quotes", quotes_websocket)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")
