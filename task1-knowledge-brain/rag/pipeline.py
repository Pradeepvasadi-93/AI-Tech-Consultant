import os
import argparse
import hashlib
import json
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

import logfire
from qdrant_client import QdrantClient, models

from app.config import settings
from parsing.sitemap_parser import parse_sitemap, parse_sitemap_entries
from ingestion.crawler import crawl_articles
from chunking.chunker import chunk_document
from services.embedder import embed_texts, get_embedding_dim


QDRANT_URI = settings.QDRANT_URI
QDRANT_API_KEY = settings.QDRANT_API_KEY

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DOCUMENT_DIR = PROJECT_ROOT / "ingestion" / "documents"
CHUNK_DIR = PROJECT_ROOT / "chunking" / "output"
EMBEDDING_DIR = PROJECT_ROOT / "embeddings" / "output"

BATCH_SIZE = 50
POINT_NAMESPACE = uuid.UUID(
    "b6c0f4a0-8f6e-4d47-a80b-bf6ad620d612"
)

logfire.configure(service_name="knowledge-brain-ingestion")
LAST_CRAWL_STATS: dict[str, int] = {}


# ---------------------------------------------------------
# Utilities
# ---------------------------------------------------------

def validate_url(url: str) -> str:
    """Validate the basic syntax of an HTTP(S) URL."""
    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL must start with http:// or https://")

    if not parsed.hostname:
        raise ValueError("URL must contain a hostname")

    if parsed.username or parsed.password:
        raise ValueError("URLs containing embedded credentials are not allowed")

    return url


def resolve_url_mode(url: str, mode: str) -> str:
    """Resolve auto mode or validate the explicitly selected mode."""
    if mode in {"sitemap", "page"}:
        return mode

    parsed = urlparse(url)
    path = parsed.path.lower()

    if path.endswith(".xml") or "sitemap" in path:
        return "sitemap"

    return "page"


def stable_chunk_id(chunk: dict[str, Any]) -> str:
    """Generate a stable ID even if the chunker doesn't supply chunk_id."""
    existing_id = chunk.get("chunk_id")

    if existing_id:
        return str(existing_id)

    identity = "|".join(
        [
            str(chunk.get("source_url", "")),
            str(chunk.get("chunk_index", "")),
            str(chunk.get("content_type", "text")),
            str(chunk.get("text", "")),
            str(chunk.get("image_url", "")),
        ]
    )

    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def point_id_for_chunk(chunk_id: str) -> str:
    """Create a deterministic Qdrant-compatible UUID."""
    return str(uuid.uuid5(POINT_NAMESPACE, chunk_id))


def save_processed_files(
    data: list | dict,
    output_dir: Path,
    filename: str,
) -> str:
    """
    Save chunk or embedding JSON.

    Example:
      chunking/output/article.json
      embeddings/output/article.json
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Avoid accidental path traversal from a filename.
    safe_filename = Path(filename).name
    if safe_filename.endswith(".json"):
        safe_filename = safe_filename[:-5]

    destination = output_dir / f"{safe_filename}.json"
    temporary = destination.with_suffix(".json.tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    # Replace atomically after the JSON has been written.
    temporary.replace(destination)
    return str(destination)


def load_json_document(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        document = json.load(file)

    if not isinstance(document, dict):
        raise ValueError(f"{path} must contain a JSON object")

    if not document.get("url"):
        raise ValueError(f"{path} is missing the required 'url' field")

    return document


# ---------------------------------------------------------
# Qdrant
# ---------------------------------------------------------

def get_qdrant_client() -> QdrantClient:
    """Create a Qdrant Cloud client using the project's settings."""
    if not QDRANT_URI:
        raise ValueError("QDRANT_URI is not configured")

    if not QDRANT_API_KEY:
        raise ValueError("QDRANT_API_KEY is not configured")

    return QdrantClient(
        url=QDRANT_URI,
        api_key=QDRANT_API_KEY,
        timeout=30,
    )


def ensure_collection(
    client: QdrantClient,
    dimensions: int,
    recreate: bool = False,
) -> None:
    """
    Ensure that the collection exists with the expected vector size.

    Recreating a collection deletes its existing vectors.
    """
    collection = settings.QDRANT_COLLECTION

    if not collection:
        raise ValueError("QDRANT_COLLECTION is not configured")

    if recreate and client.collection_exists(collection):
        client.delete_collection(collection)
        logfire.warning(
            "Deleted existing Qdrant collection",
            collection=collection,
        )

    if not client.collection_exists(collection):
        client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(
                size=dimensions,
                distance=models.Distance.COSINE,
            ),
        )
        logfire.info(
            "Created Qdrant collection",
            collection=collection,
            dimensions=dimensions,
        )
        return

    info = client.get_collection(collection)
    vectors_config = info.config.params.vectors

    # This pipeline uses a single unnamed vector, not named vectors.
    if not isinstance(vectors_config, models.VectorParams):
        raise ValueError(
            f"Collection '{collection}' uses named or unsupported vectors. "
            "Configure the pipeline for that schema or use a separate collection."
        )

    if vectors_config.size != dimensions:
        raise ValueError(
            f"Collection '{collection}' has {vectors_config.size}-dimensional "
            f"vectors, but the configured embedder reports {dimensions}. "
            "Use the matching embedding model/collection; do not mix models."
        )

    if vectors_config.distance != models.Distance.COSINE:
        raise ValueError(
            f"Collection '{collection}' does not use cosine distance."
        )

