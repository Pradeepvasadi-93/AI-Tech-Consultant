import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from chunking.chunker import chunk_document, split_text
from ingestion import manifest
from parsing.sitemap_parser import parse_sitemap, parse_sitemap_entries


def test_split_text_empty_and_invalid_arguments():
    assert split_text("") == []
    try:
        split_text("text", chunk_size=0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_chunk_document_preserves_source_title_and_image_context():
    document = {
        "url": "https://example.test/article",
        "title": "Payment Setup",
        "text": "Configure payments.\n\nCheck the provider settings.",
        "images": [{"url": "https://example.test/screenshot.png",
                    "description": "The payment provider dropdown is visible."}],
    }
    chunks = chunk_document(document)
    assert len(chunks) >= 2
    assert all(c["source_url"] == document["url"] for c in chunks)
    assert all(c["title"] == "Payment Setup" for c in chunks)
    image_chunks = [c for c in chunks if c["content_type"] == "image"]
    assert image_chunks[0]["image_url"].endswith("screenshot.png")
    assert "dropdown" in image_chunks[0]["text"]


def test_manifest_uses_configured_absolute_path_and_atomic_save(tmp_path, monkeypatch):
    manifest_path = tmp_path / "nested" / "manifest.json"
    monkeypatch.setattr(manifest, "CHECKPOINT_FILE", manifest_path)

    assert manifest.load_manifest() == {}
    expected = {"https://example.test/a": {"status": "processed"}}
    manifest.save_manifest(expected)
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == expected
    assert not manifest_path.with_suffix(".json.tmp").exists()


def test_manifest_corruption_is_not_silently_overwritten(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{broken", encoding="utf-8")
    monkeypatch.setattr(manifest, "CHECKPOINT_FILE", manifest_path)

    try:
        manifest.load_manifest()
        assert False, "expected ValueError"
    except ValueError:
        pass
    assert manifest_path.read_text(encoding="utf-8") == "{broken"


def test_sitemap_parser_extracts_nested_namespaces(monkeypatch):
    class Response:
        text = """<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.test/a</loc></url>
          <url><loc>https://example.test/b</loc></url>
        </urlset>"""
        def raise_for_status(self):
            return None

    monkeypatch.setattr("parsing.sitemap_parser.requests.get", lambda *a, **k: Response())
    assert parse_sitemap("https://example.test/sitemap.xml") == [
        "https://example.test/a", "https://example.test/b"
    ]


def test_sitemap_parser_preserves_lastmod(monkeypatch):
    class Response:
        text = """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.test/a</loc><lastmod>2026-10-01</lastmod></url>
        </urlset>"""
        def raise_for_status(self):
            return None

    monkeypatch.setattr("parsing.sitemap_parser.requests.get", lambda *a, **k: Response())
    entries = parse_sitemap_entries("https://example.test/sitemap.xml")
    assert entries == [{"url": "https://example.test/a", "lastmod": "2026-10-01"}]
