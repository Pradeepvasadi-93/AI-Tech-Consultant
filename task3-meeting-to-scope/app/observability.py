"""Optional Logfire/OpenTelemetry setup for API and agent-flow tracing."""
import logging

import logfire

from app.config import LOGFIRE_CONSOLE, LOGFIRE_SERVICE_NAME, LOGFIRE_TOKEN

_configured = False


def configure_observability() -> None:
    """Configure Logfire once; cloud export is enabled only when a token is provided."""
    global _configured
    if _configured:
        return

    # Do not send prompts, transcripts, API keys, or client content as span attributes.
    console = logfire.ConsoleOptions() if LOGFIRE_CONSOLE else False
    logfire.configure(
        service_name=LOGFIRE_SERVICE_NAME,
        token=LOGFIRE_TOKEN or None,
        send_to_logfire=bool(LOGFIRE_TOKEN),
        console=console,
    )
    _configured = True


def instrument_fastapi(app) -> None:
    """Instrument FastAPI requests after the app has been created."""
    try:
        # FastAPI instrumentation can capture validated request arguments by default.
        # Drop values (transcripts/client details) and retain only validation errors.
        def safe_request_attributes_mapper(request, attributes):
            errors = attributes.get("errors") or []
            return {"errors": errors} if errors else {}

        logfire.instrument_fastapi(app, request_attributes_mapper=safe_request_attributes_mapper)
    except Exception:
        logging.getLogger(__name__).exception("Could not instrument FastAPI with Logfire")
