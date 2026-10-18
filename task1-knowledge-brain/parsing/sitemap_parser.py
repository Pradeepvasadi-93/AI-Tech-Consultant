"""Sitemap parsing with URL deduplication and last-modified metadata."""
import requests
import xml.etree.ElementTree as ET
import logfire


def parse_sitemap_entries(url: str, timeout: int = 20, max_sitemaps: int = 100) -> list[dict]:
    """Return unique ``{url, lastmod}`` records from urlsets or sitemap indexes."""
    visited_sitemaps = set()
    entries_by_url = {}

    def visit(sitemap_url: str):
        if sitemap_url in visited_sitemaps:
            return
        if len(visited_sitemaps) >= max_sitemaps:
            raise ValueError(f"Sitemap index exceeds the limit of {max_sitemaps} files")
        visited_sitemaps.add(sitemap_url)

        with logfire.span("Sitemap Parsing", url=sitemap_url):
            response = requests.get(
                sitemap_url,
                timeout=timeout,
                headers={"User-Agent": "KnowledgeBrainBot/1.0"},
            )
            response.raise_for_status()
            root = ET.fromstring(getattr(response, "content", b"") or response.text)

        root_name = root.tag.rsplit("}", 1)[-1].lower()
        if root_name == "sitemapindex":
            for node in root.findall(".//{*}sitemap"):
                loc = node.findtext("{*}loc")
                if loc and loc.strip():
                    visit(loc.strip())
            return

        for node in root.findall(".//{*}url"):
            loc = node.findtext("{*}loc")
            if not loc or not loc.strip():
                continue
            lastmod = node.findtext("{*}lastmod")
            url_value = loc.strip()
            entries_by_url[url_value] = {
                "url": url_value,
                "lastmod": lastmod.strip() if lastmod and lastmod.strip() else None,
            }

        # Also accept minimal/nonstandard urlsets where loc elements are direct descendants.
        if not entries_by_url:
            for loc_node in root.findall(".//{*}loc"):
                if loc_node.text and loc_node.text.strip():
                    value = loc_node.text.strip()
                    entries_by_url[value] = {"url": value, "lastmod": None}

    with logfire.span("Sitemap Parsing", url=url):
        visit(url)

    result = list(entries_by_url.values())
    logfire.info("Sitemap Parsed Successfully", url=url, total_urls=len(result))
    return result


def parse_sitemap(url: str) -> list[str]:
    """Backward-compatible helper returning just page URLs."""
    return [entry["url"] for entry in parse_sitemap_entries(url)]
