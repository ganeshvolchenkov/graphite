import asyncio
import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from contracts import AdapterInfo, SimulationRequest, SimulationRun
from engine.book import build_book_path
from engine.runner import script_from_params, simulate_script
from engine.store import new_run_id, record, seed_for, utc_now_iso
from llm.prepare import prepare

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/simulations", tags=["simulations"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _resolve_script(request: SimulationRequest):
    """Prefer the rich event script; fall back to the legacy params block."""
    if request.scenario.script is not None:
        return request.scenario.script
    if request.scenario.params is not None:
        return script_from_params(request.scenario.params)
    raise ValueError("scenario must carry either a script or params")


def _frame(event: str, payload: str) -> str:
    return f"event: {event}\ndata: {payload}\n\n"


async def _stream(request: SimulationRequest, tick_delay_ms: int, use_mock: bool) -> AsyncIterator[str]:
    run_id = new_run_id()
    script = _resolve_script(request)
    prepared = await prepare(
        request.strategy.code, use_mock=use_mock,
        smoke_rows=build_book_path(script, seed=seed_for(run_id)),
    )
    ticks, events, metrics, guards, execution, _ = simulate_script(
        prepared.code, script, seed=seed_for(run_id)
    )
    logger.info(
        "run %s: %d/6 guards, executed_ok=%s, pnl %.0f",
        run_id,
        guards.score,
        execution.ok,
        metrics.pnl,
    )

    pending = {event.clock: event for event in events}
    delay = tick_delay_ms / 1000.0

    for tick in ticks:
        yield _frame("tick", tick.model_dump_json(by_alias=True))
        event = pending.pop(tick.clock, None)
        if event:
            yield _frame("market_event", event.model_dump_json(by_alias=True))
        if delay:
            await asyncio.sleep(delay)

    run = SimulationRun(
        id=run_id,
        variant=request.variant,
        strategy_name=request.strategy.name,
        scenario_name=request.scenario.name,
        started_at=utc_now_iso(),
        series=ticks,
        events=events,
        metrics=metrics,
        strategy_error=execution.error,
        adapter=AdapterInfo(**prepared.model_dump(exclude={"code"})),
    )
    record(run)
    yield _frame("complete", run.model_dump_json(by_alias=True))


@router.post("")
async def run_simulation(
    request: SimulationRequest,
    tick_delay_ms: int = Query(25, ge=0, le=500),
    use_mock: bool = Query(False, alias="use_mock"),
) -> StreamingResponse:
    return StreamingResponse(
        _stream(request, tick_delay_ms, use_mock),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/sync", response_model=SimulationRun)
async def run_simulation_sync(
    request: SimulationRequest,
    use_mock: bool = Query(False, alias="use_mock"),
) -> SimulationRun:
    """Non-streaming variant — demo insurance if SSE misbehaves on the venue network."""
    run_id = new_run_id()
    script = _resolve_script(request)
    prepared = await prepare(
        request.strategy.code, use_mock=use_mock,
        smoke_rows=build_book_path(script, seed=seed_for(run_id)),
    )
    ticks, events, metrics, _, execution, _rows = simulate_script(
        prepared.code, script, seed=seed_for(run_id)
    )
    run = SimulationRun(
        id=run_id,
        variant=request.variant,
        strategy_name=request.strategy.name,
        scenario_name=request.scenario.name,
        started_at=utc_now_iso(),
        series=ticks,
        events=events,
        metrics=metrics,
        strategy_error=execution.error,
        adapter=AdapterInfo(**prepared.model_dump(exclude={"code"})),
    )
    record(run)
    return run
