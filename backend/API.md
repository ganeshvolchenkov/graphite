# StressTest backend — everything the API outputs

Base URL `http://localhost:8000`. Interactive schema at `/docs`, raw OpenAPI at `/openapi.json`.
A working reference UI that drives every endpoint lives at `/dashboard`.

## Conventions

- **All request and response bodies are camelCase.** Python is snake_case internally; Pydantic
  translates at the wire. The one exception is `GET /api/benchmark`, which returns a raw stored
  JSON file in snake_case — noted again below.
- **Every LLM-backed endpoint accepts `?use_mock=true`** and returns a valid fixture of the same
  shape. Use this if the venue network dies during judging. It never errors.
- **LLM endpoints never 5xx on a model failure.** If Nebius is unreachable they log a warning and
  return the fallback fixture with a 200. The frontend does not need error branches for that case
  — but the payload will be the generic fixture, so don't present it as a fresh result blindly.
- Unknown fields may be added later; parse leniently.

## Endpoint map

| Method | Path | Returns |
|---|---|---|
| GET  | `/health` | liveness |
| POST | `/api/scenarios/interpret` | `Scenario` — prompt → market script + reasoning |
| POST | `/api/simulations` | **SSE stream** of `Tick` / `MarketEvent` / `SimulationRun` |
| POST | `/api/simulations/sync` | `SimulationRun` — same result, one JSON blob |
| POST | `/api/audits` | `AuditReport` |
| POST | `/api/strategies/improve` | `ImprovedStrategy` |
| POST | `/api/strategies/adapt` | `Adapter` |
| GET  | `/api/runs` | `RunSummary[]` |
| GET  | `/api/benchmark` | stored benchmark results (**snake_case**) |
| POST | `/api/backtest` | legacy one-shot endpoint, superseded — ignore |

---

## 1. `GET /health`

```json
{ "status": "ok", "engine": "Nebius Token Factory Ready" }
```

---

## 2. `POST /api/scenarios/interpret`

Natural-language market scenario → a structured, executable script. This is the "AI understands
the prompt" step, and it outputs its own reasoning so the UI can show the work.

**Request** `{ "prompt": "ECB emergency rate hike: EUR/USD spread widens from 0.8 to 65 pips within 300ms..." }`

**Response** — `Scenario`:

```json
{
  "id": "custom",
  "name": "EUR/USD — custom scenario",
  "prompt": "<echoed back>",
  "interpretation": "One-sentence plain-English summary.",
  "confidence": 0.95,
  "derivedFrom": ["top-of-book spread widens from 0.8 pips to 65 pips within 300ms", "..."],

  "params": {
    "shockMagnitudePct": -1.081, "volatilityMultiplier": 1.0, "liquidityFactor": 0.06,
    "spreadBps": 60.465, "gapPct": 0.0, "durationMinutes": 1,
    "shockDurationMinutes": 1, "recoveryMinutes": 0
  },

  "script": {
    "instrument": {
      "symbol": "EUR/USD", "assetClass": "fx", "quoteUnit": "pip",
      "startPrice": 1.075, "pipSize": 0.0001, "contractSize": 10000.0
    },
    "resolutionMs": 200,
    "durationMs": 44000,
    "baselineSpreadPips": 0.8,
    "baselineSpreadBps": 1.8,
    "events": [
      { "type": "spread_shock",      "atMs": 8000, "overMs": 300, "toSpreadPips": 65.0, "toSpreadBps": null },
      { "type": "toxic_flow",        "atMs": 8000, "durationMs": 450, "direction": "sell", "intensity": 0.9 },
      { "type": "depth_evaporation", "atMs": 8000, "overMs": 300, "side": "bid", "levels": 5, "pct": 94.0 },
      { "type": "feed_freeze",       "atMs": 8450, "durationMs": 450 },
      { "type": "crossed_book",      "atMs": 8450, "durationMs": 450, "invertBps": 5.0 },
      { "type": "price_impulse",     "atMs": 8000, "overMs": 900, "movePct": -1.081, "movePips": null }
    ]
  },

  "reasoning": {
    "summary": "...",
    "instrumentReasoning": "Why it picked EUR/USD, pip size, contract size.",
    "resolutionReasoning": "Why 200ms and not 1s.",
    "confidence": 0.95,
    "requirements": [ /* same objects as top-level requirements */ ]
  },

  "requirements": [
    {
      "quote": "followed by a 450ms WebSocket feed freeze",
      "status": "modelled",
      "mappedTo": "feed_freeze",
      "note": "Market data stops updating; strategy sees stale tick."
    }
  ],
  "coveragePct": 100.0,
  "adjustments": ["Inferred a -1.08% price impulse from the described bid-side damage."],
  "model": "Qwen/Qwen3-30B-A3B-Instruct-2507"
}
```

