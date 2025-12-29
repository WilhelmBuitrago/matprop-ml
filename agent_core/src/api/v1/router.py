from fastapi import APIRouter, FastAPI
from .scheme import Tools
from tools.config import AVAILABLES_TOOLS


router = APIRouter()


@router.get("/tools", response_model=Tools)
def get_tools():
    return {"tools": AVAILABLES_TOOLS}


@router.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    print(AVAILABLES_TOOLS)
