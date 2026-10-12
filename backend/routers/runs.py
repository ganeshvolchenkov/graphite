from fastapi import APIRouter

from contracts import RunSummary
from engine.store import history

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("", response_model=list[RunSummary])
async def list_runs() -> list[RunSummary]:
    return history()