### Fields worth building UI around

- **`requirements[]`** — the headline AI artefact. Each is a literal quote lifted from the user's
  prompt plus what the model did with it. `status` is `"modelled" | "approximated" | "unsupported"`.
  Render as a table with a status pill; `mappedTo` names the event primitive or harness field.
- **`coveragePct`** — 0–100, computed as modelled=1.0, approximated=0.5, unsupported=0.0. Good as a
  big number / progress ring. *Self-reported by the model — label it "self-assessed coverage".*
- **`adjustments[]`** — deterministic post-processing the backend applied after the model answered
  (inferring a missing price move, shifting events past warmup, clamping step count). Plain strings.
  Showing these is honest and looks good: it proves there's real engineering behind the model call.
- **`script.events[]`** — a **discriminated union on `type`**. Switch on `type` in TS and you get
  exact field types. Great as a Gantt/timeline: x-axis `atMs`, bar length `overMs` or `durationMs`.
- **`derivedFrom[]`** — short phrase chips.
- **`params`** — the older flat representation. Still populated for backwards compatibility.
  **Prefer `script`.** Only fall back to `params` if `script` is `null`.
- `script`, `reasoning` are `null` and `requirements`/`adjustments` empty when the fallback fixture
  is served. Guard for that.

### The ten event types

Every event has `type` and `atMs`. The rest varies:

| `type` | extra fields |
|---|---|
| `spread_shock` | `overMs`, `toSpreadPips?`, `toSpreadBps?` |
| `depth_evaporation` | `overMs`, `side` (`bid`/`ask`/`both`), `levels`, `pct` |
| `price_impulse` | `overMs`, `movePct?`, `movePips?` |
| `gap` | `movePct` |
| `feed_freeze` | `durationMs` |
| `crossed_book` | `durationMs`, `invertBps` |
| `toxic_flow` | `durationMs`, `direction` (`buy`/`sell`), `intensity` |
| `volatility_regime` | `overMs`, `multiplier` |
| `halt` | `durationMs` |
| `recovery` | `overMs`, `reclaimPct` |

---

## 3. `POST /api/simulations` — SSE stream

This is the main event. **Streams over POST**, so `EventSource` will not work — use `fetch` with a
`ReadableStream` reader, or `@microsoft/fetch-event-source`.

Query params: `tickDelayMs` (default `25`, range 0–500 — controls playback speed) and `use_mock`.

**Request** — `SimulationRequest`:

```json
{
  "strategy": { "name": "My MM", "code": "def on_tick(bar, book, account): ..." },
  "scenario": { "id": "custom", "name": "ECB", "script": { /* from interpret */ } },
  "variant": "original"
}
```

`scenario` needs **either** `script` (preferred) or `params`. `variant` is `"original" | "improved"`
and is only a label — run the improved code by passing it as `strategy.code` with `variant: "improved"`.

**Frame format** — standard SSE, three named events:

```
event: tick
data: {"index":40,"total":220,...}

event: market_event
data: {"clock":"09:30:08.000","severity":"critical","message":"Spread blew out to 43.7 pips."}

event: complete
data: {"id":"...","series":[...],"metrics":{...},...}
```

### `tick` — one per simulation step, 220 of them in the example above

