from rag.pipeline import run_pipeline

def main():
    try:
        print("Starting RAG ingestion pipeline...")

        result = run_pipeline(
            url="https://support.brilliantdirectories.com/support/sitemap.xml",
            mode="sitemap",
            max_pages=3,
            delay=1.0,
            process_images=False,
            wipe=False,
        )

        print("\nPipeline completed successfully!")

    except Exception as exc:
        print(f"\nPipeline failed: {exc}")

if __name__ == "__main__":
    main()