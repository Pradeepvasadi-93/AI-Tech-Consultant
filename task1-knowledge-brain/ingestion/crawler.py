
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import logfire
import requests
from bs4 import BeautifulSoup

from ingestion.loaders.html import parse_html
from ingestion.manifest import load_manifest, save_manifest
from parsing.image_processor import process_article_images


# Resolve paths relative to the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENT_DIR = PROJECT_ROOT / "ingestion" / "documents"

MAX_IMAGES_PER_PAGE = 20
REQUEST_TIMEOUT = 15
USER_AGENT = "KnowledgeBrainBot/1.0"


def utc_now() -> str:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()




def fetch_with_retries(session, url: str, headers: dict, attempts: int = 3):
    """Retry transient network, rate-limit and server errors with backoff."""
    last_error = None
    for attempt_index in range(attempts):
        response = None
        try:
            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=False,
                headers=headers,
            )
            if response.status_code == 304:
                return response
            if response.status_code == 429 or response.status_code >= 500:
                if attempt_index < attempts - 1:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        wait_seconds = float(retry_after) if retry_after else 2 ** attempt_index
                    except ValueError:
                        wait_seconds = 2 ** attempt_index
                    response.close()
                    time.sleep(min(max(wait_seconds, 1), 30))
                    continue
            return response
        except requests.RequestException as exc:
            last_error = exc
            if response is not None:
                response.close()
            if attempt_index >= attempts - 1:
                raise
            time.sleep(2 ** attempt_index)

    if last_error:
        raise last_error
    raise RuntimeError(f"Could not fetch {url} after {attempts} attempts")


def get_document_path(url: str) -> Path:
    """Generate a stable filename for each webpage."""
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return DOCUMENT_DIR / f"{url_hash}.json"


def extract_image_urls(
    html: str,
    page_url: str,
    max_images: int = MAX_IMAGES_PER_PAGE,
) -> list[str]:
    """Extract unique absolute HTTP(S) image URLs."""
    if max_images <= 0:
        return []

    soup = BeautifulSoup(html, "html.parser")
    image_urls = []
    seen = set()

    for img in soup.find_all("img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-lazy-src")
        )

        # Use the first srcset candidate if no other source exists.
        if not src and img.get("srcset"):
            candidates = img["srcset"].split(",")

            if candidates:
                src = candidates[0].strip().split()[0]

        if not src:
            continue

        image_url = urljoin(page_url, src.strip())
        parsed_url = urlparse(image_url)

        if parsed_url.scheme not in {"http", "https"}:
            continue

        if not parsed_url.hostname or image_url in seen:
            continue

        if parsed_url.path.lower().endswith(".svg"):
            continue

        seen.add(image_url)
        image_urls.append(image_url)

        if len(image_urls) >= max_images:
            break

    return image_urls


def process_images(
    html: str,
    page_url: str,
    max_images: int = MAX_IMAGES_PER_PAGE,
) -> list[dict]:
    """
    Describe webpage images using the OpenAI image processor.

    Image failures are recorded individually and do not fail
    the entire webpage ingestion.
    """
    image_urls = extract_image_urls(
        html,
        page_url,
        max_images=max_images,
    )

    if not image_urls:
        return []

    try:
        # This function downloads each image, calls describe_image()
        # with its local file path, and cleans up temporary files.
        results = process_article_images(image_urls)

    except Exception as exc:
        logfire.error(
            "Image batch processing failed",
            page_url=page_url,
            error=str(exc),
        )

        return [
            {
                "url": image_url,
                "description": None,
                "status": "failed",
                "error": str(exc),
            }
            for image_url in image_urls
        ]

    images = []

    for result in results:
        description = result.get("description") or ""
        error = result.get("error")

        status = (
            "processed"
            if description.strip() and not error
            else "failed"
        )

        image = {
            "url": result["url"],
            "description": description.strip() or None,
            "status": status,
        }

        if status == "failed":
            image["error"] = error or "No image description returned"

        images.append(image)

    return images


