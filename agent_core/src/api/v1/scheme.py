# agent_core/tools/api/v1/scheme.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class Tools(BaseModel):
    tools: List[Dict[str, Any]]
