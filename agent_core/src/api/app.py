from fastapi import APIRouter, FastAPI
from .router import router

app = FastAPI(title="Agent Core API", version="0.1.0")
app.include_router(router)
