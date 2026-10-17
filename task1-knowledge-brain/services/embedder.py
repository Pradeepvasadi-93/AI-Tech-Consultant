
import os
import time
from typing import Optional

import logfire
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings


load_dotenv()

BATCH_SIZE = 50

GEMINI_MODEL = "models/gemini-embedding-2-preview"
FALLBACK_MODEL = "sentence-transformers/all-mpnet-base-v2"

GEMINI_DIM = 3072
FALLBACK_DIM = 768

_active_model = None
_model_type: Optional[str] = None
_model_name: Optional[str] = None


def _probe_gemini():
    """Initialize Gemini and verify that embedding requests work."""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        logfire.warning(
            "GEMINI_API_KEY is not configured; "
            "Gemini embeddings will not be used."
        )
        return None

    try:
        model = GoogleGenerativeAIEmbeddings(
            model=GEMINI_MODEL,
            google_api_key=api_key,
        )

        # Verify API access before selecting Gemini.
        model.embed_query("embedding initialization probe")

        logfire.info(
            "Gemini embeddings initialized",
            model=GEMINI_MODEL,
            expected_dimensions=GEMINI_DIM,
        )
        return model

    except Exception as exc:
        logfire.warning(
            "Gemini initialization failed; trying local fallback",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return None


def _load_fallback():
    """Load the local sentence-transformers model."""
    from sentence_transformers import SentenceTransformer

    logfire.info(
        "Loading sentence-transformers fallback",
        model=FALLBACK_MODEL,
    )

    model = SentenceTransformer(FALLBACK_MODEL)

    # Fail early if the actual dimension differs from our expectation.
    actual_dim = model.get_sentence_embedding_dimension()

    if actual_dim != FALLBACK_DIM:
        raise RuntimeError(
            f"Expected {FALLBACK_DIM} dimensions, "
            f"but fallback returned {actual_dim}"
        )

    logfire.info(
        "Fallback embeddings initialized",
        model=FALLBACK_MODEL,
        dimensions=actual_dim,
    )

    return model


def _init():
    """Initialize one embedding model and keep it active."""
    global _active_model, _model_type, _model_name

    if _active_model is not None:
        return

    gemini = _probe_gemini()

    if gemini is not None:
        _active_model = gemini
        _model_type = "gemini"
        _model_name = GEMINI_MODEL
    else:
        _active_model = _load_fallback()
        _model_type = "fallback"
        _model_name = FALLBACK_MODEL


def get_embedding_dim() -> int:
    """Return the selected model's embedding dimension."""
    _init()

    if _model_type == "gemini":
        return GEMINI_DIM

    return FALLBACK_DIM


def get_embedding_model_info() -> dict:
    """Return the model identity for output metadata."""
    _init()

    return {
        "model_type": _model_type,
        "model_name": _model_name,
        "dimensions": get_embedding_dim(),
    }


def _embed_batch(batch: list[str]) -> list[list[float]]:
    """Embed a batch using the selected model."""
    if _model_type == "gemini":
        for attempt in range(4):
            try:
                vectors = _active_model.embed_documents(batch)

                if len(vectors) != len(batch):
                    raise RuntimeError(
                        "Gemini returned an unexpected number of vectors"
                    )

                return vectors

            except Exception as exc:
                error_text = str(exc).lower()

                is_rate_limit = any(
                    term in error_text
                    for term in (
                        "429",
                        "rate limit",
                        "rate_limit",
                        "quota",
                        "resource_exhausted",
                    )
                )

                if is_rate_limit and attempt < 3:
                    wait_seconds = 2 ** attempt

                    logfire.warning(
                        "Gemini rate limit; retrying",
                        attempt=attempt + 1,
                        max_attempts=4,
                        wait_seconds=wait_seconds,
                    )

                    time.sleep(wait_seconds)
                else:
                    logfire.error(
                        "Gemini batch embedding failed",
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )
                    raise

        raise RuntimeError(
            "Gemini rate limit persisted after four attempts"
        )

    vectors = _active_model.encode(
        batch,
        show_progress_bar=False,
        convert_to_numpy=True,
    )

    return vectors.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a query using the same model selected for documents."""
    _init()

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must be a non-empty string")

    if _model_type == "gemini":
        vector = _active_model.embed_query(query)
    else:
        vector = _active_model.encode(
            [query],
            show_progress_bar=False,
            convert_to_numpy=True,
        )[0].tolist()

    if len(vector) != get_embedding_dim():
        raise RuntimeError("Query embedding dimension mismatch")

    return vector


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts in batches and preserve their input order."""
    _init()

    if not texts:
        return []

    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("All texts must be non-empty strings")

    all_embeddings = []

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]

        with logfire.span(
            "Embed batch",
            model=_model_type,
            model_name=_model_name,
            start=start,
            batch_size=len(batch),
        ):
            vectors = _embed_batch(batch)

            if any(len(vector) != get_embedding_dim() for vector in vectors):
                raise RuntimeError("Document embedding dimension mismatch")

            all_embeddings.extend(vectors)

    return all_embeddings
