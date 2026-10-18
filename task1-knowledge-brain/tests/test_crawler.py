import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion import crawler, manifest


class FakeResponse:
    def __init__(self, html):
        self.text = html
        self.content = html.encode("utf-8")
        self.status_code = 200
        self.headers = {"Content-Type": "text/html; charset=utf-8", "ETag": '"v1"'}
    def raise_for_status(self):
        return None


class FakeSession:
    html = "<html><head><title>Test Article</title></head><body><h1>Settings</h1><p>Change the logo here.</p></body></html>"
    def __init__(self):
        self.headers = {}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def get(self, *args, **kwargs):
        return FakeResponse(type(self).html)


def test_crawler_saves_checkpoint_and_skips_unchanged_content(tmp_path, monkeypatch):
    monkeypatch.setattr(crawler, "DOCUMENT_DIR", tmp_path / "documents")
    monkeypatch.setattr(manifest, "CHECKPOINT_FILE", tmp_path / "manifest.json")
    monkeypatch.setattr(crawler.requests, "Session", FakeSession)

    url = "https://example.test/support/article"
    first = crawler.crawl_articles([url], delay=0, process_images_enabled=False)
    assert first["processed"] == 1
    saved_path = crawler.get_document_path(url)
    document = json.loads(saved_path.read_text(encoding="utf-8"))
    assert document["title"] == "Test Article"
    assert document["content_hash"] == hashlib.sha256(FakeSession.html.encode()).hexdigest()

    second = crawler.crawl_articles([url], delay=0, process_images_enabled=False)
    assert second["skipped"] == 1
    assert second["processed"] == 0

    FakeSession.html = "<html><head><title>Updated Article</title></head><body><p>Updated help content.</p></body></html>"
    third = crawler.crawl_articles([url], delay=0, process_images_enabled=False)
    assert third["processed"] == 1
    updated = json.loads(saved_path.read_text(encoding="utf-8"))
    assert updated["title"] == "Updated Article"


def test_fetch_with_retries_retries_transient_server_error(monkeypatch):
    calls = {"count": 0}
    class RetryResponse(FakeResponse):
        def __init__(self, html, status_code):
            super().__init__(html)
            self.status_code = status_code
        def close(self):
            pass
    class RetrySession:
        def get(self, *args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                return RetryResponse("temporary", 503)
            return RetryResponse("ok", 200)

    monkeypatch.setattr(crawler.time, "sleep", lambda *_: None)
    response = crawler.fetch_with_retries(RetrySession(), "https://example.test", {})
    assert response.status_code == 200
    assert calls["count"] == 2
