"""
c2a-llm-sample-app — single-page chat UI for the Clue2App Daari LLM Gateway.

A deliberately minimal FastAPI app whose only job is to prove the Daari
LLM Gateway binding is wired into a running pod's environment and give
you a real chat UI to confirm it. Platform-managed creds — no BYO.

Zero runtime dependencies on the browser side: vanilla JS, Google Fonts
for type, everything else inline. No React, no CDN JS, no build step.

Required env (fail-fast at startup if missing):
    OPENAI_API_KEY       - minted by Daari (platform creds, not BYO).
    OPENAI_BASE_URL      - gateway endpoint (OpenAI-compatible).
Optional:
    LLM_MODEL            - default: llama-3.1-8b-instant.

Endpoints:
    GET  /          chat one-pager (vanilla JS, no framework, no CDN).
    GET  /healthz   liveness. Does NOT call upstream.
    GET  /meta      JSON {model, gateway, binding_present} — consumed by UI.
    POST /chat      body {prompt, max_tokens?} → {reply, model, usage}.
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


@app.get("/meta")
def meta() -> dict:
    return {
        "model": LLM_MODEL,
        "gateway": OPENAI_BASE_URL,
        "binding_present": True,
    }


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


# --- One-page chat UI -----------------------------------------------------
#
# Design brief: "terminal × chat" hybrid. JetBrains Mono for metadata
# chips (gateway + model — the things a developer glance-verifies the
# binding by), Inter for the chat bubbles people actually read. Slate
# base, orange reserved for Send, soft blue chip for the gateway
# status. Full dark + light.
#
# Implementation: Google Fonts for type, everything else inline. No
# React, no CDN JS, no build step. ~200 LOC of vanilla ES2020 split
# into tiny render/handle functions — a developer reading the source
# sees the whole thing in one scroll.

_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>c2a · llm sample</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #f7f8fa;
      --surface: #ffffff;
      --surface-2: #eff1f5;
      --border: #e4e7ec;
      --ink: #0b1220;
      --ink-2: #475467;
      --muted: #98a2b3;
      --accent: #ea580c;
      --accent-hover: #c2410c;
      --gw-ok: #2563eb;
      --gw-ok-bg: #dbeafe;
      --error: #dc2626;
      --error-bg: #fee2e2;
      --bubble-user: #e0e7ff;
      --bubble-user-ink: #1e1b4b;
      --bubble-asst: var(--surface);
      --bubble-asst-ink: var(--ink);
      --mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      --sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    @media (prefers-color-scheme: dark) {
      :root:not([data-theme="light"]) {
        --bg: #0b1220;
        --surface: #111827;
        --surface-2: #1f2937;
        --border: #1f2937;
        --ink: #e5e7eb;
        --ink-2: #9ca3af;
        --muted: #6b7280;
        --accent: #fb923c;
        --accent-hover: #ea580c;
        --gw-ok: #60a5fa;
        --gw-ok-bg: #1e3a8a;
        --error: #f87171;
        --error-bg: #450a0a;
        --bubble-user: #312e81;
        --bubble-user-ink: #e0e7ff;
        --bubble-asst: var(--surface-2);
        --bubble-asst-ink: var(--ink);
      }
    }
    :root[data-theme="dark"] {
      --bg: #0b1220;
      --surface: #111827;
      --surface-2: #1f2937;
      --border: #1f2937;
      --ink: #e5e7eb;
      --ink-2: #9ca3af;
      --muted: #6b7280;
      --accent: #fb923c;
      --accent-hover: #ea580c;
      --gw-ok: #60a5fa;
      --gw-ok-bg: #1e3a8a;
      --error: #f87171;
      --error-bg: #450a0a;
      --bubble-user: #312e81;
      --bubble-user-ink: #e0e7ff;
      --bubble-asst: var(--surface-2);
      --bubble-asst-ink: var(--ink);
    }
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: var(--sans);
      font-size: 15px;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
    }
    .shell {
      display: grid;
      grid-template-rows: auto 1fr auto;
      max-width: 720px;
      height: 100vh;
      margin: 0 auto;
      padding: 0 1rem;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1rem 0 0.75rem;
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
      gap: 0.5rem;
    }
    .brand { display: flex; align-items: baseline; gap: 0.5rem; }
    .brand h1 {
      font-size: 1rem; font-weight: 600;
      letter-spacing: -0.01em; margin: 0;
    }
    .brand .sub {
      font-family: var(--mono);
      font-size: 0.75rem;
      color: var(--muted);
    }
    .chips { display: flex; gap: 0.4rem; flex-wrap: wrap; }
    .chip {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-family: var(--mono);
      font-size: 0.72rem;
      color: var(--ink-2);
      background: var(--surface);
      border: 1px solid var(--border);
      padding: 0.2rem 0.5rem;
      border-radius: 999px;
      white-space: nowrap;
    }
    .chip.gw { color: var(--gw-ok); background: var(--gw-ok-bg); border-color: transparent; }
    .chip .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: 0.9; }
    .chip.gw .dot { animation: pulse 2s ease-in-out infinite; }
    @keyframes pulse { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }

    main.chat {
      overflow-y: auto;
      padding: 1rem 0;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .empty {
      display: grid;
      place-items: center;
      height: 100%;
      color: var(--muted);
      text-align: center;
      font-size: 0.9rem;
      padding: 2rem;
    }
    .empty code {
      font-family: var(--mono);
      font-size: 0.85em;
      background: var(--surface-2);
      padding: 0.08em 0.4em;
      border-radius: 4px;
      color: var(--ink-2);
    }
    .bubble {
      max-width: 90%;
      padding: 0.65rem 0.85rem;
      border-radius: 12px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .bubble.user {
      align-self: flex-end;
      background: var(--bubble-user);
      color: var(--bubble-user-ink);
      border-top-right-radius: 4px;
    }
    .bubble.asst {
      align-self: flex-start;
      background: var(--bubble-asst);
      color: var(--bubble-asst-ink);
      border: 1px solid var(--border);
      border-top-left-radius: 4px;
    }
    .bubble.err {
      align-self: flex-start;
      background: var(--error-bg);
      color: var(--error);
      border: 1px solid var(--error);
      border-top-left-radius: 4px;
    }
    .meta-row {
      font-family: var(--mono);
      font-size: 0.7rem;
      color: var(--muted);
      margin-top: 0.25rem;
    }
    .dots { display: inline-flex; gap: 3px; align-items: center; }
    .dots span {
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--muted);
      animation: bounce 1.3s ease-in-out infinite;
    }
    .dots span:nth-child(2) { animation-delay: 0.15s; }
    .dots span:nth-child(3) { animation-delay: 0.3s; }
    @keyframes bounce {
      0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
      40% { transform: scale(1); opacity: 1; }
    }

    footer { padding: 0.75rem 0 1rem; border-top: 1px solid var(--border); }
    .composer {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 0.5rem;
      align-items: end;
    }
    textarea {
      width: 100%;
      min-height: 44px;
      max-height: 180px;
      resize: none;
      font-family: inherit;
      font-size: 0.95rem;
      line-height: 1.4;
      color: var(--ink);
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.6rem 0.75rem;
      outline: none;
      transition: border-color 0.12s ease;
    }
    textarea:focus { border-color: var(--accent); }
    button.send {
      font-family: inherit;
      font-weight: 500;
      font-size: 0.9rem;
      padding: 0 1rem;
      height: 44px;
      border: none;
      border-radius: 10px;
      background: var(--accent);
      color: #fff;
      cursor: pointer;
      transition: background 0.12s ease;
    }
    button.send:hover:not(:disabled) { background: var(--accent-hover); }
    button.send:disabled { opacity: 0.5; cursor: not-allowed; }
    .hint {
      display: flex;
      justify-content: space-between;
      font-family: var(--mono);
      font-size: 0.68rem;
      color: var(--muted);
      margin-top: 0.4rem;
    }
    .hint kbd {
      font-family: var(--mono);
      font-size: 0.95em;
      background: var(--surface-2);
      padding: 0.05em 0.35em;
      border-radius: 3px;
      border: 1px solid var(--border);
    }
    a { color: var(--muted); text-decoration: none; }
    a:hover { color: var(--ink-2); }

    main.chat::-webkit-scrollbar { width: 8px; }
    main.chat::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
    main.chat::-webkit-scrollbar-track { background: transparent; }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div class="brand">
        <h1>c2a-llm-sample</h1>
        <span class="sub">daari gateway</span>
      </div>
      <div class="chips">
        <span id="chip-gw" class="chip gw"><span class="dot"></span><span>connecting…</span></span>
        <span id="chip-model" class="chip"><span class="dot"></span><span>…</span></span>
      </div>
    </header>

    <main id="chat" class="chat">
      <div class="empty" id="empty">
        <div>
          <div style="margin-bottom:0.5rem;">Ask the model anything to prove the binding works.</div>
          <div style="font-size:0.8rem;">e.g. <code>Write a haiku about kubernetes.</code></div>
        </div>
      </div>
    </main>

    <footer>
      <div class="composer">
        <textarea id="prompt" placeholder="Message the model…" autofocus></textarea>
        <button id="send" class="send" disabled>Send</button>
      </div>
      <div class="hint">
        <span><kbd>Enter</kbd> send · <kbd>⇧ Enter</kbd> newline · <kbd>⌘K</kbd> focus</span>
        <span><a href="https://github.com/clue2solve/c2a-llm-sample-app" target="_blank" rel="noopener">source</a></span>
      </div>
    </footer>
  </div>

  <script>
    (function () {
      const $ = (id) => document.getElementById(id);
      const chatEl = $("chat");
      const emptyEl = $("empty");
      const promptEl = $("prompt");
      const sendBtn = $("send");
      const chipGw = $("chip-gw").lastElementChild;
      const chipModel = $("chip-model").lastElementChild;

      let sending = false;
      let messages = []; // {role: "user"|"asst"|"err", text, meta?}

      // --- meta chip wiring --------------------------------------------
      fetch("/meta")
        .then((r) => r.json())
        .then((m) => {
          const short = (m.gateway || "").replace(/^https?:\/\//, "").replace(/\/$/, "");
          chipGw.textContent = short || "unknown";
          chipModel.textContent = m.model || "unknown";
        })
        .catch(() => { chipGw.textContent = "offline"; });

      // --- render ------------------------------------------------------
      function render() {
        if (messages.length === 0) {
          emptyEl.hidden = false;
          chatEl.innerHTML = "";
          chatEl.appendChild(emptyEl);
          return;
        }
        emptyEl.hidden = true;
        chatEl.innerHTML = "";
        for (const m of messages) {
          const wrap = document.createElement("div");
          const bubble = document.createElement("div");
          bubble.className = "bubble " + m.role;
          if (m.isLoading) {
            bubble.innerHTML = '<span class="dots"><span></span><span></span><span></span></span>';
          } else {
            bubble.textContent = m.text || "";
          }
          wrap.appendChild(bubble);
          if (m.meta) {
            const meta = document.createElement("div");
            meta.className = "meta-row";
            meta.textContent = m.meta;
            wrap.appendChild(meta);
          }
          chatEl.appendChild(wrap);
        }
        chatEl.scrollTop = chatEl.scrollHeight;
      }

      function updateSendState() {
        sendBtn.disabled = sending || promptEl.value.trim().length === 0;
      }

      // --- send --------------------------------------------------------
      async function send() {
        const text = promptEl.value.trim();
        if (!text || sending) return;
        sending = true;
        messages.push({ role: "user", text });
        messages.push({ role: "asst", isLoading: true });
        promptEl.value = "";
        updateSendState();
        render();
        try {
          const r = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: text, max_tokens: 400 }),
          });
          const data = await r.json();
          const last = messages[messages.length - 1];
          if (!r.ok) {
            const err =
              (data && data.detail && data.detail.error) ||
              (data && data.error) ||
              ("HTTP " + r.status);
            Object.assign(last, { role: "err", text: err, isLoading: false });
          } else {
            const u = data.usage || {};
            last.role = "asst";
            last.isLoading = false;
            last.text = data.reply || "(empty reply)";
            last.meta =
              data.model + " · " +
              (u.prompt_tokens || 0) + "p + " +
              (u.completion_tokens || 0) + "c = " +
              (u.total_tokens || 0) + "t";
          }
        } catch (e) {
          const last = messages[messages.length - 1];
          Object.assign(last, { role: "err", text: String(e), isLoading: false });
        } finally {
          sending = false;
          updateSendState();
          render();
          setTimeout(() => promptEl.focus(), 0);
        }
      }

      // --- events ------------------------------------------------------
      promptEl.addEventListener("input", updateSendState);
      promptEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          send();
        }
      });
      sendBtn.addEventListener("click", send);
      window.addEventListener("keydown", (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
          e.preventDefault();
          promptEl.focus();
        }
      });

      render();
    })();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return _PAGE
