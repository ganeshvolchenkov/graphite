"""Vercel serverless entrypoint.

Vercel turns every file under api/ into a function, and vercel.json rewrites
every path here, so this module owns the whole surface. The app itself is
unchanged — main.py still runs under plain uvicorn locally.
"""

import sys
from pathlib import Path

# main.py and the contracts/engine/llm/routers packages sit one level up, and
# the function's own directory is what lands on sys.path.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import app  # noqa: E402

__all__ = ["app"]
