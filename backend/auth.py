"""Shared-secret auth for the /api surface.

This API executes strategy code that is posted to it. On a public URL that is
not something to leave open, so every /api route requires a key.

Set STRESSTEST_API_KEY to turn it on. With the variable unset the API stays
open and logs a warning at startup — that keeps local development frictionless
and means a host that is missing the variable still demos rather than returning
401 for everything. Anything reachable from the internet must set it.
"""

import hmac
import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

HEADER = "X-API-Key"
PROTECTED_PREFIX = "/api/"


def configured_key() -> str | None:
    return os.getenv("STRESSTEST_API_KEY", "").strip() or None


def _supplied(request: Request) -> str | None:
    """Accept the header, or a bearer token so curl and HTTP clients work too."""
    header = request.headers.get(HEADER)
    if header:
        return header.strip()
    bearer = request.headers.get("Authorization", "")
    if bearer.lower().startswith("bearer "):
        return bearer[7:].strip()
    return None


def log_status() -> None:
    if configured_key():
        logger.info("API key required on %s*", PROTECTED_PREFIX)
    else:
        logger.warning(
            "STRESSTEST_API_KEY is not set - %s* is OPEN. Fine locally, not on a public URL.",
            PROTECTED_PREFIX,
        )


async def require_api_key(request: Request, call_next):
    key = configured_key()

    # OPTIONS carries no custom headers, so blocking it would break every
    # browser preflight before the real request is ever sent.
    if (
        key is None
        or request.method == "OPTIONS"
        or not request.url.path.startswith(PROTECTED_PREFIX)
    ):
        return await call_next(request)

    supplied = _supplied(request)
    if supplied is None:
        return JSONResponse(
            status_code=401,
            content={"detail": f"Missing credentials. Send the {HEADER} header."},
        )
    if not hmac.compare_digest(supplied, key):
        return JSONResponse(status_code=401, content={"detail": "Invalid API key."})

    return await call_next(request)
