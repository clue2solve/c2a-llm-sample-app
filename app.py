"""
c2a-llm-sample-app — one-page React chat UI for the Clue2App Daari LLM Gateway.

A deliberately minimal FastAPI app whose only job is to prove the Daari
LLM Gateway binding is wired into a running pod's environment and give
you a real chat UI to confirm it. Platform-managed creds — no BYO.

Required env (fail-fast at startup if missing):
    OPENAI_API_KEY       - minted by Daari (platform creds, not BYO).
    OPENAI_BASE_URL      - gateway endpoint (OpenAI-compatible).
Optional:
    LLM_MODEL            - default: llama-3.1-8b-instant.

Endpoints:
    GET  /          chat one-pager (React UMD + Babel standalone, no build).
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
    """Fail loudly if a required env var is missing — the exact
    failure mode this app exists to catch when a binding is wrong."""
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
    """UI-visible metadata so the page can show which gateway + model it
    is talking to and prove the binding reached the pod."""
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


# --- One-page React UI ----------------------------------------------------
#
# No build step. React 18 + ReactDOM 18 as UMD from cdnjs; Babel standalone
# transpiles the <script type="text/babel"> block in the browser. That is
# the "cost" of staying single-file: a ~230KB Babel runtime download on
# first visit. Acceptable for a dev-focused showcase — the entire point
# of this app is to prove the gateway binding works, not to ship a tuned
# production bundle.
#
# Design direction: "terminal × chat" hybrid.
#   - JetBrains Mono for metadata chips, model names, gateway URL — things
#     a developer would check at a glance.
#   - Inter for chat bubbles — the content people read.
#   - Slate base palette (not warm cream), orange reserved for the Send
#     affordance, soft blue for the gateway-status chip.
#   - Full light + dark via prefers-color-scheme + explicit tokens.

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
    }
    .brand {
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
    }
    .brand h1 {
      font-size: 1rem;
      font-weight: 600;
      letter-spacing: -0.01em;
      margin: 0;
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
    .chip .dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: currentColor; opacity: 0.9;
    }
    .chip.gw .dot {
      animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 0.4; }
      50% { opacity: 1; }
    }

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

    footer {
      padding: 0.75rem 0 1rem;
      border-top: 1px solid var(--border);
    }
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

    /* scrollbar polish */
    main.chat::-webkit-scrollbar { width: 8px; }
    main.chat::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
    main.chat::-webkit-scrollbar-track { background: transparent; }
  </style>
</head>
<body>
  <div id="root"></div>

  <script crossorigin src="https://cdnjs.cloudflare.com/ajax/libs/react/18.3.1/umd/react.production.min.js"></script>
  <script crossorigin src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.3.1/umd/react-dom.production.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/7.25.6/babel.min.js"></script>

  <script type="text/babel" data-presets="react">
    const { useState, useEffect, useRef, useCallback } = React;

    function Chip({ children, variant }) {
      return (
        <span className={"chip " + (variant || "")}>
          <span className="dot" />{children}
        </span>
      );
    }

    function Bubble({ role, children, meta }) {
      return (
        <div>
          <div className={"bubble " + role}>{children}</div>
          {meta ? <div className="meta-row">{meta}</div> : null}
        </div>
      );
    }

    function Dots() {
      return <span className="dots"><span /><span /><span /></span>;
    }

    function App() {
      const [metaInfo, setMetaInfo] = useState({ model: "…", gateway: "…" });
      const [messages, setMessages] = useState([]); // {role,text,meta?,isLoading?,isError?}
      const [input, setInput] = useState("");
      const [sending, setSending] = useState(false);
      const chatRef = useRef(null);
      const inputRef = useRef(null);

      useEffect(() => {
        fetch("/meta").then(r => r.json()).then(setMetaInfo).catch(() => {});
      }, []);

      useEffect(() => {
        if (chatRef.current) {
          chatRef.current.scrollTop = chatRef.current.scrollHeight;
        }
      }, [messages]);

      const gatewayShort = (metaInfo.gateway || "")
        .replace(/^https?:\/\//, "")
        .replace(/\/$/, "");

      const send = useCallback(async () => {
        const text = input.trim();
        if (!text || sending) return;
        setMessages(m => [
          ...m,
          { role: "user", text },
          { role: "asst", text: "", isLoading: true },
        ]);
        setInput("");
        setSending(true);
        try {
          const r = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: text, max_tokens: 400 }),
          });
          const data = await r.json();
          if (!r.ok) {
            const err =
              (data && data.detail && data.detail.error) ||
              (data && data.error) ||
              ("HTTP " + r.status);
            setMessages(m => {
              const copy = m.slice();
              copy[copy.length - 1] = { role: "err", text: err };
              return copy;
            });
            return;
          }
          const u = data.usage || {};
          const metaLine =
            `${data.model} · ${u.prompt_tokens || 0}p + ${u.completion_tokens || 0}c = ${u.total_tokens || 0}t`;
          setMessages(m => {
            const copy = m.slice();
            copy[copy.length - 1] = {
              role: "asst",
              text: data.reply || "(empty reply)",
              meta: metaLine,
            };
            return copy;
          });
        } catch (e) {
          setMessages(m => {
            const copy = m.slice();
            copy[copy.length - 1] = { role: "err", text: String(e) };
            return copy;
          });
        } finally {
          setSending(false);
          setTimeout(() => inputRef.current && inputRef.current.focus(), 0);
        }
      }, [input, sending]);

      const onKey = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          send();
        }
      };

      // Cmd/Ctrl+K focuses the input
      useEffect(() => {
        const h = (e) => {
          if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
            e.preventDefault();
            inputRef.current && inputRef.current.focus();
          }
        };
        window.addEventListener("keydown", h);
        return () => window.removeEventListener("keydown", h);
      }, []);

      return (
        <div className="shell">
          <header>
            <div className="brand">
              <h1>c2a-llm-sample</h1>
              <span className="sub">daari gateway</span>
            </div>
            <div className="chips">
              <Chip variant="gw">{gatewayShort || "connecting…"}</Chip>
              <Chip>{metaInfo.model}</Chip>
            </div>
          </header>

          <main className="chat" ref={chatRef}>
            {messages.length === 0 ? (
              <div className="empty">
                <div>
                  <div style={{marginBottom: "0.5rem"}}>
                    Ask the model anything to prove the binding works.
                  </div>
                  <div style={{fontSize: "0.8rem"}}>
                    e.g. <code>Write a haiku about kubernetes.</code>
                  </div>
                </div>
              </div>
            ) : (
              messages.map((m, i) => (
                <Bubble key={i} role={m.role} meta={m.meta}>
                  {m.isLoading ? <Dots /> : m.text}
                </Bubble>
              ))
            )}
          </main>

          <footer>
            <div className="composer">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={onKey}
                placeholder="Message the model…"
                autoFocus
              />
              <button
                className="send"
                disabled={!input.trim() || sending}
                onClick={send}
              >
                Send
              </button>
            </div>
            <div className="hint">
              <span><kbd>Enter</kbd> send · <kbd>⇧ Enter</kbd> newline · <kbd>⌘K</kbd> focus</span>
              <span>
                <a href="https://github.com/clue2solve/c2a-llm-sample-app"
                   target="_blank" rel="noopener"
                   style={{color: "var(--muted)", textDecoration: "none"}}>source</a>
              </span>
            </div>
          </footer>
        </div>
      );
    }

    ReactDOM.createRoot(document.getElementById("root")).render(<App />);
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return _PAGE
