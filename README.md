# c2a-llm-sample-app

Tiny FastAPI app that proves the Clue2App **Daari LLM Gateway** binding
is wired into a running pod's environment and that calls through the
gateway succeed. Platform-managed credentials — no BYO keys needed.

## What the demo shows

1. Create a per-project LLM Gateway instance on Clue2App. The platform
   mints an `OPENAI_API_KEY` + `OPENAI_BASE_URL` and stores them as a
   Kubernetes secret in your project namespace.
2. Deploy this app via `c2a app create -g <this repo URL>`. The app
   fails fast at startup if those env vars are missing — exactly the
   failure mode a bad binding would produce.
3. Bind the gateway secret into the app's pod with
   `c2a daari llm bind llm-demo <bindingName>`. Knative rolls a new
   revision; the pod now has the env vars.
4. `GET /llm-check` on the deployed URL fires a trivial "reply pong"
   prompt through the gateway and returns `{"ok":true,"model":"...","reply":"..."}`
   on success.

## Endpoints

| Path         | Purpose                                                       |
|--------------|---------------------------------------------------------------|
| `GET /`      | Landing page linking to `/llm-check`.                         |
| `GET /healthz` | Liveness probe. Does NOT call upstream.                     |
| `GET /llm-check` | Posts a trivial prompt to the gateway, returns JSON.      |

## Required env

| Var             | Source                                 | Default                     |
|-----------------|----------------------------------------|-----------------------------|
| `OPENAI_API_KEY` | `c2a daari llm bind` (secret)         | *(required, fail-fast)*     |
| `OPENAI_BASE_URL` | `c2a daari llm bind` (secret)        | *(required, fail-fast)*     |
| `LLM_MODEL`     | optional override                      | `llama-3.1-8b-instant`      |

## End-to-end walkthrough

```sh
# 0. Prereqs: c2a CLI installed + authenticated, active project set.
c2a login
c2a project use <your-project>

# 1. Spin up a platform-creds LLM Gateway instance for this project.
c2a daari llm create sample-llm
# → prints the binding name (e.g. 'sample-llm-llm-gateway').
#   The platform manages the upstream provider key; nothing BYO.

c2a daari llm list                   # confirm the instance is READY

# 2. Deploy this app from the sibling repo.
c2a app create llm-demo \
  -g https://github.com/clue2solve/c2a-llm-sample-app \
  --port 8080
# App builds via kpack + Paketo, then starts in FAIL-FAST state because
# OPENAI_API_KEY / OPENAI_BASE_URL aren't bound yet.

# 3. Bind the LLM Gateway secret into the app.
c2a daari llm bind llm-demo sample-llm-llm-gateway
# Knative rolls a new revision; env vars are now present.

# 4. Hit the demo endpoint.
APP_URL=$(c2a app show llm-demo -f url)
curl "$APP_URL/llm-check"
# → {"ok": true, "model": "llama-3.1-8b-instant", "reply": "pong"}
```

## Why fail-fast?

A silently-missing binding is the exact bug class this demo surfaces
([`coordinator#187`](https://github.com/clue2solve/coordinator/issues/187)).
Better to crash on boot with a clear stderr line than to serve requests
that fail opaquely later at connection time.

## License

MIT — see [`LICENSE`](./LICENSE).
