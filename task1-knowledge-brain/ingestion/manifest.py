import json
import os
from pathlib import Path

import logfire


CHECKPOINT_FILE = Path("ingestion/manifest.json")

print("Current working directory:", Path.cwd())
print("Manifest path:", CHECKPOINT_FILE.resolve())
print("Manifest exists:", CHECKPOINT_FILE.exists())

def load_manifest() -> dict:
    """Load the crawler's checkpoint manifest."""
    with logfire.span("📋 Load ingestion manifest"):
        CHECKPOINT_FILE.parent.mkdir(
            parents=True, exist_ok=True
        )

        if not CHECKPOINT_FILE.exists():
            return {}

        try:
            with CHECKPOINT_FILE.open(
                "r", encoding="utf-8"
            ) as file:
                manifest = json.load(file)

            if not isinstance(manifest, dict):
                raise ValueError(
                    "Manifest must contain a JSON object"
                )

            return manifest

        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logfire.error(
                f"❌ Failed to load manifest: {exc}"
            )
            raise


def save_manifest(manifest: dict) -> None:
    """Save the manifest atomically."""
    with logfire.span("💾 Save ingestion manifest"):
        CHECKPOINT_FILE.parent.mkdir(
            parents=True, exist_ok=True
        )

        temp_file = CHECKPOINT_FILE.with_suffix(".tmp")

        try:
            with temp_file.open(
                "w", encoding="utf-8"
            ) as file:
                json.dump(
                    manifest,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )
                file.flush()
                os.fsync(file.fileno())

            os.replace(temp_file, CHECKPOINT_FILE)

        except Exception as exc:
            logfire.error(
                f"❌ Failed to save manifest: {exc}"
            )

            if temp_file.exists():
                temp_file.unlink()

            raise
