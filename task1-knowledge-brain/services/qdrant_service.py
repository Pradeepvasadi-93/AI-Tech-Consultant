"""Qdrant retrieval helpers used by the API and downstream agents."""
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config import settings
from services.embedder import embed_query


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    if not settings.QDRANT_URI or not settings.QDRANT_API_KEY:
        raise RuntimeError("QDRANT_URI and QDRANT_API_KEY must be configured")
    return QdrantClient(
        url=settings.QDRANT_URI,
        api_key=settings.QDRANT_API_KEY,
        timeout=30,
    )


def search_enterprise_knowledge(query: str, limit: int = 8) -> list[dict]:
    """Return ranked text/image evidence with stable source metadata."""
    if not query or not query.strip():
        raise ValueError("query must be non-empty")
    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50")

    vector = embed_query(query)
    response = get_qdrant_client().query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=vector,
        limit=limit,
        with_payload=True,
    )

    results = []
    for point in response.points:
        payload = point.payload or {}
        source_url = payload.get("source_url") or payload.get("url")
        results.append({
            "chunk_id": payload.get("chunk_id"),
            "content": payload.get("text", ""),
            "title": payload.get("title", ""),
            "source_url": source_url,
            "image_url": payload.get("image_url"),
            "content_type": payload.get("content_type", "text"),
            "score": float(point.score),
        })
    return results
