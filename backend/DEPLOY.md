# Deploying the StressTest API on Vercel

```bash
vercel login
vercel link          # from backend/ — set Root Directory to backend
vercel env add NEBIUS_API_KEY production
vercel env add STRESSTEST_API_KEY production
vercel --prod
```

`vercel.json` rewrites every path to `api/index.py`, which imports the same
FastAPI app that runs under uvicorn locally. Nothing about the app changed.

**This is a monorepo, so Root Directory must be `backend`.** If Vercel builds
from the repo root it will find the Next.js frontend instead and the API will
404 on everything.

## Check these three things the moment it deploys

Vercel is serverless, and the app was built for a long-lived process. Three
things can break, all of them in the first minute, all of them checkable.

### 1. Does the sandbox still work? — the one that matters

The product executes strategy code in a subprocess. Some serverless runtimes do
not allow spawning one, and if this fails, nothing else matters.

```bash
curl https://<app>.vercel.app/health/sandbox
```

```json
{"subprocess": true, "ticks": 3, "fills": 3, "executable": "...", "error": null}
```

`"subprocess": true` means strategy execution works. If it is `false`, read
`error` — and the answer is to move the API to a host that runs a real container
(the previous commit has a working Dockerfile in its history). Do not try to
patch around it by running strategy code in the API process: an infinite loop
would then hang the function instead of hitting the 8s worker timeout, and the
process holding `NEBIUS_API_KEY` would be the one running untrusted code.

### 2. Does the tick stream still stream?

Serverless proxies sometimes buffer a response until it closes, which turns the
live chart into a single jump at the end.

```bash
curl -N -H "X-API-Key: <key>" -H "Content-Type: application/json" \
  -d @- https://<app>.vercel.app/api/simulations <<'JSON'
{"strategy":{"name":"t","code":"def on_tick(bar, book, account):\n    account.buy(1)\n"},
 "scenario":{"id":"c","name":"t","params":{"shockMagnitudePct":-8,"volatilityMultiplier":5,
 "liquidityFactor":0.1,"spreadBps":40,"gapPct":0,"durationMinutes":20,
 "shockDurationMinutes":5,"recoveryMinutes":5}},"variant":"original"}
JSON
```

Ticks should appear gradually over several seconds. If they all land at once,
point the frontend at `POST /api/simulations/sync` instead — same
`SimulationRun` payload, no streaming — and drop the live animation.

### 3. Is the plan's timeout long enough?

`vercel.json` asks for `maxDuration: 300`. **Hobby caps at 60s**; 300s needs Pro.
A run that generates an adapter and then simulates can take 30–60s, so on Hobby
it is genuinely close to the limit. Confirm the plan, and if it is Hobby, either
upgrade or lower `maxDuration` to 60 and expect occasional timeouts on the
slowest institutional prompts.

## Cold starts

Serverless scales to zero, so the first request after idle pays for a container
start plus a numpy import — a few seconds. The URL is permanent and never dies,
but it is not always-warm. Before judging, hit `/health` once to warm it.

## Environment variables

| name | required | purpose |
|---|---|---|
| `NEBIUS_API_KEY` | yes | backend → Nebius model inference |
| `STRESSTEST_API_KEY` | on any public URL | frontend → this API, via `X-API-Key` |

With `STRESSTEST_API_KEY` unset the `/api` routes are **open** and the app logs a
warning at startup. Local dev needs no key; anything public must set one.

Set both for the Production environment. Never commit either — `.env` is in
`.gitignore` and `.vercelignore`.

## Bundle size

Measured at **67.6 MB** installed (numpy 34.6, openai 14.7, pydantic 9.4, the
rest small) against Vercel's 250 MB limit. Not a concern, but `numpy` cannot be
dropped — strategy code is allowed to import it.

## After deploying

Send the frontend two values and nothing else:

```
Backend URL : https://<app>.vercel.app
API key     : <STRESSTEST_API_KEY>
```

Both are settings fields in the frontend, so a redeploy is a paste, not a rebuild.

```bash
curl https://<app>.vercel.app/health
curl https://<app>.vercel.app/health/sandbox
curl https://<app>.vercel.app/api/runs                      # expect 401
curl -H "X-API-Key: <key>" https://<app>.vercel.app/api/runs  # expect 200
```
