from contracts import CamelModel

from .nebius import CODE_MODEL, chat_json

HARNESS_API = """The harness calls on_tick(bar, book, account) once per simulation step.

bar.index, bar.t_ms, bar.clock, bar.phase      step number, ms since open, "HH:MM:SS", regime
bar.price, bar.mid                             the mid price (same value)
bar.spread_bps, bar.spread_pips                current top-of-book spread
bar.volatility_pct, bar.atr                    realised vol proxy, ATR in price units
bar.rolling_high, bar.rolling_low              trailing 12-step extremes
bar.stale, bar.halted                          True when the feed is frozen / trading halted

book.bid, book.ask                             top-of-book prices (bid > ask when crossed)
book.bids, book.asks                           5 levels each, objects with .price and .size
book.depth_bid, book.depth_ask                 summed size over the 5 levels (reaches 0.0)
book.depth                                     int(depth_bid + depth_ask)
book.imbalance, book.liquidity_pct             -1..1 skew, 0..100 depth remaining
book.spread_bps, book.crossed                  spread, True when bid prints above ask
book.toxic, book.toxic_direction               0..1 informed-flow intensity, "buy"/"sell"

account.position, account.inventory            signed size (same value)
account.cash, account.equity, account.entry_price, account.trades
account.unhedged_delta, account.adverse_fill_rate, account.passive_fills
account.buy(size), account.sell(size)          cross the spread now
account.flatten()                              close any open position
account.quote(bid_price, ask_price, size)      post a two-sided passive quote
account.stop_loss_hit(distance)                True if price fell `distance` below entry"""

SYSTEM = f"""You write adapters that let an existing trading strategy run inside a stress-test
harness. You are given the strategy's source and the harness API.

{HARNESS_API}

Return JSON with exactly these keys:
  interface:  one sentence naming the entry point you found and its signature
  adapter:    Python source defining on_tick(bar, book, account) at module level
  mapping:    array of short strings, each describing one translation you performed
  risks:      array of short strings for anything that may not translate faithfully

Rules for the adapter code:
  - It is appended AFTER the user's source in the same module, so their names are in scope.
  - Do NOT restate, rewrite or repair the user's code. Do not import it.
  - Construct their strategy object ONCE, lazily, via a module-level global.
  - Build whatever input type their entry point expects from bar/book. If they expect an
    order-book object with levels, construct it from book.bids and book.asks, preserving
    the real sizes including zero.
  - Translate their output into harness calls: a two-sided quote becomes account.quote(...),
    a directional order becomes account.buy(...) / account.sell(...).
  - If their code has a fill callback, call it after the harness call so their internal
    inventory stays in step.
  - CRITICAL: do not add guards, try/except, clamping or validation the user did not write.
    The harness exists to surface their bugs. If their code divides by zero when the book
    empties, it must still divide by zero. Let every exception propagate.
  - Use only these modules if you need any: math, dataclasses, typing, collections, numpy.
  - The adapter must be complete and runnable. No placeholders, no ellipses."""


class Adapter(CamelModel):
    interface: str
    adapter: str
    mapping: list[str] = []
    risks: list[str] = []


FALLBACK = Adapter(
    interface="Could not reach the model; no adapter generated.",
    adapter="",
    mapping=[],
    risks=["Adapter generation unavailable — supply an on_tick(bar, book, account) yourself."],
)


async def adapt(code: str, use_mock: bool = False) -> tuple[Adapter, dict]:
    if use_mock:
        return FALLBACK, {"model": "mock"}

    user = f"Strategy source:\n```python\n{code}\n```"
    payload, telemetry = await chat_json(SYSTEM, user, model=CODE_MODEL, temperature=0.1)
    return Adapter.model_validate(payload), telemetry
