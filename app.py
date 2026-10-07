"""
c2a-llm-sample-app — one-pager showcase for the Clue2App Daari LLM Gateway.

A single-page web app that fails fast when the Daari LLM Gateway
binding is missing and, when bound, lets you type a prompt and see the
model's reply right on the page. The POST /chat endpoint is also the
JSON API path if you'd rather curl it.

Required environment variables (fail-fast at import time if missing):
    OPENAI_API_KEY       - minted by the Daari LLM Gateway (platform
                           creds — not a BYO provider key).
    OPENAI_BASE_URL      - gateway endpoint (OpenAI-compatible).
Optional:
    LLM_MODEL            - default: llama-3.1-8b-instant.

Endpoints:
    GET  /          one-pager UI (prompt box + reply).
    GET  /healthz   liveness probe. Does NOT call upstream.
    GET  /llm-check sanity ping — fixed "reply pong" prompt, JSON.
    POST /chat      JSON body {"prompt": "..."} → {"reply": "...", "model": "..."}.
"""
import os
import sys

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

REQUIRED_ENV_VARS = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
)


def _check_required_env() -> None:
    """Fail loudly if a required env var is missing — that's the exact
    failure mode this app exists to surface when a binding is wrong."""
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


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    max_tokens: int = Field(default=400, ge=1, le=2000)


def _call_gateway(prompt: str, max_tokens: int) -> dict:
    resp = httpx.post(
        f"{OPENAI_BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    reply = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {"reply": reply, "model": LLM_MODEL, "usage": usage}


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.get("/llm-check")
def llm_check():
    try:
        out = _call_gateway("Reply with just the word: pong", max_tokens=10)
        return JSONResponse({"ok": True, **out})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/chat")
def chat(req: ChatRequest):
    try:
        return JSONResponse(_call_gateway(req.prompt, req.max_tokens))
    except httpx.HTTPStatusError as e:
        detail = {
            "error": "upstream HTTP error",
            "status": e.response.status_code,
            "body": e.response.text[:400],
        }
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail={"error": str(e)})


# --- One-pager UI ----------------------------------------------------------
#
# Hand-rolled HTML + CSS + a tiny bit of JS so the whole showcase is
# self-contained in one file. No build step, no framework. The point of
# the showcase is to prove the gateway binding works end-to-end from a
# running pod; the UI is deliberately minimal so the gateway call is
# the thing you focus on.

