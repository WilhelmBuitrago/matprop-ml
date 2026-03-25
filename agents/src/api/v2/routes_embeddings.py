"""Embeddings endpoints under API v2."""

import logging
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .service import EmbeddingsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


class EmbeddingRequest(BaseModel):
    """Request body for embeddings endpoint."""

    texts: List[str] = Field(..., min_items=1, description="List of texts to embed")


class EmbeddingResponse(BaseModel):
    """Response body for embeddings endpoint."""

    embeddings: List[List[float]] = Field(..., description="Embedding vectors")


@router.post("", response_model=EmbeddingResponse)
async def embed_texts(request: EmbeddingRequest) -> EmbeddingResponse:
    """Embed input texts using the configured embeddings model."""
    if not request.texts:
        raise HTTPException(status_code=400, detail="texts list cannot be empty")

    try:
        embeddings = EmbeddingsService().embed_texts(request.texts)
        return EmbeddingResponse(embeddings=embeddings)
    except RuntimeError as exc:
        logger.error("Embedding failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Embedding service failed: {exc}",
        ) from exc
    except Exception as exc:  # pragma: no cover
        logger.error("Unexpected embeddings error: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc
