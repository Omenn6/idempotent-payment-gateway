import uvicorn
from fastapi import FastAPI

from src.api.operations import router as operations_router

app = FastAPI()

app.include_router(operations_router)


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=True)
