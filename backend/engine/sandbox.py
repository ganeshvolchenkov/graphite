import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

WORKER = Path(__file__).parent / "worker.py"
TIMEOUT_SECONDS = 8


@dataclass
class ExecutionResult:
    ticks: list[dict]
    fills: list[dict]
    error: dict | None
    quotes: list[dict] = field(default_factory=list)
    stdout: str = ""
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return bool(self.ticks) and self.error is None and not self.timed_out


def self_check() -> dict:
    """Run a trivial strategy end to end and report whether this host allows it.

    Serverless runtimes do not always let a function spawn a process, and the
    whole product depends on that working. Finding out from a health check right
    after deploying is recoverable; finding out mid-demo is not.
    """
    rows = [
        {
            "index": i, "t_ms": i * 1000, "clock": f"09:30:0{i}", "phase": "warmup",
            "price": 100.0, "bid": 99.99, "ask": 100.01,
            "spread_bps": 2.0, "spread_pips": 1.0,
            "bids": [{"price": 99.99, "size": 100.0}], "asks": [{"price": 100.01, "size": 100.0}],
            "depth_bid": 100.0, "depth_ask": 100.0, "imbalance": 0.0,
            "liquidity_pct": 100.0, "volatility_pct": 1.0,
            "stale": False, "halted": False, "crossed": False,
            "toxic": 0.0, "toxic_direction": "sell", "atr": 0.01,
            "rolling_high": 100.0, "rolling_low": 100.0,
        }
        for i in range(3)
    ]
    result = run_strategy("def on_tick(bar, book, account):\n    account.buy(1)\n", rows)
    return {
        "subprocess": result.error is None and bool(result.ticks),
        "ticks": len(result.ticks),
        "fills": len(result.fills),
        "executable": sys.executable,
        "error": result.error,
    }


def run_strategy(code: str, rows: list[dict], contract_size: float = 1.0) -> ExecutionResult:
    """Execute the strategy in a separate process with a hard wall-clock limit.

    Isolation is demo-grade: separate process, stripped builtins, no __import__, timeout.
    It stops careless or crashing strategies from touching the API process. It is NOT a
    hardened boundary against a determined attacker — that needs container isolation.
    """
    payload = json.dumps({"code": code, "rows": rows, "contract_size": contract_size})

    try:
        completed = subprocess.run(
            [sys.executable, str(WORKER)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=str(WORKER.parent),
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            ticks=[],
            fills=[],
            error={
                "type": "TimeoutError",
                "message": f"strategy exceeded {TIMEOUT_SECONDS}s wall clock (possible infinite loop)",
                "index": None,
            },
            timed_out=True,
        )

    if completed.returncode != 0:
        return ExecutionResult(
            ticks=[],
            fills=[],
            error={
                "type": "WorkerCrash",
                "message": (completed.stderr or "worker exited non-zero").strip()[:400],
                "index": None,
            },
        )

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return ExecutionResult(
            ticks=[],
            fills=[],
            error={"type": "WorkerOutput", "message": "worker returned unparseable output", "index": None},
        )

    return ExecutionResult(
        ticks=data["ticks"],
        fills=data["fills"],
        error=data["error"],
        quotes=data.get("quotes", []),
        stdout=data.get("stdout", ""),
    )
