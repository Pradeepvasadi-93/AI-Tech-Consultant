"""Atomic, project-root-relative crawler manifest persistence."""
import json
import os
from pathlib import Path

import logfire

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_FILE = PROJECT_ROOT / "ingestion" / "manifest.json"


def load_manifest() -> dict:
    """Load the crawler checkpoint; a missing manifest starts empty."""
    with logfire.span("Load ingestion manifest"):
        CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not CHECKPOINT_FILE.exists():
            return {}
        try:
            with CHECKPOINT_FILE.open("r", encoding="utf-8") as file:
                manifest = json.load(file)
            if not isinstance(manifest, dict):
                raise ValueError("Manifest must contain a JSON object")
            return manifest
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logfire.error("Failed to load manifest", error=str(exc))
            raise ValueError(
                f"Cannot read ingestion manifest at {CHECKPOINT_FILE}: {exc}. "
                "Repair or back up the file before retrying; it was not overwritten."
            ) from exc


def save_manifest(manifest: dict) -> None:
    """Save the manifest atomically so an interrupted write cannot truncate it."""
    if not isinstance(manifest, dict):
        raise TypeError("Manifest must be a dictionary")
    with logfire.span("Save ingestion manifest"):
        CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp_file = CHECKPOINT_FILE.with_suffix(".json.tmp")
        try:
            with temp_file.open("w", encoding="utf-8") as file:
                json.dump(manifest, file, indent=2, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_file, CHECKPOINT_FILE)
        except Exception as exc:
            logfire.error("Failed to save manifest", error=str(exc))
            temp_file.unlink(missing_ok=True)
            raise
