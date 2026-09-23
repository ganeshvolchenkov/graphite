# StressTest — frontend brief

Paste this whole file into Lovable as the opening prompt. The exact response
shapes and TypeScript types are in `backend/API.md` — paste that as a follow-up
message once the app scaffolding exists.

---

## What the product is

**StressTest** breaks trading strategies before the market does.

A quant pastes their strategy code and describes a market catastrophe in plain
English — *"ECB emergency rate hike, EUR/USD spread widens from 0.8 to 65 pips
in 300ms, bid-side depth evaporates 94%, then a 450ms feed freeze"*. The system
turns that sentence into a real, executable market simulation, runs their actual
Python against it tick by tick, and shows them the exact moment their code dies.

Then it explains why, rewrites the code to survive, and re-runs it to prove the
fix worked.

The buyer is a prop trading desk or quant fund. The tone is professional trading
software, not a consumer SaaS landing page.

## Why it is interesting (this is an AI hackathon — this part must be visible)

Three separate AI jobs happen, and each one produces evidence the UI should show:

1. **Comprehension.** A reasoning model reads an institutional prompt and emits a
   structured market script — instrument, tick resolution, and a timeline of
   order-book events. It reports *which phrases it understood and what it did
   with each one*, quote by quote.
2. **Code adaptation.** Real strategies do not have the function signature our
   harness calls. A code model reads arbitrary strategy source — a Zipline-style
   class, a Backtrader `next()`, a bare signal function — and writes the glue so
   it runs unmodified. It reports the interface it found, every translation it
   made, and the risks it could not translate faithfully.
3. **Repair.** After the strategy fails, a model explains the failure and rewrites
   the code with the missing guards, which then gets re-run for a before/after.

**The system deliberately does not fix the user's bugs.** If their code divides by
zero when the book empties, it still divides by zero — that failure is the
product's output. The UI should treat a crash as the headline result, not an error
state to apologise for.

## The screen flow

Six stages. They can be one scrolling console or a stepper — but stage 2 must
feel live, and the user must be able to see earlier stages' output while reading
later ones.

### 1. Scenario — plain English to numbers
User types a market catastrophe. Calls `POST /api/scenarios/interpret`.

Show:
- **A requirements table.** One row per demand the model found: the literal
  `quote` from their prompt, a status pill (`modelled` / `approximated` /
  `unsupported`), what it `mappedTo`, and a `note`. This is the single most
  important panel in the app — it proves the model read the prompt rather than
  pattern-matched it. Never collapse or truncate the quotes.
- **A coverage number** (`coveragePct`, 0–100). Label it "self-assessed coverage"
  — it is the model's own judgement, and saying so is more credible than hiding it.
- **An event timeline.** `script.events[]` is a list of order-book events with
  `atMs` and a duration. Render as a horizontal Gantt — time on x, one bar per
  event, coloured by type. This makes an abstract paragraph legible at a glance.
