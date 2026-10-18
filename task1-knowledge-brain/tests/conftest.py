"""Provide a lightweight Logfire stub for offline unit tests when not installed."""
import importlib.util
import sys
import types
from contextlib import contextmanager

if importlib.util.find_spec("logfire") is None:
    stub = types.ModuleType("logfire")

    @contextmanager
    def _span(*args, **kwargs):
        yield

    def _noop(*args, **kwargs):
        return None

    stub.span = _span
    stub.info = _noop
    stub.warning = _noop
    stub.error = _noop
    stub.exception = _noop
    stub.configure = _noop
    stub.instrument_fastapi = _noop
    stub.instrument_system_metrics = _noop
    sys.modules["logfire"] = stub


if importlib.util.find_spec("openai") is None:
    openai_stub = types.ModuleType("openai")
    class _UnavailableOpenAI:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Install requirements.txt to enable OpenAI image processing")
    openai_stub.OpenAI = _UnavailableOpenAI
    sys.modules["openai"] = openai_stub