def ensure_payload_indexes(client: QdrantClient) -> None:
    """Create the payload indexes required by Qdrant filters."""
    collection_name = settings.QDRANT_COLLECTION

    client.create_payload_index(
        collection_name=collection_name,
        field_name="source_url",
        field_schema=models.PayloadSchemaType.KEYWORD,
        wait=True,
    )

    logfire.info(
        "Qdrant payload index created or verified",
        collection=collection_name,
        field="source_url",
    )

def upsert_points(
    client: QdrantClient,
    points: list[models.PointStruct],
) -> int:
    """Upload points in bounded batches."""
    collection = settings.QDRANT_COLLECTION

    for start in range(0, len(points), BATCH_SIZE):
        batch = points[start : start + BATCH_SIZE]

        client.upsert(
            collection_name=collection,
            points=batch,
            wait=True,
        )

    return len(points)


def remove_stale_chunks_for_url(
    client: QdrantClient,
    source_url: str,
    active_point_ids: set[str],
) -> int:
    """Delete obsolete chunks for a source only after replacement points are indexed."""
    source_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="source_url",
                match=models.MatchValue(value=source_url),
            )
        ]
    )
    stale_ids = []
    offset = None
    while True:
        records, next_offset = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=source_filter,
            limit=500,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        stale_ids.extend(
            str(record.id) for record in records
            if str(record.id) not in active_point_ids
        )
        if next_offset is None:
            break
        offset = next_offset

    for start in range(0, len(stale_ids), BATCH_SIZE):
        client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=models.PointIdsList(points=stale_ids[start:start + BATCH_SIZE]),
            wait=True,
        )
    return len(stale_ids)


def deactivate_removed_sitemap_urls(
    client: QdrantClient,
    sitemap_url: str,
    current_urls: list[str],
) -> int:
    """Mark missing help-center URLs as removed and deactivate their vectors."""
    from ingestion.manifest import load_manifest, save_manifest

    sitemap_host = urlparse(sitemap_url).hostname
    active = set(current_urls)
    manifest = load_manifest()
    removed_count = 0

    for page_url, entry in list(manifest.items()):
        parsed = urlparse(page_url)
        # Restrict deletion to this help-center namespace; do not deactivate
        # unrelated pages that may have been ingested manually.
        if parsed.hostname != sitemap_host or not parsed.path.startswith("/support/"):
            continue
        if page_url in active or entry.get("status") == "removed":
            continue

        entry["status"] = "removed"
        entry["removed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        manifest[page_url] = entry
        client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="source_url",
                            match=models.MatchValue(value=page_url),
                        )
                    ]
                )
            ),
            wait=True,
        )
        removed_count += 1

    if removed_count:
        save_manifest(manifest)
    return removed_count


# ---------------------------------------------------------
# Chunking, persistence, embedding and indexing
# ---------------------------------------------------------

