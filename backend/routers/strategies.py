import logging

from fastapi import APIRouter, Query

from contracts import CamelModel, ImprovedStrategy, ImproveRequest
from llm.adapt import FALLBACK as ADAPT_FALLBACK, Adapter, adapt
from llm.improve import FALLBACK, improve
from llm.nebius import NebiusError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.post("/improve", response_model=ImprovedStrategy)
async def improve_strategy(
    request: ImproveRequest,
    use_mock: bool = Query(False, alias="use_mock"),
) -> ImprovedStrategy:
    try:
        improved, telemetry = await improve(request, use_mock=use_mock)
    except NebiusError as exc:
        logger.warning("strategy rewrite fell back to fixture: %s", exc)
        return FALLBACK

    logger.info(
        "rewrote strategy via %s (%d recommendations)",
        telemetry.get("model"),
        len(improved.recommendations),
    )
    return improved


class AdaptRequest(CamelModel):
    code: str


@router.post("/adapt", response_model=Adapter)
async def adapt_strategy(
    request: AdaptRequest,
    use_mock: bool = Query(False, alias="use_mock"),
) -> Adapter:
    """Generate an on_tick adapter for a strategy that uses a different interface."""
    try:
        adapter, telemetry = await adapt(request.code, use_mock=use_mock)
    except NebiusError as exc:
        logger.warning("adapter generation failed: %s", exc)
        return ADAPT_FALLBACK

    logger.info("generated adapter via %s: %s", telemetry.get("model"), adapter.interface)
    return adapter
