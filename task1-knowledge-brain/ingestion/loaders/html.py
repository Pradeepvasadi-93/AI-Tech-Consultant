import logfire
from bs4 import BeautifulSoup


def parse_html(content: str) -> str:
    """
    Parse HTML content, remove unwanted elements,
    and return clean text for RAG ingestion.
    """
    with logfire.span("📄 HTML Parsing"):
        try:
            soup = BeautifulSoup(content, "html.parser")

            # Remove scripts, styles, metadata, and noscript content
            for element in soup(
                ["script", "style", "meta", "noscript"]
            ):
                element.decompose()

            # Extract readable text
            text = soup.get_text(separator="\n")

            # Clean whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (
                phrase.strip()
                for line in lines
                for phrase in line.split("  ")
            )

            text_clean = "\n".join(
                chunk for chunk in chunks if chunk
            )

            logfire.info(
                "✅ HTML Parsing Successful",
                characters=len(text_clean)
            )

            return text_clean

        except Exception as e:
            logfire.error(f"❌ HTML Parse Failed: {e}")
            raise
