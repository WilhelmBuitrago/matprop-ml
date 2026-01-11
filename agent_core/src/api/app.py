from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware
from .router import router
from .router import v1_lifespan

app = FastAPI(title="Agent Core API", version="0.1.0", lifespan=v1_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
