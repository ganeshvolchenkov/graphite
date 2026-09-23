import logging

from fastapi import APIRouter, Query

from contracts import InterpretRequest, Scenario
from llm.nebius import NebiusError
from llm.scenario import FALLBACK, interpret

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.post("/interpret", response_model=Scenario)
async def interpret_scenario(
    request: InterpretRequest,
    use_mock: bool = Query(False, alias="use_mock"),
) -> Scenario:
    try:
        scenario, telemetry = await interpret(request.prompt, use_mock=use_mock)
    except NebiusError as exc:
        logger.warning("scenario interpretation fell back to fixture: %s", exc)
        return FALLBACK.model_copy(update={"prompt": request.prompt})

    logger.info("interpreted scenario via %s", telemetry.get("model"))
    return scenario
