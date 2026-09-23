"""Deploy the StressTest API on Modal.

    modal deploy modal_app.py

Modal is the right host for this service specifically because it runs untrusted
code. engine/safeexec.py restricts builtins and imports, but that only stops
accidents and casual misuse — it is not a boundary against a determined
attacker. Here every request is handled inside a gVisor-sandboxed container
with no access to any other machine, so a strategy that escapes the restricted
namespace escapes into a disposable container instead of onto a laptop.
"""

from pathlib import Path

import modal

HERE = Path(__file__).parent

# venv is gigabytes and platform-specific, .env belongs in a Modal Secret, and
# the rest is local scratch that must not end up in a published image.
EXCLUDE = [
    "venv/**", ".venv/**", "**/__pycache__/**", "**/*.pyc",
    ".env", "*.log", ".uvicorn*", ".tunnel*",
    "ecb*.json", "test_*.py", "smoke_test.py", "probe_usage.py",
]

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements(str(HERE / "requirements.txt"))
    # /root is the container working directory and is already on sys.path, so
    # `import main` resolves to the app exactly as it does locally.
    .add_local_dir(HERE, remote_path="/root", ignore=EXCLUDE)
)

app = modal.App("stresstest")

# NEBIUS_API_KEY is required. STRESSTEST_API_KEY is optional but should be set:
# without it the /api routes are open, and this URL is public.
secret = modal.Secret.from_name("stresstest", required_keys=["NEBIUS_API_KEY"])


@app.function(
    image=image,
    secrets=[secret],
    # A model call plus a full simulation is slow; the default would cut the
    # SSE stream off mid-run.
    timeout=900,
    # Judges arrive without warning, so pay for one warm container rather than
    # showing them a cold start.
    min_containers=1,
    scaledown_window=300,
    cpu=2.0,
    memory=2048,
)
@modal.asgi_app(label="stresstest")
def api():
    from main import app as fastapi_app

    return fastapi_app