```json
{
  "index": 40, "total": 220, "phase": "shock", "clock": "09:30:08.000",
  "price": 1.071936, "equity": 999996.81, "pnl": -3.19, "drawdownPct": 0.0,
  "position": 1000.0, "trades": 1,
  "spreadBps": 1.8, "liquidityPct": 100.0, "volatilityPct": 8.0
}
```

- `phase` ∈ `"warmup" | "shock" | "recovery" | "stabilised"` — use it to band the chart background.
- `clock` is `"HH:MM:SS"`, or `"HH:MM:SS.mmm"` when `resolutionMs < 1000`. Simulated clock starting
  at 09:30:00, not wall time. **Use `index` for the x-axis and `clock` as the label** — clock strings
  repeat at sub-second resolution if you're not careful.
- `total` lets you render a progress bar from the first tick.
- Equity starts at 1,000,000. `pnl` is absolute currency, `drawdownPct` and `volatilityPct` are
  percentages already (`0.0`–`100.0`, not fractions). `liquidityPct` is 0–100 depth remaining.

### `market_event` — interleaved between ticks, only at notable moments

```json
{ "clock": "09:30:08.000", "severity": "warn", "message": "Toxic sell flow detected (intensity 0.90)." }
```

`severity` ∈ `"info" | "warn" | "critical" | "good"`. Map to your palette; `info` is almost always a
fill notification, `critical` is book damage or a strategy exception. Matched to a tick by `clock`.

Messages you'll actually see: shock regime entered, spread blowout, book CROSSED, feed frozen, toxic
flow, bid side evaporated, trading halted, bought/sold N @ price, adversely selected, and
`Strategy raised ZeroDivisionError: ... — execution halted.`

### `complete` — the full `SimulationRun`, fires once at the end

```json
{
  "id": "RUN-YABUNT",
  "variant": "original",
  "strategyName": "My MM",
  "scenarioName": "ECB",
  "startedAt": "2026-09-23T11:10:05.293Z",
  "series": [ /* every Tick again */ ],
  "events": [ /* every MarketEvent again */ ],
  "metrics": {
    "pnl": -42.31, "pnlPct": -0.0, "maxDrawdownPct": 0.0, "sharpe": -3.47,
    "trades": 7, "slippageBps": 38.22, "winRatePct": 0.0,
    "exposureMinutes": 148, "finalEquity": 999957.69
  },
  "strategyError": null,
  "adapter": {
    "adapted": false, "interface": "", "mapping": [], "risks": [],
    "notes": ["Strategy already implements on_tick."]
  }
}
```

`series` and `events` are the **complete** arrays — if you buffered the stream you now have them
twice. Easiest approach: render live from `tick` frames, then replace state wholesale on `complete`.

**`strategyError`** is `null` on a clean run, otherwise:

```json
{ "type": "ZeroDivisionError", "message": "float division by zero", "index": 170 }
```

This is a **product output, not a bug** — the point of the tool is to break strategies. Render it
prominently: "your code died at tick 170 of 220." `index` is `null` if it failed at import time.
The chart should stop there; `series` ends at the failing tick.

**`adapter`** describes what the AI did to make the code runnable:

```json
{
  "adapted": true,
  "interface": "class MarketMaker with on_market_data(self, snapshot) -> list[Quote]",
  "mapping": [
    "Constructed MarketMaker once via a module-level global",
    "Built a snapshot object from book.bids/book.asks preserving zero sizes",
    "Translated returned Quote pairs into account.quote(bid, ask, size)"
  ],
  "risks": ["The strategy ignores bar.halted, so it keeps quoting through the halt"],
  "notes": ["No on_tick found — generated an adapter with moonshotai/Kimi-K2.7-Code.",
            "Adapter broke on its first ticks (TypeError on tick 0); repaired and re-verified."]
}
```

When `adapted` is `true`, show this. It's the clearest demonstration of AI doing real work: the user
pasted a Zipline/Backtrader/custom class and the model wrote the glue. `risks[]` in particular reads
as genuine analysis. When `adapted` is `false`, `interface`/`mapping`/`risks` are empty and `notes`
explains why (already had `on_tick`, or generation was unavailable).

