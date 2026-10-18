"""Manual ingestion smoke test.

Run with `python test_api.py` after installing requirements and configuring .env.
This is intentionally not auto-executed by pytest because it calls external services.
"""


def main():
    from rag.pipeline import run_pipeline

    print("Starting RAG ingestion pipeline...")
    result = run_pipeline(
        url="https://support.brilliantdirectories.com/support/sitemap.xml",
        mode="sitemap",
        max_pages=3,
        delay=1.0,
        process_images=False,
        wipe=False,
    )
    print("\nPipeline completed:", result)


if __name__ == "__main__":
    main()