_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>c2a-llm-sample-app</title>
  <style>
    :root {
      --bg: #f8fafc;
      --surface: #ffffff;
      --border: #e2e8f0;
      --ink: #0f172a;
      --muted: #64748b;
      --accent: #ea580c;
      --accent-hover: #c2410c;
      --ok: #16a34a;
      --error: #dc2626;
      --code-bg: #f1f5f9;
    }
    @media (prefers-color-scheme: dark) {
      :root:not([data-theme="light"]) {
        --bg: #0f172a;
        --surface: #1e293b;
        --border: #334155;
        --ink: #e2e8f0;
        --muted: #94a3b8;
        --accent: #fb923c;
        --accent-hover: #ea580c;
        --ok: #4ade80;
        --error: #f87171;
        --code-bg: #0f172a;
      }
    }
    :root[data-theme="dark"] {
      --bg: #0f172a;
      --surface: #1e293b;
      --border: #334155;
      --ink: #e2e8f0;
      --muted: #94a3b8;
      --accent: #fb923c;
      --accent-hover: #ea580c;
      --ok: #4ade80;
      --error: #f87171;
      --code-bg: #0f172a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.5;
    }
    .wrap {
      max-width: 720px;
      margin: 3rem auto;
      padding: 0 1.5rem;
    }
    header {
      margin-bottom: 2rem;
    }
    header h1 {
      font-size: 1.75rem;
      margin: 0 0 0.25rem;
      letter-spacing: -0.02em;
    }
    header p {
      margin: 0;
      color: var(--muted);
      font-size: 0.95rem;
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1.25rem;
      margin-bottom: 1.25rem;
    }
    .meta {
      display: flex;
      gap: 1.5rem;
      font-size: 0.825rem;
      color: var(--muted);
      flex-wrap: wrap;
    }
    .meta code {
      background: var(--code-bg);
      padding: 0.1em 0.4em;
      border-radius: 3px;
      font-size: 0.9em;
      color: var(--ink);
    }
    form { display: grid; gap: 0.75rem; }
    label {
      font-size: 0.85rem;
      font-weight: 500;
      color: var(--muted);
    }
    textarea {
      resize: vertical;
      min-height: 100px;
      padding: 0.75rem;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--bg);
      color: var(--ink);
      font-family: inherit;
      font-size: 1rem;
    }
    textarea:focus {
      outline: 2px solid var(--accent);
      outline-offset: -1px;
    }
    .row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
    }
    button {
      background: var(--accent);
      color: white;
      border: none;
      padding: 0.6rem 1.1rem;
      border-radius: 6px;
      font-size: 0.95rem;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }
    button:hover:not(:disabled) { background: var(--accent-hover); }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .hint { color: var(--muted); font-size: 0.825rem; }
    .reply {
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.925rem;
      background: var(--code-bg);
      padding: 0.9rem 1rem;
      border-radius: 6px;
      border: 1px solid var(--border);
      min-height: 1.5em;
    }
    .reply.empty { color: var(--muted); font-style: italic; font-family: inherit; }
    .reply.error { color: var(--error); }
    .usage {
      margin-top: 0.5rem;
      font-size: 0.8rem;
      color: var(--muted);
    }
    footer {
      margin-top: 2rem;
      font-size: 0.825rem;
      color: var(--muted);
      text-align: center;
    }
    footer a { color: var(--accent); text-decoration: none; }
    footer a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>c2a-llm-sample-app</h1>
      <p>Clue2App &middot; Daari LLM Gateway binding showcase</p>
    </header>

    <div class="card">
      <div class="meta">
        <div>Gateway: <code id="base-url">__BASE_URL__</code></div>
        <div>Model: <code id="model">__MODEL__</code></div>
      </div>
    </div>

    <form id="chat-form" class="card">
      <label for="prompt">Your prompt</label>
      <textarea id="prompt" name="prompt" required
        placeholder="Ask the model anything. Example: &quot;Write a haiku about kubernetes.&quot;"></textarea>
      <div class="row">
        <div class="hint">Enter &nbsp;&middot;&nbsp; <kbd>Cmd/Ctrl+Enter</kbd> to send</div>
        <button type="submit" id="send">Send</button>
      </div>
    </form>

    <div class="card" id="reply-card" hidden>
      <label>Response</label>
      <div class="reply empty" id="reply">(waiting)</div>
      <div class="usage" id="usage"></div>
    </div>

    <footer>
      <a href="/llm-check">GET /llm-check</a> &middot;
      <a href="/healthz">GET /healthz</a> &middot;
      <a href="https://github.com/clue2solve/c2a-llm-sample-app" target="_blank" rel="noopener">source</a>
    </footer>
  </div>

  <script>
    const form = document.getElementById('chat-form');
    const promptEl = document.getElementById('prompt');
    const sendBtn = document.getElementById('send');
    const card = document.getElementById('reply-card');
    const replyEl = document.getElementById('reply');
    const usageEl = document.getElementById('usage');

    async function send() {
      const prompt = promptEl.value.trim();
      if (!prompt) return;
      card.hidden = false;
      replyEl.classList.remove('empty', 'error');
      replyEl.textContent = 'Thinking…';
      usageEl.textContent = '';
      sendBtn.disabled = true;
      try {
        const res = await fetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt })
        });
        const data = await res.json();
        if (!res.ok) {
          replyEl.classList.add('error');
          replyEl.textContent =
            (data && data.detail && data.detail.error) ||
            (data && data.error) ||
            ('Error ' + res.status);
          return;
        }
        replyEl.textContent = data.reply;
        if (data.usage && (data.usage.prompt_tokens || data.usage.completion_tokens)) {
          usageEl.textContent =
            `tokens: prompt ${data.usage.prompt_tokens || 0}, ` +
            `completion ${data.usage.completion_tokens || 0}, ` +
            `total ${data.usage.total_tokens || 0} · model ${data.model}`;
        } else {
          usageEl.textContent = `model: ${data.model}`;
        }
      } catch (e) {
        replyEl.classList.add('error');
        replyEl.textContent = String(e);
      } finally {
        sendBtn.disabled = false;
      }
    }

    form.addEventListener('submit', (e) => { e.preventDefault(); send(); });
    promptEl.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        send();
      }
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return _PAGE.replace("__BASE_URL__", OPENAI_BASE_URL).replace("__MODEL__", LLM_MODEL)