---

## 4. `POST /api/simulations/sync`

Identical `SimulationRequest` in, a single `SimulationRun` out — no streaming. Build the UI against
this first, then switch to SSE. Also the demo-safety net if streaming misbehaves on venue wifi.

---

## 5. `POST /api/audits`

**Request** — `AuditRequest`: `{ id, variant, strategyName, scenarioName, metrics, series, events, code?, scenario?, strategyError? }`.
In practice: take the `complete` payload, add `code`, post it.

**Response** — `AuditReport`:

```json
{
  "verdict": "failed",
  "score": 31,
  "headline": "Severe drawdown during liquidity shock: execution halts absent.",
  "narrative": "The strategy held exposure through the shock window without a stop or spread guard...",
  "strengths": ["Low turnover during the calm warmup regime"],
  "weaknesses": [{
    "title": "Unconstrained order sizing into illiquid book",
    "severity": "critical",
    "detail": "Market orders continued while spread widened past 30 bps."
  }],
  "failureModes": [{
    "title": "Adverse selection on breakout triggers",
    "severity": "high",
    "detail": "Entries clustered immediately before the volatility cascade."
  }]
}
```

`verdict` ∈ `"passed" | "marginal" | "failed"`. `score` is 0–100.
`severity` on weaknesses ∈ `"low" | "medium" | "high" | "critical"` — **note this is a different
scale from `MarketEvent.severity`.** Don't share a colour map between them.
`weaknesses` and `failureModes` have an identical shape; render as two sections.

---

## 6. `POST /api/strategies/improve`

**Request** `{ "code": "...", "audit": { /* the AuditReport above */ } }`

**Response** — `ImprovedStrategy`:

```json
{
  "code": "MAX_SPREAD_BPS = 25.0\n...\ndef on_tick(bar, book, account):\n    ...",
  "summary": "Added spread ceiling, liquidity floor, trailing ATR stop, and position cap.",
  "recommendations": [{
    "title": "Liquidity Guard",
    "problem": "Orders continued dispatching while the book thinned past 20%.",
    "change": "Flatten and stop trading when liquidity drops below MIN_LIQUIDITY_PCT.",
    "impact": "Removes fills during the widest-spread regime."
  }]
}
```

`code` is raw Python with real newlines — put it in a diff view against the original. Then feed it
straight back into `/api/simulations` with `variant: "improved"` for the before/after comparison.
That round trip is the money shot of the demo.

---

## 7. `POST /api/strategies/adapt`

Rarely needed directly — `/api/simulations` calls this internally and reports it in `adapter`. Exposed
so you can preview the glue before running.

**Request** `{ "code": "..." }` → **Response** `{ "interface", "adapter", "mapping": [], "risks": [] }`
where `adapter` is the generated Python source. Same fields as the `adapter` block above, minus
`adapted`/`notes`, plus the actual generated `adapter` code string.

---

## 8. `GET /api/runs`

```json
[{ "id": "RUN-YABUNT", "strategyName": "My MM", "scenarioName": "ECB",
   "verdict": "failed", "pnl": -42.31, "at": "2026-09-23T11:10:05.293Z" }]
```

In-memory only — resets when the server restarts. `verdict` is `""` until that run has been audited.

---

## 9. `GET /api/benchmark`

**⚠️ This one is snake_case** — it's a stored file served verbatim, not a Pydantic model.
Returns `404` with `{"detail": "no benchmark results yet"}` if it hasn't been generated.

