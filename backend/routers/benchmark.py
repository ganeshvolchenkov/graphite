import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

RESULTS = Path(__file__).parent.parent / "benchmark_results.json"

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])


@router.get("")
async def latest_benchmark() -> dict:
    """The stored cross-model comprehension results (regenerate: python -m benchmarks.run)."""
    if not RESULTS.exists():
        raise HTTPException(status_code=404, detail="no benchmark results yet")
    return json.loads(RESULTS.read_text(encoding="utf-8"))
