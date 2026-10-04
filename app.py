"""
c2a-llm-sample-app — Daari LLM Gateway binding showcase.

A minimal FastAPI app whose only job is to prove that
`c2a daari llm bind` wires the LLM Gateway credentials into a running
pod's environment and that calls through the gateway succeed.

Required environment variables (all fail-fast at import time if missing):
    OPENAI_API_KEY       - minted by the Daari LLM Gateway for this
                           project (platform-managed, NOT a BYO key).
    OPENAI_BASE_URL      - the gateway endpoint
                           (e.g. https://llm-gateway.control.apps.clue2.app).
Optional:
    LLM_MODEL            - default: llama-3.1-8b-instant

Endpoints:
    GET /          - landing page linking to /llm-check
    GET /healthz   - liveness probe (does NOT call upstream)
    GET /llm-check - calls the Daari LLM Gateway with a trivial prompt
                     and returns {"ok": true, "model": "...", "reply": "..."}
                     on success, {"ok": false, "error": "..."} with HTTP 500
                     on failure.
"""
import os
import sys

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

REQUIRED_ENV_VARS = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
)


def _check_required_env() -> None:
    """Fail loudly if any required env var is missing — the exact
    failure mode this app exists to catch when a binding is misconfigured."""
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        sys.stderr.write(
            "FATAL: c2a-llm-sample-app missing env var(s): "
            f"{', '.join(missing)}\n"
            "Expected from `c2a daari llm bind <app> <binding>`. "
            "Refusing to start.\n"
        )
        raise SystemExit(1)


_check_required_env()

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_BASE_URL = os.environ["OPENAI_BASE_URL"]
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.1-8b-instant")

app = FastAPI(title="c2a-llm-sample-app")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>c2a-llm-sample-app</title>
    <style>
      body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        max-width: 640px; margin: 4rem auto; padding: 0 1rem;
        color: #1e293b;
      }}
      code {{ background: #f1f5f9; padding: 0.1em 0.35em; border-radius: 3px; }}
      a {{ color: #ea580c; }}
    </style>
  </head>
  <body>
    <h1>c2a-llm-sample-app</h1>
    <p>Daari LLM Gateway binding showcase.</p>
    <p>Configured to call <code>{OPENAI_BASE_URL}</code>
       with model <code>{LLM_MODEL}</code>.</p>
    <p>
      <a href="/llm-check">GET /llm-check</a> &mdash;
      sends a trivial &ldquo;reply pong&rdquo; prompt through the gateway.
    </p>
  </body>
</html>
"""


@app.get("/llm-check")
def llm_check():
    try:
        resp = httpx.post(
            f"{OPENAI_BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "user", "content": "Reply with just the word: pong"},
                ],
                "max_tokens": 10,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"]
        return JSONResponse({"ok": True, "model": LLM_MODEL, "reply": reply})
    except Exception as e:  # noqa: BLE001 - surface any failure as ok:false
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