```json
{
  "cases": ["equity-flash-crash", "liquidity-freeze", "ecb-fx-microstructure",
            "crypto-venue-outage", "gilt-rates-spiral"],
  "models": [{
    "model": "Qwen/Qwen3-30B-A3B-Instruct-2507",
    "cases": 5, "succeeded": 5, "score": 94.8,
    "event_recall": 95.0, "param_accuracy": 91.0,
    "instrument_acc": 100.0, "resolution_acc": 100.0,
    "avg_requirements": 4.6, "repairs": 0,
    "avg_latency_ms": 21250, "total_tokens": 13933
  }],
  "detail": [{
    "case": "equity-flash-crash", "model": "Qwen/...", "ok": true,
    "event_recall": 1.0, "param_accuracy": 1.0, "param_misses": [],
    "instrument_ok": true, "resolution_ok": true, "requirement_ratio": 1.0,
    "forbidden_hits": 0, "score": 100.0, "requirements_found": 4,
    "resolution_ms": 1000, "asset_class": "future",
    "latency_ms": 22502.4, "prompt_tokens": 2036, "completion_tokens": 676,
    "repaired": false, "error": ""
  }]
}
```

3 models × 5 cases = 15 `detail` rows. Render `models` as a leaderboard (score descending) and
`detail` as a models × cases grid. `param_misses` is a list of human-readable strings naming which
numeric parameters the model got wrong — worth showing on hover.

---

## TypeScript types

Paste into `frontend/lib/api-types.ts`.

```ts
// ---- scenario -------------------------------------------------------------
export type AssetClass = "fx" | "equity" | "future" | "crypto" | "rates";
export type QuoteUnit = "pip" | "bps" | "pct";
export type Side = "bid" | "ask" | "both";
export type RequirementStatus = "modelled" | "approximated" | "unsupported";

export interface Instrument {
  symbol: string; assetClass: AssetClass; quoteUnit: QuoteUnit;
  startPrice: number; pipSize: number; contractSize: number;
}

export type ScenarioEvent =
  | { type: "spread_shock"; atMs: number; overMs: number; toSpreadPips: number | null; toSpreadBps: number | null }
  | { type: "depth_evaporation"; atMs: number; overMs: number; side: Side; levels: number; pct: number }
  | { type: "price_impulse"; atMs: number; overMs: number; movePct: number | null; movePips: number | null }
  | { type: "gap"; atMs: number; movePct: number }
  | { type: "feed_freeze"; atMs: number; durationMs: number }
  | { type: "crossed_book"; atMs: number; durationMs: number; invertBps: number }
  | { type: "toxic_flow"; atMs: number; durationMs: number; direction: "buy" | "sell"; intensity: number }
  | { type: "volatility_regime"; atMs: number; overMs: number; multiplier: number }
  | { type: "halt"; atMs: number; durationMs: number }
  | { type: "recovery"; atMs: number; overMs: number; reclaimPct: number };

export interface ScenarioScript {
  instrument: Instrument; resolutionMs: number; durationMs: number;
  baselineSpreadPips: number | null; baselineSpreadBps: number | null;
  events: ScenarioEvent[];
}

export interface Requirement {
  quote: string; status: RequirementStatus; mappedTo: string; note: string;
}

export interface ScenarioParams {
  shockMagnitudePct: number; volatilityMultiplier: number; liquidityFactor: number;
  spreadBps: number; gapPct: number; durationMinutes: number;
  shockDurationMinutes: number; recoveryMinutes: number;
}

export interface Scenario {
  id: string; name: string; prompt: string; interpretation: string;
  confidence: number; derivedFrom: string[];
  params: ScenarioParams;
  script: ScenarioScript | null;
  reasoning: {
    summary: string; instrumentReasoning: string; resolutionReasoning: string;
    confidence: number; requirements: Requirement[];
  } | null;
  requirements: Requirement[]; coveragePct: number;
  adjustments: string[]; model: string;
}

// ---- simulation -----------------------------------------------------------
export type Phase = "warmup" | "shock" | "recovery" | "stabilised";
export type Severity = "info" | "warn" | "critical" | "good";
export type Variant = "original" | "improved";

export interface Tick {
  index: number; total: number; phase: Phase; clock: string;
  price: number; equity: number; pnl: number; drawdownPct: number;
  position: number; trades: number;
  spreadBps: number; liquidityPct: number; volatilityPct: number;
}

export interface MarketEvent { clock: string; severity: Severity; message: string }

export interface Metrics {
  pnl: number; pnlPct: number; maxDrawdownPct: number; sharpe: number;
  trades: number; slippageBps: number; winRatePct: number;
  exposureMinutes: number; finalEquity: number;
}

export interface StrategyError { type: string; message: string; index: number | null }

export interface AdapterInfo {
  adapted: boolean; interface: string;
  mapping: string[]; risks: string[]; notes: string[];
}

export interface SimulationRequest {
  strategy: { name: string; code: string };
  scenario: { id: string; name: string; params?: ScenarioParams; script?: ScenarioScript };
  variant: Variant;
}

export interface SimulationRun {
  id: string; variant: Variant; strategyName: string; scenarioName: string;
  startedAt: string; series: Tick[]; events: MarketEvent[]; metrics: Metrics;
  strategyError: StrategyError | null; adapter: AdapterInfo | null;
}

// ---- audit / improve ------------------------------------------------------
export type Verdict = "passed" | "marginal" | "failed";
export type WeaknessSeverity = "low" | "medium" | "high" | "critical";

export interface Weakness { title: string; severity: WeaknessSeverity; detail: string }

export interface AuditReport {
  verdict: Verdict; score: number; headline: string; narrative: string;
  strengths: string[]; weaknesses: Weakness[]; failureModes: Weakness[];
}

export interface Recommendation { title: string; problem: string; change: string; impact: string }

export interface ImprovedStrategy {
  code: string; summary: string; recommendations: Recommendation[];
}

export interface Adapter {
  interface: string; adapter: string; mapping: string[]; risks: string[];
}

export interface RunSummary {
  id: string; strategyName: string; scenarioName: string;
  verdict: string; pnl: number; at: string;
}
```