def save_document(document: dict, url: str) -> Path:
    """Atomically persist a webpage document."""
    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = get_document_path(url)
    temp_path = output_path.with_suffix(".tmp")

    try:
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(
                document,
                file,
                indent=2,
                ensure_ascii=False,
            )
            file.flush()

        temp_path.replace(output_path)
        return output_path

    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def crawl_articles(
    urls: list[str],
    delay: float = 2,
    max_images: int = MAX_IMAGES_PER_PAGE,
    process_images_enabled: bool = True,
    sitemap_metadata: dict[str, dict] | None = None,
) -> dict:
    """
    Crawl pages, extract text and images, save documents,
    and maintain manifest checkpoints.
    """
    manifest = load_manifest()

    stats = {
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "images_processed": 0,
        "images_failed": 0,
    }

    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})

        for url in urls:
            existing = manifest.get(url, {})
            document_path = get_document_path(url)

            # A processed page is not automatically unchanged. Check it again
            # using conditional HTTP headers/content hashes so daily runs detect updates.
            attempt = existing.get("attempts", 0) + 1
            last_attempt = utc_now()

            manifest[url] = {
                **existing,
                "status": "processing",
                "attempts": attempt,
                "last_attempt": last_attempt,
                "sitemap_lastmod": (sitemap_metadata or {}).get(url, {}).get("lastmod", existing.get("sitemap_lastmod")),
            }

            # Save the checkpoint before starting the crawl.
            save_manifest(manifest)

            try:
                with logfire.span(
                    "Crawl webpage",
                    url=url,
                    attempt=attempt,
                ):
                    parsed_url = urlparse(url)

                    if (
                        parsed_url.scheme not in {"http", "https"}
                        or not parsed_url.hostname
                    ):
                        raise ValueError("Invalid webpage URL")

                    # Avoid silently following redirects.
                    conditional_headers = {}
                    retry_failed_images = (
                        process_images_enabled and existing.get("failed_images", 0) > 0
                    )
                    if not retry_failed_images:
                        if existing.get("etag"):
                            conditional_headers["If-None-Match"] = existing["etag"]
                        if existing.get("http_last_modified"):
                            conditional_headers["If-Modified-Since"] = existing["http_last_modified"]

                    response = fetch_with_retries(session, url, conditional_headers)

                    if response.status_code == 304 and document_path.is_file():
                        manifest[url] = {
                            **existing,
                            "status": "processed",
                            "last_checked": utc_now(),
                            "attempts": attempt,
                            "last_attempt": last_attempt,
                        }
                        stats["skipped"] += 1
                        continue

                    response.raise_for_status()

                    content_type = response.headers.get(
                        "Content-Type", ""
                    ).lower()

                    if "text/html" not in content_type:
                        raise ValueError(
                            f"Expected HTML, received: "
                            f"{content_type or 'unknown content type'}"
                        )

                    html = response.text
                    content_hash = hashlib.sha256(
                        response.content or html.encode("utf-8")
                    ).hexdigest()

                    # If validators are unavailable, compare the response body.
                    # This catches changed pages without rewriting documents unnecessarily.
                    if (
                        existing.get("status") == "processed"
                        and existing.get("content_hash") == content_hash
                        and document_path.is_file()
                        and not retry_failed_images
                    ):
                        manifest[url] = {
                            **existing,
                            "status": "processed",
                            "last_checked": utc_now(),
                            "etag": response.headers.get("ETag", existing.get("etag")),
                            "http_last_modified": response.headers.get(
                                "Last-Modified", existing.get("http_last_modified")
                            ),
                            "attempts": attempt,
                            "last_attempt": last_attempt,
                        }
                        stats["skipped"] += 1
                        continue

                    page_soup = BeautifulSoup(html, "html.parser")
                    title = page_soup.title.get_text(" ", strip=True) if page_soup.title else ""
                    # Extract the webpage text.
                    text = parse_html(html)

                    if not text or not text.strip():
                        raise ValueError(
                            "No readable text extracted from webpage"
                        )

                    # Process images only when explicitly enabled.
                    if process_images_enabled and max_images > 0:
                        images = process_images(
                            html,
                            url,
                            max_images=max_images,
                        )
                    else:
                        images = []

                    ingested_at = utc_now()

                    document = {
                        "url": url,
                        "title": title,
                        "text": text,
                        "images": images,
                        "content_hash": content_hash,
                        "http_last_modified": response.headers.get("Last-Modified"),
                        "ingested_at": ingested_at,
                        "character_count": len(text),
                        "image_count": len(images),
                    }

                    # Save the document before marking it processed.
                    saved_path = save_document(document, url)

                    failed_images = sum(
                        image["status"] == "failed"
                        for image in images
                    )

                    successful_images = sum(
                        image["status"] == "processed"
                        for image in images
                    )

                    manifest[url] = {
                        "status": "processed",
                        "attempts": attempt,
                        "last_attempt": last_attempt,
                        "last_ingested": ingested_at,
                        "last_checked": ingested_at,
                        "document_path": str(saved_path),
                        "title": title,
                        "content_hash": content_hash,
                        "sitemap_lastmod": (sitemap_metadata or {}).get(url, {}).get("lastmod", existing.get("sitemap_lastmod")),
                        "etag": response.headers.get("ETag"),
                        "http_last_modified": response.headers.get("Last-Modified"),
                        "character_count": len(text),
                        "image_count": len(images),
                        "processed_images": successful_images,
                        "failed_images": failed_images,
                    }

                    stats["processed"] += 1
                    stats["images_processed"] += successful_images
                    stats["images_failed"] += failed_images

                    logfire.info(
                        "Webpage ingested",
                        url=url,
                        characters=len(text),
                        images=len(images),
                        failed_images=failed_images,
                    )

            except Exception as exc:
                manifest[url] = {
                    **manifest.get(url, {}),
                    "status": "failed",
                    "attempts": attempt,
                    "last_attempt": last_attempt,
                    "error": str(exc),
                }

                stats["failed"] += 1

                logfire.error(
                    "Webpage ingestion failed",
                    url=url,
                    error=str(exc),
                )

            finally:
                # Persist final status. If persistence fails, let the
                # error surface instead of pretending checkpointing worked.
                save_manifest(manifest)

                if delay > 0:
                    time.sleep(delay)

    logfire.info("Crawling completed", **stats)

    return stats
