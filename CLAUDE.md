# CLAUDE.md — Accel AI Innovate Hackathon Spec

## 1. Project Overview & Hackathon Rules
- Architecture: Monorepo containing `/frontend` (Next.js 14 App Router, Tailwind CSS, shadcn/ui) and `/backend` (FastAPI, Python 3.11, Pydantic v2).
- Core Engine: Nebius Token Factory (OpenAI-compatible client). All LLM inference MUST route through Nebius endpoints, not direct OpenAI/Anthropic APIs.
- Git & Team Boundaries: Teammates work on separate branches (`feature/frontend` and `feature/backend`). Never modify `/frontend` files when fulfilling backend requests, and vice versa.

## 2. Essential Commands & Verification
Always verify work with these exact commands before declaring a feature complete:

- Backend Dev: `cd backend && uvicorn main:app --reload --port 8000`
- Backend Lint & Typecheck: `cd backend && mypy . && pytest`
- Frontend Dev: `cd frontend && npm run dev`
- Frontend Build Check: `cd frontend && npm run build` (Run this before committing to catch TypeScript/JSX breaks early)

## 3. Nebius Token Factory Integration Rules
- Base URL: `https://api.tokenfactory.nebius.com/v1/`
- API Key: Loaded exclusively via `NEBIUS_API_KEY` environment variable.
- Target Models: Default to `meta-llama/Meta-Llama-3.1-70B-Instruct` or `Qwen/Qwen2.5-Coder-32B-Instruct`.
- Implementation: Always use the standard `openai.OpenAI` or `openai.AsyncOpenAI` client pointing to the Nebius base URL.
- Error Handling: Wrap model calls in try/except blocks catching rate limits (`openai.RateLimitError`) and connection drops. Always return structured JSON.

## 4. Coding & Architecture Standards
- Modularity: Keep files under 150 lines. Decompose UI into small components in `components/` and backend logic into `services/` and `routers/`.
- Strict Schemas: Every FastAPI endpoint must take a Pydantic `BaseModel` input and define a typed response schema (`response_model=...`).
- Grounding: When using search or live data (Tavily/Firecrawl), pass scraped web content directly inside system/user prompt wrappers to prevent hallucinations.
- Zero Stubs: Never leave `// TODO`, `pass`, or mock placeholders in code unless explicitly requested. Write fully implemented, functional code.

## 5. Fallback & Stage Demo Safety
- Every API endpoint that touches Nebius or Tavily must support a `use_mock=true` query param or fallback to a local JSON fixture if the external network drops during judging.