# Portable image for the StressTest API. Runs unchanged on Fly.io, Cloud Run,
# Railway, Hugging Face Spaces or any plain Docker host, so the app is never
# tied to one provider.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first so edits to the source do not invalidate the pip layer.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# This service executes strategy code that callers post to it. engine/safeexec.py
# restricts builtins and imports, but it is not a boundary against a determined
# attacker, so the process must not be root and must not own its own source.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R root:root /app \
    && chmod -R a-w /app
USER appuser

ENV PORT=8080
EXPOSE 8080

# Shell form so ${PORT} is expanded — hosts inject their own port number.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