def process_document(
    client: QdrantClient,
    document_path: Path,
    expected_dimensions: int,
) -> dict[str, int]:
    """
    Load a parsed document and run:
    chunk -> save chunks -> embed -> save embeddings -> index.
    """
    document = load_json_document(document_path)
    document_url = str(document["url"])
    filename = document_path.stem

    with logfire.span(
        "Process document",
        filename=filename,
        source_url=document_url,
    ):
        # 1. Chunk using the existing chunker.
        chunks = chunk_document(document)

        if not chunks:
            logfire.warning(
                "No chunks generated",
                filename=filename,
            )
            return {"chunks": 0, "embedded": 0, "indexed": 0}

        normalized_chunks: list[dict[str, Any]] = []

        for index, original_chunk in enumerate(chunks):
            chunk = dict(original_chunk)

            chunk.setdefault("source_url", document_url)
            chunk.setdefault("chunk_index", index)
            chunk.setdefault("content_type", "text")
            chunk["chunk_id"] = stable_chunk_id(chunk)

            if not str(chunk.get("text", "")).strip():
                logfire.warning(
                    "Skipping empty chunk",
                    filename=filename,
                    chunk_index=index,
                )
                continue

            normalized_chunks.append(chunk)

        if not normalized_chunks:
            return {"chunks": 0, "embedded": 0, "indexed": 0}

        # 2. Save the chunk records in the same format as run_chunking.py.
        chunk_path = save_processed_files(
            normalized_chunks,
            CHUNK_DIR,
            filename,
        )

        logfire.info(
            "Saved chunk file",
            path=chunk_path,
            chunks=len(normalized_chunks),
        )

        # 3. Embed only the chunk text.
        texts = [chunk["text"] for chunk in normalized_chunks]
        vectors = embed_texts(texts)

        if len(vectors) != len(normalized_chunks):
            raise ValueError(
                f"Embedder returned {len(vectors)} vectors for "
                f"{len(normalized_chunks)} chunks"
            )

        for vector in vectors:
            if len(vector) != expected_dimensions:
                raise ValueError(
                    f"Embedding dimension mismatch: expected "
                    f"{expected_dimensions}, got {len(vector)}"
                )

        # 4. Save embedding records in the same format as run_embeddings.py.
        embedding_records: list[dict[str, Any]] = []
        points: list[models.PointStruct] = []

        for chunk, vector in zip(normalized_chunks, vectors):
            record = {
                **chunk,
                "embedding": vector,
                # Add these fields to the persisted record.
                "embedding_dimensions": len(vector),
            }

            # Prefer the model name exposed by the embedder if available.
            record.setdefault(
                "embedding_model",
                getattr(settings, "EMBEDDING_MODEL", "configured-embedder"),
            )
            embedding_records.append(record)

            # Do not store the large vector again inside the Qdrant payload.
            payload = {
                key: value
                for key, value in chunk.items()
                if key != "embedding"
            }

            payload["source_url"] = chunk.get("source_url", document_url)
            payload["chunk_id"] = chunk["chunk_id"]

            points.append(
                models.PointStruct(
                    id=point_id_for_chunk(chunk["chunk_id"]),
                    vector=vector,
                    payload=payload,
                )
            )

        embedding_path = save_processed_files(
            embedding_records,
            EMBEDDING_DIR,
            filename,
        )

        logfire.info(
            "Saved embedding file",
            path=embedding_path,
            embeddings=len(embedding_records),
        )

        # 5. Index the vectors in Qdrant.
        indexed_count = upsert_points(client, points)
        active_point_ids = {str(point.id) for point in points}
        stale_deleted = remove_stale_chunks_for_url(
            client,
            document_url,
            active_point_ids,
        )

        logfire.info(
            "Indexed document",
            filename=filename,
            indexed=indexed_count,
            stale_chunks_deleted=stale_deleted,
        )

        return {
            "chunks": len(normalized_chunks),
            "embedded": len(vectors),
            "indexed": indexed_count,
        }


# ---------------------------------------------------------
# URL processing
# ---------------------------------------------------------

def process_url(
    url: str,
    mode: str = "auto",
    max_pages: int | None = None,
    delay: float = 1.0,
    process_images: bool = True,
) -> list[str]:
    """
    Resolve the URL as a sitemap or a single page, then crawl it.

    Returns the discovered/crawled URL list.
    """
    url = validate_url(url)
    resolved_mode = resolve_url_mode(url, mode)

    with logfire.span(
        "Resolve and crawl URL",
        url=url,
        mode=resolved_mode,
    ):
        sitemap_metadata = {}
        if resolved_mode == "sitemap":
            entries = parse_sitemap_entries(url)
            if not entries:
                raise ValueError(f"No page URLs found in sitemap: {url}")
            if max_pages is not None:
                entries = entries[:max_pages]
            urls = [entry["url"] for entry in entries]
            sitemap_metadata = {entry["url"]: entry for entry in entries}
        else:
            # A direct page URL is crawled as one page.
            urls = [url]

        logfire.info(
            "URLs selected for crawling",
            mode=resolved_mode,
            count=len(urls),
        )

        global LAST_CRAWL_STATS
        LAST_CRAWL_STATS = crawl_articles(
            urls=urls,
            delay=delay,
            max_images=2,
            process_images_enabled=process_images,
            sitemap_metadata=sitemap_metadata,
        )

        return urls


# ---------------------------------------------------------
# Complete pipeline
# ---------------------------------------------------------

