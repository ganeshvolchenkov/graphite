import random
import string
from datetime import datetime, timezone

from contracts import RunSummary, SimulationRun

_HISTORY: list[RunSummary] = []
MAX_HISTORY = 20


def new_run_id() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"RUN-{suffix}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def seed_for(run_id: str) -> int:
    return abs(hash(run_id)) % (2**31)


def record(run: SimulationRun, verdict: str = "pending") -> None:
    _HISTORY.insert(
        0,
        RunSummary(
            id=run.id,
            strategy_name=run.strategy_name,
            scenario_name=run.scenario_name,
            verdict=verdict,
            pnl=run.metrics.pnl,
            at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        ),
    )
    del _HISTORY[MAX_HISTORY:]


def set_verdict(run_id: str, verdict: str) -> None:
    for entry in _HISTORY:
        if entry.id == run_id:
            entry.verdict = verdict
            return


def history() -> list[RunSummary]:
    return list(_HISTORY)
