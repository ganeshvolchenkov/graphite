"""Does an arbitrary real-world strategy actually run? One row per script shape."""

import asyncio
from pathlib import Path

from contracts import ScenarioScript
from engine.book import build_book_path
from engine.sandbox import run_strategy
from llm.prepare import prepare

SCENARIO = ScenarioScript.model_validate({
    "instrument": {"symbol": "ACME", "assetClass": "equity", "quoteUnit": "bps",
                   "startPrice": 100.0, "pipSize": 1.0},
    "resolutionMs": 1000, "durationMs": 240000, "baselineSpreadBps": 2.0,
    "events": [
        {"type": "price_impulse", "atMs": 60000, "overMs": 120000, "movePct": -8.0},
        {"type": "volatility_regime", "atMs": 60000, "overMs": 120000, "multiplier": 5.0},
        {"type": "depth_evaporation", "atMs": 60000, "overMs": 110000,
         "side": "bid", "levels": 5, "pct": 100.0},
        {"type": "spread_shock", "atMs": 60000, "overMs": 120000, "toSpreadBps": 400.0},
    ],
})

SCRIPTS = {
    "already-on_tick": '''
def on_tick(bar, book, account):
    if bar.price > bar.rolling_high:
        account.buy(100)
''',
    "class-zipline-style": '''
class MomentumAlgo:
    def __init__(self):
        self.held = 0

    def handle_data(self, context, data):
        if data["price"] > data["rolling_high"] and not self.held:
            self.held = 250
            return {"action": "BUY", "size": 250}
        return {"action": "HOLD", "size": 0}
''',
    "backtrader-style-next": '''
class MeanReversion:
    params = {"lookback": 12, "size": 150}

    def __init__(self):
        self.position = 0
        self.prices = []

    def next(self, price, low, high):
        self.prices.append(price)
        if len(self.prices) < 5:
            return None
        if price < low * 1.001 and self.position == 0:
            self.position = self.params["size"]
            return ("buy", self.params["size"])
        if price > high * 0.999 and self.position > 0:
            qty = self.position
            self.position = 0
            return ("sell", qty)
        return None
''',
    "numpy-signal": '''
import numpy as np


class VolTargetStrategy:
    def __init__(self, target_vol=0.15):
        self.target_vol = target_vol
        self.window = []

    def generate_signal(self, price, atr):
        self.window.append(price)
        if len(self.window) < 10:
            return 0.0
        returns = np.diff(np.array(self.window[-20:])) / np.array(self.window[-20:-1])
        realised = float(np.std(returns)) or 1e-9
        scale = self.target_vol / (realised * np.sqrt(252))
        return float(np.clip(scale, 0.0, 3.0)) * 100.0
''',
    "main-block-and-print": '''
import math

STATE = {"pos": 0}


def decide(price, high, depth):
    print("evaluating", price)
    edge = math.log(1.0 + depth) if depth > 0 else 0.0
    if price > high and edge > 1.0:
        return 120
    return 0


if __name__ == "__main__":
    print("standalone run")
    for p in range(5):
        decide(p, 1, 10)
''',
}


async def main() -> None:
    rows = build_book_path(SCENARIO, seed=3)
    print(f"{'script':24s} {'adapted':8s} {'ran':5s} {'ticks':>6s} {'fills':>6s}  outcome")
    print("-" * 96)

    for name, code in SCRIPTS.items():
        prepared = await prepare(code, smoke_rows=rows)
        result = run_strategy(prepared.code, rows)
        error = result.error
        outcome = "clean" if not error else f"{error['type']} @{error['index']}"
        print(f"{name:24s} {str(prepared.adapted):8s} {str(bool(result.ticks)):5s} "
              f"{len(result.ticks):6d} {len(result.fills):6d}  {outcome}")
        for note in prepared.notes:
            print(f"{'':24s} note: {note}")

    institutional = Path("sample_strategies/institutional_mm.py").read_text(encoding="utf-8")
    prepared = await prepare(institutional, smoke_rows=rows)
    result = run_strategy(prepared.code, rows)
    error = result.error
    outcome = "clean" if not error else f"{error['type']} @{error['index']}"
    print(f"{'institutional-mm':24s} {str(prepared.adapted):8s} {str(bool(result.ticks)):5s} "
          f"{len(result.ticks):6d} {len(result.fills):6d}  {outcome}")


if __name__ == "__main__":
    asyncio.run(main())