def run_pipeline(
    url: str,
    mode: str = "auto",
    max_pages: int | None = None,
    delay: float = 1.0,
    process_images: bool = True,
    wipe: bool = False,
) -> dict[str, int]:
    started = time.perf_counter()
    totals = {
        "documents": 0,
        "chunks": 0,
        "embedded": 0,
        "indexed": 0,
        "failed": 0,
        "crawl_processed": 0,
        "crawl_skipped": 0,
        "crawl_failed": 0,
        "images_processed": 0,
        "images_failed": 0,
    }

    client: QdrantClient | None = None

    try:
        # Step 1: Crawl and save parsed JSON documents.
        selected_urls = process_url(
            url=url,
            mode=mode,
            max_pages=max_pages,
            delay=delay,
            process_images=process_images,
        )
        resolved_mode = resolve_url_mode(url, mode)
        for stat_key in ("processed", "skipped", "failed", "images_processed", "images_failed"):
            LAST_CRAWL_STATS.setdefault(stat_key, 0)
        totals["crawl_processed"] = LAST_CRAWL_STATS["processed"]
        totals["crawl_skipped"] = LAST_CRAWL_STATS["skipped"]
        totals["crawl_failed"] = LAST_CRAWL_STATS["failed"]
        totals["images_processed"] = LAST_CRAWL_STATS["images_processed"]
        totals["images_failed"] = LAST_CRAWL_STATS["images_failed"]

        # Step 2: Resolve the configured embedding dimension.
        dimensions = get_embedding_dim()

        # Step 3: Check Qdrant and the collection schema.
        client = get_qdrant_client()
        client.get_collections()  # Connection/credentials check.
        ensure_collection(client, dimensions, recreate=wipe)
        ensure_payload_indexes(client)

        if resolved_mode == "sitemap" and max_pages is None:
            removed = deactivate_removed_sitemap_urls(client, url, selected_urls)
            logfire.info("Sitemap removal sync completed", removed=removed)

        # Step 4: Process documents already saved by the crawler.
        DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
        document_paths = sorted(DOCUMENT_DIR.glob("*.json"))

        from ingestion.manifest import load_manifest
        current_manifest = load_manifest()
        selected_url_set = set(selected_urls)

        if not document_paths:
            logfire.warning(
                "No document JSON files found",
                directory=str(DOCUMENT_DIR),
            )
            totals["elapsed_seconds"] = round(time.perf_counter() - started, 2)
            if totals["crawl_failed"]:
                raise RuntimeError(
                    f"No documents were available and {totals['crawl_failed']} pages failed. "
                    "Review the manifest and retry."
                )
            return totals

        for document_path in document_paths:
            try:
                # Keep archived JSON for auditability, but never re-index removed pages.
                with document_path.open("r", encoding="utf-8") as source_file:
                    saved_document = json.load(source_file)
                saved_url = saved_document.get("url", "")
                # A limited smoke test or direct-page run should not unexpectedly
                # embed every historical JSON file in the documents directory.
                if (max_pages is not None or resolved_mode == "page") and saved_url not in selected_url_set:
                    continue
                manifest_entry = current_manifest.get(saved_url, {})
                if manifest_entry.get("status") == "removed":
                    continue
                if (
                    not wipe
                    and manifest_entry.get("status") == "processed"
                    and manifest_entry.get("content_hash")
                    and manifest_entry.get("indexed_content_hash") == manifest_entry.get("content_hash")
                ):
                    continue

                result = process_document(
                    client=client,
                    document_path=document_path,
                    expected_dimensions=dimensions,
                )

                totals["documents"] += 1
                for key in ("chunks", "embedded", "indexed"):
                    totals[key] += result[key]

                if saved_url in current_manifest:
                    current_manifest[saved_url]["indexed_content_hash"] = current_manifest[saved_url].get("content_hash")
                    current_manifest[saved_url]["indexed_at"] = time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                    )
                    from ingestion.manifest import save_manifest
                    save_manifest(current_manifest)

            except Exception:
                totals["failed"] += 1
                logfire.exception(
                    "Document processing failed",
                    document=str(document_path),
                )

        totals["elapsed_seconds"] = round(
            time.perf_counter() - started, 2
        )

        logfire.info("Pipeline finished", **totals)

        if totals["failed"] or totals["crawl_failed"]:
            raise RuntimeError(
                f"Pipeline incomplete: {totals['crawl_failed']} crawl failures and "
                f"{totals['failed']} document-processing failures. "
                "Review the manifest and Logfire errors, then rerun to resume."
            )

        return totals

    finally:
        if client is not None:
            client.close()


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Website RAG ingestion: crawl, chunk, embed and index."
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Sitemap URL or individual webpage URL",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "sitemap", "page"],
        default="auto",
        help="How to interpret --url (default: auto)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum sitemap URLs to crawl",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between page requests in seconds",
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Disable image processing",
    )
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="Delete and recreate the Qdrant collection",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than zero")

    if args.delay < 0:
        parser.error("--delay cannot be negative")

    try:
        totals = run_pipeline(
            url=args.url,
            mode=args.mode,
            max_pages=args.limit,
            delay=args.delay,
            process_images=not args.skip_images,
            wipe=args.wipe,
        )
        print(json.dumps(totals, indent=2))

    except Exception as exc:
        logfire.exception("Ingestion pipeline failed")
        parser.exit(1, f"Pipeline failed: {exc}\n")


if __name__ == "__main__":
    main()