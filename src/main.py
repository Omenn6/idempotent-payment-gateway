from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

from src.api.operations import router as operations_router
from src.services.provider import (
    restart_pending_operations_helper,
    shutdown_background_tasks,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await restart_pending_operations_helper()
    yield
    await shutdown_background_tasks(timeout=10.0)


app = FastAPI(
    lifespan=lifespan,
    title="Idempotent Payment Gateway API",
    description="Сервис идемпотентного платежного шлюза с гарантированной обработкой операций и отказоустойчивостью.",
    version="1.0.0",
)

app.include_router(operations_router)

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=True)
