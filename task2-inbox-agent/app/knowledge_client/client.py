
import os
from typing import Any

import httpx


class KnowledgeBrainError(Exception):
    """Raised when the Knowledge Brain cannot return a usable response."""


class Task1KnowledgeClient:
    """HTTP client for the Task 1 Knowledge Brain API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 15.0,
    ):
        self.base_url = (
            base_url or os.getenv(
                "TASK1_API_BASE_URL",
                "http://127.0.0.1:8000",
            )
        ).rstrip("/")

        self.api_key = api_key or os.getenv("TASK1_API_KEY")
        self.timeout = timeout

    def query(
        self,
        question: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Ask Task 1 a question and return its evidence and answer."""

        if not question or not question.strip():
            raise ValueError("The question cannot be empty.")

        headers = {"Accept": "application/json"}

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        payload = {
            "question": question.strip(),
            "top_k": top_k,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/query",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

        except httpx.TimeoutException as exc:
            raise KnowledgeBrainError(
                "Task 1 timed out while retrieving knowledge."
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise KnowledgeBrainError(
                f"Task 1 returned HTTP {exc.response.status_code}: "
                f"{exc.response.text[:300]}"
            ) from exc

        except httpx.RequestError as exc:
            raise KnowledgeBrainError(
                "Could not connect to Task 1. "
                "Check that the Knowledge Brain API is running."
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise KnowledgeBrainError(
                "Task 1 returned invalid JSON."
            ) from exc

        if not isinstance(data, dict):
            raise KnowledgeBrainError(
                "Task 1 returned an unexpected response format."
            )

        # Keep the response fields from Task 1 intact.
        # The actual contract must be checked against Task 1's API.
        return data