- **The model's reasoning**: why this instrument, why this tick resolution.
- **`adjustments[]`** — deterministic corrections the backend applied after the
  model answered (e.g. "inferred a -1.08% price impulse from the described
  bid-side damage"). Show these. They prove real engineering sits behind the
  model call rather than a raw passthrough.

Offer 3–4 preset prompts as buttons. Judges will not type a 60-word
institutional prompt themselves.

### 2. Simulation — watch it break
Streams from `POST /api/simulations` over SSE. **This is the moment that wins or
loses the pitch, so it must animate.**

- A live price/equity chart building left to right as ticks arrive (~25ms apart,
  about 6 seconds for a full run).
- Band the chart background by `tick.phase`: `warmup` / `shock` / `recovery` /
  `stabilised`.
- A scrolling event log fed by `market_event` frames, colour-coded by `severity`
  (`info` / `warn` / `critical` / `good`). Real messages include *"Spread blew out
  to 43.7 pips"*, *"Book CROSSED: bid above ask"*, *"Bid side evaporated"*,
  *"Market data feed frozen"*.
- Live metric tiles: P&L, position, drawdown, spread, liquidity remaining.
- **If `strategyError` is non-null, that is the headline.** Mark the exact tick on
  the chart with a vertical rule and show something like *"ZeroDivisionError at
  tick 170 of 220 — your code stopped here"*, with the message. Make it feel like
  a finding, not a bug report.
- **If `adapter.adapted` is true, show the adapter panel**: the `interface` the AI
  found, the `mapping[]` it performed, and the `risks[]` it flagged. Example risk:
  *"the strategy ignores bar.halted, so it keeps quoting through the halt."*

There is a several-second wait before the first tick while the AI prepares the
strategy. Show a status line that says what is happening ("adapting your
strategy…"), not a bare spinner.

### 3. Audit — why it failed
`POST /api/audits`. A verdict (`passed`/`marginal`/`failed`), a 0–100 score, a
headline, a narrative, plus `strengths[]`, `weaknesses[]` and `failureModes[]`
(each with its own severity). Two columns, severity-sorted.

### 4. Auto-patch — and prove it helped
`POST /api/strategies/improve` returns rewritten `code`, a `summary`, and
`recommendations[]` (each with `problem` / `change` / `impact`).

Show a **side-by-side diff**, then a "re-run patched version" button that sends the
new code back through stage 2 with `variant: "improved"`. End on a
**before/after comparison**: two equity curves on one chart, original vs improved,
with both P&L figures. That comparison is the closing frame of the demo.

### 5. Run history
`GET /api/runs` — a compact table of past runs. Low priority, build it last.

### 6. Model benchmark
`GET /api/benchmark`. We scored three models on how well they comprehend
institutional prompts, across 5 hand-labelled cases, on event recall, numeric
parameter fidelity, instrument inference and resolution choice.

Render `models` as a leaderboard and `detail` as a models × cases grid. Real
results: DeepSeek-V4-Pro 100.0, Qwen3-235B 97.2, Qwen3-30B 94.8.

**Note this endpoint returns snake_case**, unlike every other endpoint. It is a
stored file served verbatim.

## Hard requirements

1. **The backend URL must be editable at runtime.** A settings input, persisted to
   `localStorage` under `apiBase`. Every call routes through one
   `getApiBase()` helper in `src/lib/api.ts`. The URL changes whenever the
   backend is redeployed, and re-prompting to change a hardcoded constant wastes
   time. Include a connection status dot in the header polling `GET /health`
   every 10s — green on `{"status":"ok"}`, red otherwise.
2. **`EventSource` will not work.** The simulation stream is SSE over **POST**.
   Use `fetch` with a `ReadableStream` reader — there is a working implementation
   in `backend/API.md`.
3. **Build against fixtures first.** `GET /fixtures.json` on the backend returns
   real captured responses for every endpoint, keyed by endpoint name, including
   a full 220-tick simulation. Download it once, commit it into the project, and
   develop with the backend switched off. Wire live calls last.
4. **Every response is camelCase** except `/api/benchmark`.
5. Percentages are already percentages — `drawdownPct: 12.4` means 12.4%.
6. Equity starts at 1,000,000, so absolute P&L numbers look small beside it.

## Design direction

Dark, dense, professional — Bloomberg terminal rather than marketing site. Tabular
numerals everywhere numbers appear; numbers must not jitter as they update during
the stream. Monospace for code, prompts and quoted phrases.

A restrained palette: one neutral surface ramp, one accent for the strategy's own
series, and a reserved status set for `info`/`warn`/`critical`/`good` that is
never reused for ordinary data series.

Charts:
- **Never a dual-axis chart.** Two measures of different scale get two stacked
  charts sharing an x-axis, never two y-scales.
- Thin marks, recessive gridlines, direct labels on a few points rather than a
  number on every point.
- A legend whenever two or more series are present.
- Status must never be carried by colour alone — pair every severity colour with
  an icon or text label, since roughly 1 in 12 men has a colour vision deficiency
  and the judges are a small sample.

Two severity scales exist and they are different — `MarketEvent.severity` is
`info|warn|critical|good`, `Weakness.severity` is `low|medium|high|critical`.
Do not share one colour map between them.

## What not to build

No auth, no signup, no onboarding, no landing page, no pricing page, no user
accounts. It is a single-screen tool that a judge opens and immediately uses.
Every second spent on chrome is a second not spent on the six stages above.
