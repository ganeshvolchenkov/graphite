# Deploying the StressTest API

The deployable unit is `Dockerfile`. It is plain Docker with no host-specific
anything, so it runs on Fly.io, Cloud Run, Railway, Hugging Face Spaces or a VPS.
Nothing below is hard to undo, and moving host later costs one command.

Verified locally before writing this:

```
docker build -t stresstest:test .
docker run -d -p 8099:8080 -e STRESSTEST_API_KEY=... stresstest:test
```

| check | result |
|---|---|
| image builds | yes, `python:3.11-slim` |
| runs as | `appuser`, uid 10001, not root |
| `/app` writable | no — `touch` denied |
| `/api` without key | `401` |
| `/api` with key | `200` |
| sandbox in container | 220 ticks, no error |
| numpy inside a strategy | runs clean |

## Fly.io (recommended)

Deploys from this directory, so it needs no GitHub access — which matters here,
because the git credentials on this machine belong to a different account.

```bash
fly auth login                                   # browser
fly launch --copy-config --no-deploy             # claims the app name, keeps fly.toml
fly secrets set NEBIUS_API_KEY=xxx STRESSTEST_API_KEY=yyy
fly deploy --remote-only                         # builds on Fly, no local Docker needed
```

Then:

```bash
fly status          # should show 1 machine running
fly logs
fly open /dashboard
```

The URL is `https://<app-name>.fly.dev` and it does not change between deploys.

`fly.toml` sets `auto_stop_machines = 'off'` and `min_machines_running = 1`, so it
never scales to zero and never cold-starts in front of a judge. That is the whole
reason for choosing this over a free tier that sleeps.

**Cost:** one `shared-cpu-1x` / 1GB machine runs about $5/month. Not free. If it
must be $0, see Cloud Run below and accept a cold start.

## Google Cloud Run (the $0 option)

Generous always-free tier, but it scales to zero, so the first request after idle
waits 2–5 seconds while the container starts.

```bash
gcloud run deploy stresstest \
  --source . --region europe-west4 --allow-unauthenticated \
  --set-env-vars STRESSTEST_API_KEY=yyy --set-env-vars NEBIUS_API_KEY=xxx
```

Add `--min-instances 1` to stop the cold starts; that costs roughly the same as Fly.

## Environment variables

| name | required | purpose |
|---|---|---|
| `NEBIUS_API_KEY` | yes | backend → Nebius model inference |
| `STRESSTEST_API_KEY` | on any public URL | frontend → this API, via `X-API-Key` |
| `PORT` | no | injected by the host; defaults to 8080 |

With `STRESSTEST_API_KEY` unset the `/api` routes are **open** and the app logs a
warning at startup. That is deliberate — local dev needs no key and a host missing
the variable should still demo rather than 401 everything — but anything reachable
from the internet must set it.

Never bake either key into the image. `.env` is in `.dockerignore` and `.gitignore`.

## After deploying

Send the frontend two values, and nothing else:

```
Backend URL : https://<app-name>.fly.dev
API key     : <STRESSTEST_API_KEY>
```

Both are settings fields in the frontend, so a redeploy is a paste, not a rebuild.

Confirm it end to end:

```bash
curl https://<app>.fly.dev/health
curl -H "X-API-Key: <key>" https://<app>.fly.dev/api/runs
curl https://<app>.fly.dev/api/runs        # expect 401
```

Then check the streaming endpoint actually streams rather than buffering — some
proxies hold the response until it closes, which kills the live chart. If ticks
arrive in one clump, switch the frontend to `POST /api/simulations/sync`.
