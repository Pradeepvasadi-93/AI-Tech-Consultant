import hashlib
import re


DEFAULT_CHUNK_SIZE = 1200
DEFAULT_OVERLAP = 200


def create_chunk_id(source_url, index, content):
    """Create a reproducible ID for a chunk."""
    value = f"{source_url}|{index}|{content}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def split_oversized_text(text, chunk_size, overlap):
    """Split long text without unnecessarily breaking words."""
    pieces = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Prefer a nearby word boundary.
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        piece = text[start:end].strip()

        if piece:
            pieces.append(piece)

        if end >= len(text):
            break

        # Guarantee forward progress.
        start = max(end - overlap, start + 1)

    return pieces


def split_text(text, chunk_size=DEFAULT_CHUNK_SIZE,
               overlap=DEFAULT_OVERLAP):
    """Split article text by paragraphs, then by size."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    if not isinstance(text, str) or not text.strip():
        return []

    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]

    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current)
                current = ""

            chunks.extend(
                split_oversized_text(paragraph, chunk_size, overlap)
            )
            continue

        candidate = f"{current}\n{paragraph}" if current else paragraph

        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)

            # Carry a suffix into the next chunk for continuity.
            suffix = current[-overlap:] if overlap and current else ""
            current = f"{suffix} {paragraph}".strip()

            if len(current) > chunk_size:
                chunks.extend(
                    split_oversized_text(current, chunk_size, overlap)
                )
                current = ""

    if current:
        chunks.append(current)

    return chunks


def chunk_document(document, chunk_size=DEFAULT_CHUNK_SIZE,
                   overlap=DEFAULT_OVERLAP):
    """Convert one saved document into searchable chunks."""
    source_url = document.get("url", "")
    chunks = []

    text_parts = split_text(
        document.get("text", ""),
        chunk_size=chunk_size,
        overlap=overlap,
    )

    for index, content in enumerate(text_parts):
        chunks.append({
            "chunk_id": create_chunk_id(source_url, index, content),
            "source_url": source_url,
            "chunk_index": index,
            "content_type": "text",
            "text": content,
        })

    # Keep image descriptions independently searchable.
    next_index = len(chunks)
    images = document.get("images", [])

    for image in images:
        if not isinstance(image, dict):
            continue

        description = (
            image.get("description")
            or image.get("alt")
            or ""
        ).strip()

        if not description:
            continue

        image_url = image.get("url", "")

        chunks.append({
            "chunk_id": create_chunk_id(
                source_url, next_index, description
            ),
            "source_url": source_url,
            "chunk_index": next_index,
            "content_type": "image",
            "image_url": image_url,
            "text": description,
        })

        next_index += 1

    return chunks
