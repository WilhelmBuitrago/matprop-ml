from fastapi import FastAPI
from matprop_ml.api.router import router

app = FastAPI(
    title="MatProp ML API",
    version="0.1.0",
)

app.include_router(router)
