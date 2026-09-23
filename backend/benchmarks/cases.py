"""Hand-labelled stress-scenario prompts with the ground truth a correct reading must hit.

Labels were written before any model was run, so the scoring is not fitted to any model.
param_checks are (event_type, field, expected, relative_tolerance); tolerance None means
an exact match is required.
"""

from dataclasses import dataclass, field


@dataclass
class Case:
    name: str
    prompt: str
    asset_class: str
    min_resolution_ms: int
    max_resolution_ms: int
    required_events: set[str]
    expected_requirements: int
    notes: str = ""
    forbidden_events: set[str] = field(default_factory=set)
    param_checks: list[tuple] = field(default_factory=list)


CASES: list[Case] = [
    Case(
        name="equity-flash-crash",
        prompt=(
            "S&P 500 e-mini flash crash: 5% drop over four minutes on doubled volatility, "
            "order book depth halves, then a partial recovery over the following half hour."
        ),
        asset_class="future",
        min_resolution_ms=500,
        max_resolution_ms=60_000,
        required_events={"price_impulse", "volatility_regime", "depth_evaporation", "recovery"},
        expected_requirements=4,
        notes="Baseline. Minute-scale, symmetric damage, explicit magnitudes.",
        param_checks=[
            ("price_impulse", "move_pct", -5.0, 0.05),
            ("price_impulse", "over_ms", 240_000, 0.10),
            ("volatility_regime", "multiplier", 2.0, 0.30),
            ("depth_evaporation", "pct", 50.0, 0.10),
            ("recovery", "over_ms", 1_800_000, 0.15),
        ],
    ),
    Case(
        name="liquidity-freeze",
        prompt=(
            "Mid-cap equity liquidity freeze: resting size on both sides drops 96% for ten "
            "minutes and the touch spread widens from 3 bps to 180 bps. No directional view "
            "is given, volume simply disappears and the tape goes quiet."
        ),
        asset_class="equity",
        min_resolution_ms=500,
        max_resolution_ms=60_000,
        required_events={"depth_evaporation", "spread_shock"},
        expected_requirements=3,
        notes="No stated price move; the engine must still produce a dangerous regime.",
        param_checks=[
            ("depth_evaporation", "pct", 96.0, 0.03),
            ("depth_evaporation", "side", "both", None),
            ("spread_shock", "to_spread_bps", 180.0, 0.05),
        ],
    ),
    Case(
        name="ecb-fx-microstructure",
        prompt=(
            "ECB emergency rate hike announcement: EUR/USD top-of-book spread widens from "
            "0.8 pips to 65 pips within 300ms. Bid-side depth across the first 5 levels "
            "evaporates by 94% due to aggressive institutional market sell orders (toxic flow "
            "cascade), followed by a 450ms WebSocket feed freeze. Evaluate inventory skew "
            "calculation, adverse selection fill rates, and unhedged delta exposure during a "
            "crossed or inverted book state."
        ),
        asset_class="fx",
        min_resolution_ms=10,
        max_resolution_ms=500,
        required_events={"spread_shock", "depth_evaporation", "feed_freeze", "crossed_book", "toxic_flow"},
        expected_requirements=6,
        notes="Hard. Sub-second, asymmetric damage, pips, feed outage, crossed book.",
        param_checks=[
            ("spread_shock", "to_spread_pips", 65.0, 0.03),
            ("spread_shock", "over_ms", 300, 0.15),
            ("depth_evaporation", "pct", 94.0, 0.03),
            ("depth_evaporation", "side", "bid", None),
            ("depth_evaporation", "levels", 5, None),
            ("feed_freeze", "duration_ms", 450, 0.10),
            ("toxic_flow", "direction", "sell", None),
        ],
    ),
    Case(
        name="crypto-venue-outage",
        prompt=(
            "BTC/USDT perpetual: the venue matching engine stalls for 2 seconds during a "
            "cascade of liquidations, price gaps down 7% on the reopen, and the book comes "
            "back 80% thinner on the bid with sustained aggressive selling for 30 seconds."
        ),
        asset_class="crypto",
        min_resolution_ms=10,
        max_resolution_ms=1_000,
        required_events={"halt", "gap", "depth_evaporation", "toxic_flow"},
        expected_requirements=5,
        notes="Halt then gap-on-reopen; asymmetric bid damage; sub-second timescale.",
        param_checks=[
            ("halt", "duration_ms", 2_000, 0.10),
            ("gap", "move_pct", -7.0, 0.05),
            ("depth_evaporation", "pct", 80.0, 0.05),
            ("depth_evaporation", "side", "bid", None),
            ("toxic_flow", "duration_ms", 30_000, 0.15),
        ],
    ),
    Case(
        name="gilt-rates-spiral",
        prompt=(
            "10-year gilt yields spike in a forced-deleveraging spiral: price falls 9% over "
            "twenty minutes in three accelerating waves, dealer balance sheets withdraw so "
            "depth falls 85%, bid-ask goes from 2 bps to 120 bps, and there is no recovery "
            "within the session."
        ),
        asset_class="rates",
        min_resolution_ms=1_000,
        max_resolution_ms=60_000,
        required_events={"price_impulse", "depth_evaporation", "spread_shock"},
        expected_requirements=4,
        notes="Explicitly no recovery - tests whether the model over-applies the template.",
        forbidden_events={"recovery"},
        param_checks=[
            ("price_impulse", "move_pct", -9.0, 0.05),
            ("price_impulse", "over_ms", 1_200_000, 0.10),
            ("depth_evaporation", "pct", 85.0, 0.05),
            ("spread_shock", "to_spread_bps", 120.0, 0.05),
        ],
    ),
]
