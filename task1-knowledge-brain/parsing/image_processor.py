
import os
import base64
import tempfile
import mimetypes
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
import requests
import logfire
from openai import OpenAI
load_dotenv()

# Configuration
MODEL_NAME = os.getenv("OPENAI_VISION_MODEL", "gpt-4.1")
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
REQUEST_TIMEOUT = 20

client = None


def _get_openai_client():
    """Create the vision client only when image processing is requested."""
    global client
    if client is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required for image descriptions")
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return client


def download_image(url: str) -> str:
    """
    Download an HTTP(S) image and save it to a temporary file.
    Returns the local file path.
    """
    with logfire.span("Download Image", url=url):
        parsed_url = urlparse(url)

        if parsed_url.scheme not in {"http", "https"}:
            raise ValueError("Only HTTP and HTTPS image URLs are allowed.")

        if not parsed_url.hostname:
            raise ValueError("Invalid image URL.")

        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            stream=True,
            headers={"User-Agent": "KnowledgeBrainBot/1.0"},
        )

        try:
            response.raise_for_status()

            content_type = (
                response.headers.get("Content-Type", "")
                .split(";")[0]
                .strip()
                .lower()
            )

            allowed_types = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "image/gif": ".gif",
            }

            if content_type not in allowed_types:
                raise ValueError(
                    f"Unsupported image content type: {content_type or 'unknown'}"
                )

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_IMAGE_BYTES:
                raise ValueError("Image exceeds the 10 MB size limit.")

            tmp_fd, tmp_path = tempfile.mkstemp(
                suffix=allowed_types[content_type]
            )

            total_bytes = 0

            try:
                with os.fdopen(tmp_fd, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not chunk:
                            continue

                        total_bytes += len(chunk)

                        if total_bytes > MAX_IMAGE_BYTES:
                            raise ValueError(
                                "Image exceeds the 10 MB size limit."
                            )

                        file.write(chunk)

                if total_bytes == 0:
                    raise ValueError("Downloaded image is empty.")

                return tmp_path

            except Exception:
                Path(tmp_path).unlink(missing_ok=True)
                raise

        finally:
            response.close()


def describe_image(image_path: str) -> str:
    """
    Use OpenAI vision to describe a screenshot or website image.
    Returns a text description, or an empty string on failure.
    """
    with logfire.span("Describe Image", file=image_path):
        try:
            path = Path(image_path)

            mime_type, _ = mimetypes.guess_type(path.name)

            allowed_mime_types = {
                "image/jpeg",
                "image/png",
                "image/webp",
                "image/gif",
            }

            if mime_type not in allowed_mime_types:
                raise ValueError(f"Unsupported image type: {mime_type}")

            image_bytes = path.read_bytes()

            if len(image_bytes) > MAX_IMAGE_BYTES:
                raise ValueError("Image exceeds the 10 MB size limit.")

            encoded_image = base64.b64encode(image_bytes).decode("utf-8")
            image_data_url = f"data:{mime_type};base64,{encoded_image}"

            response = _get_openai_client().chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You analyze images for a website knowledge base. "
                            "Describe only what is visible. Do not invent "
                            "missing text, actions, or functionality."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Analyze this website image or screenshot. "
                                    "Identify visible UI labels, buttons, menus, "
                                    "form fields, important text, diagrams, "
                                    "and any clearly visible sequence of steps. "
                                    "Explain the image in concise, searchable "
                                    "sentences. If text is unreadable, say so."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data_url,
                                    "detail": "high",
                                },
                            },
                        ],
                    },
                ],
                max_tokens=300,
            )

            description = response.choices[0].message.content or ""

            logfire.info(
                "Image processed",
                description_length=len(description),
            )

            return description.strip()

        except Exception as exc:
            logfire.error(
                "Image processing failed",
                error=str(exc),
            )
            return ""


def process_article_images(image_urls: list[str]) -> list[dict]:
    """
    Download and describe article images.

    Returns:
        [{"url": "...", "description": "..."}]
    """
    results = []

    for url in image_urls:
        local_path = None

        try:
            local_path = download_image(url)
            description = describe_image(local_path)

            results.append({
                "url": url,
                "description": description,
            })

        except Exception as exc:
            logfire.error(
                "Failed to process image",
                url=url,
                error=str(exc),
            )

            # Preserve the failed image in the results for later retry.
            results.append({
                "url": url,
                "description": "",
                "error": str(exc),
            })

        finally:
            if local_path:
                try:
                    Path(local_path).unlink(missing_ok=True)
                except OSError as exc:
                    logfire.warning(
                        "Temporary image cleanup failed",
                        error=str(exc),
                    )

    return results