## Consuming the SSE stream

`EventSource` cannot do POST. This works:

```ts
export async function streamSimulation(
  body: SimulationRequest,
  on: { tick(t: Tick): void; event(e: MarketEvent): void; complete(r: SimulationRun): void },
  tickDelayMs = 25,
) {
  const res = await fetch(`http://localhost:8000/api/simulations?tickDelayMs=${tickDelayMs}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // frames are separated by a blank line
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const name = frame.match(/^event: (.+)$/m)?.[1];
      const data = frame.match(/^data: (.+)$/m)?.[1];
      if (!name || !data) continue;
      const parsed = JSON.parse(data);
      if (name === "tick") on.tick(parsed);
      else if (name === "market_event") on.event(parsed);
      else if (name === "complete") on.complete(parsed);
    }
  }
}
```

Ticks arrive every `tickDelayMs`. At 25ms a 220-step run takes ~5.5s — good demo pacing. Set `0` for
instant. **Note the first frame is delayed by several seconds** while the AI prepares the strategy
(adapter generation, if needed) and the whole simulation runs server-side. Show a spinner with a
message like "adapting your strategy" until the first `tick` lands.

## Gotchas

1. **`/api/benchmark` is snake_case.** Everything else is camelCase.
2. **Two different `severity` scales.** `MarketEvent.severity` is `info|warn|critical|good`;
   `Weakness.severity` is `low|medium|high|critical`. Only `critical` overlaps.
3. **`script` can be `null`** on `Scenario` when the model call failed — fall back to `params`.
4. **`strategyError` is a feature.** Design for it. Most interesting runs end in one.
5. **Percentages are already percentages.** `drawdownPct: 12.4` means 12.4%, not 1240%.
6. **`series` arrives twice** if you stream — once tick-by-tick, once inside `complete`.
7. **Equity base is 1,000,000**, so absolute `pnl` numbers look small next to it. `pnlPct` rounds to
   `-0.0` on tiny losses; prefer formatting `pnl` directly for small runs.
8. **Run history is in-memory.** Restarting the backend clears `/api/runs`.
9. **CORS allows all origins** for `GET/POST/OPTIONS` — no config needed on the frontend side.
10. **Adapter generation is non-deterministic.** The same pasted script can produce slightly
    different fill counts across runs. Don't build UI that asserts run-to-run equality.
