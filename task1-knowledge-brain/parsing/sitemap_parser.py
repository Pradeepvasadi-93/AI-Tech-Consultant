import requests
import xml.etree.ElementTree as ET
import logfire

def parse_sitemap(url: str):
    """
    Extract all URLs from a website's XML sitemap.
    """
    with logfire.span("🗺️ Sitemap Parsing", url=url):
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()

            root = ET.fromstring(resp.text)

            urls = [
                elem.text.strip()
                for elem in root.findall(".//{*}loc")
                if elem.text and elem.text.strip()
            ]

            logfire.info(
                "✅ Sitemap Parsed Successfully",
                url=url,
                total_urls=len(urls)
            )

            return urls

        except Exception as e:
            logfire.error(f"❌ Sitemap Parsing Failed: {e}")
            raise
