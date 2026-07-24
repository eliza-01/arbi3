from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.container import Container


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = Container()
    app.state.container = container
    await container.start()
    try:
        yield
    finally:
        await container.stop()
