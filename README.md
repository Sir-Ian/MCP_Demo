# MCP_Demo

A small demo Model Context Protocol (MCP) server implemented with FastAPI. It ships a tiny frontend and a handful of demo tools (weather, crypto, file, health) so you can exercise tool integrations (for example with Claude or other assistants that support MCP-style tool hooks).

This README shows how to install, run, and connect the MCP server to Claude (or other assistants). It includes troubleshooting notes and a short reference for the API endpoints the server exposes.

## Contents

- `app.py` — FastAPI MCP demo server and static UI mounting
- `static/` — tiny web UI (`index.html`, `app.js`, `style.css`)
- `resources/docs/` — shipped example files (served via the `/mcp/file` tool)
- `requirements.txt` — Python dependencies

## Quick overview

The server exposes the following demo tools under `/mcp/*`:

- `/mcp/weather` (POST) — returns a small daily forecast; accepts `city` or `lat/lon` and `days` (1–7). Supports `x-demo-fallback` header to skip external network calls and return deterministic demo data.
- `/mcp/crypto` (POST) — returns a price for `btc`, `eth`, or `sol`; supports `x-demo-fallback` header for deterministic values.
- `/mcp/file` (POST) — reads a file from `resources/docs` and returns clipped text.
- `/mcp/health` (GET) — server health and uptime.

There is also a tiny frontend shipped in `static/index.html` that exercises these endpoints and is served at the root URL.

## Requirements

- Windows, macOS, or Linux with Python 3.11+ (this README uses PowerShell examples for Windows).
- Git (if you cloned the repository).

Recommended: use a virtual environment to avoid changing your system Python.

## Install (Windows PowerShell)

1. If you do not have Python installed, download and install it from https://www.python.org/downloads/windows/. During install, check "Add Python to PATH".

2. From the repo root, create and activate a virtual environment (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If you already used a different venv name (for example `.venv-2`), activate that instead:

```powershell
.\.venv-2\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

Note: There are known compatibility variations between FastAPI and Pydantic versions. If you encounter errors mentioning `ForwardRef._evaluate()` or similar, try the pinned versions used in this repo (installed by `requirements.txt`). If you upgrade packages, prefer the matching FastAPI/Pydantic pairings (FastAPI <-> Pydantic v1 or FastAPI >=0.100 / Pydantic v2). See Troubleshooting below.

## Run the server

Start the app with the venv's Python (PowerShell):

```powershell

.\.venv\Scripts\python.exe app.py

# or if you used another env name:
.\.venv-2\Scripts\python.exe app.py
```

The server will start on `http://127.0.0.1:8000` by default. Open that URL in your browser to see the demo UI. The OpenAPI docs are at `http://127.0.0.1:8000/docs`.

If port 8000 is already in use, stop the process that is bound to it, or run the server on a different port by editing the `uvicorn.run(...)` call in `app.py` or running `uvicorn` directly, for example:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8001
```

## API Reference (summary)

- POST /mcp/weather
	- Body: { city?: string, lat?: number, lon?: number, days: number }
	- Headers: `x-demo-fallback: 1|true` to force fallback (no outgoing network).

- POST /mcp/crypto
	- Body: { symbol: string, vs?: string }
	- Accepts `symbol` like `btc`, `eth`, `sol`.

- POST /mcp/file
	- Body: { name: string, max_chars: int }
	- `name` resolves to files under `resources/docs`.

- GET /mcp/health
	- Returns server name, uptime, and versions.

Tip: use the shipped frontend at `/` to exercise tools quickly.

## Claude (MCP) integration

This project was designed to be used as an MCP tool server for assistant integrations. To connect it to Claude Desktop (or another MCP-capable assistant):

1. Make sure the server is running and reachable at the configured base URL (default is `http://127.0.0.1:8000`). Open the health endpoint to verify:

```powershell
Tiny demo server to prove the MCP concept (tools+JSON+STDIO/http). This repository contains a minimal FastAPI app that exposes three "data lanes" (weather, crypto, file summarizer) plus a health endpoint.
curl http://127.0.0.1:8000/mcp/health
```

2. Add a Claude config JSON (example below). If you're using Claude Desktop, the config is typically stored under your app config location — in our tests we used `claude_desktop_config.json`.

Example Claude MCP config (minimal):

```json
{
	"server_url": "http://127.0.0.1:8000",
	"tools": [
		{ "name": "weather", "path": "/mcp/weather", "input_schema": "WeatherIn", "output_schema": "WeatherOut" },
		{ "name": "crypto",  "path": "/mcp/crypto",  "input_schema": "CryptoIn",  "output_schema": "CryptoOut" },
		{ "name": "file",    "path": "/mcp/file",    "input_schema": "FileIn",    "output_schema": "FileOut" },
		{ "name": "health",  "path": "/mcp/health",  "input_schema": "none",     "output_schema": "HealthOut", "http_method": "GET" }
	]
}
```

Notes for Claude integration:

- Ensure Claude can reach `http://127.0.0.1:8000` from the machine where it runs. If Claude runs elsewhere (cloud), you'll need to expose the MCP server (ngrok, localtunnel, or host it publicly) and secure it appropriately.
- The server has CORS enabled (for demo convenience) and supports a simple tool catalog at `/mcp/tools`.
- If Claude requires explicit JSON schemas in the config, include the `input_schema` / `output_schema` objects (JSON Schema) rather than just names. An example schema-filled config is provided in the repo's documentation/tests.

3. Restart Claude (desktop) after updating its config so it picks up the new tools. Then try asking Claude to use a tool, e.g. "What's the weather in Chicago?".

## Development notes / code pointers

- `app.py` centralizes the endpoints and static mounting. The root route redirects to `/static/index.html`.
- The demo uses `httpx` for outgoing HTTP; network calls are guarded by a 5s timeout and have a deterministic fallback mode.
- Look at `resources/docs/ai-safety-notes.txt` for a shipped example file used by the File tool.

## Troubleshooting

- "Python was not found" — install Python and add it to PATH or run the full path to the interpreter.
- Activation errors in PowerShell — make sure script execution is allowed or use the `Activate.ps1` script as shown above. If you see `source` errors, that's a Unix shell command; use the PowerShell activation form instead.
- "Port 8000 already in use" — stop the existing process (`Ctrl+C` in the server terminal) or find/kill the process using PowerShell: `Stop-Process -Name python -Force` (careful, this kills all Python processes).
- Pydantic / FastAPI compatibility errors (examples: `ForwardRef._evaluate()` missing argument) — these come from mixing Pydantic v1 style annotations with Pydantic v2 runtime. Recommended approach:
	- Use the package versions pinned in `requirements.txt` for the code as written.
	- Or upgrade the app models to Pydantic v2 idioms (the repo contains a few annotated examples for Pydantic v2 compatibility).

## Example quick smoke test (PowerShell)

```powershell

.\.venv\Scripts\Activate.ps1
Run (recommended in a venv)
.\.venv\Scripts\python.exe app.py

curl http://127.0.0.1:8000/mcp/health
```

## Contributing

Small, focused changes are welcome. If you add or change APIs, update the README and the sample Claude config.

---

If you'd like, I can also:

- add a `docker-compose.yml` to run the server inside a container,
- create a pre-built Claude config that includes full JSON Schema objects, or
- add a small test script that exercises each endpoint automatically.

Tell me which of those you'd like next.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Endpoints
- GET /mcp/tools — tool catalog
- POST /mcp/weather — WeatherIn -> WeatherOut
- POST /mcp/crypto — CryptoIn -> CryptoOut
- POST /mcp/file — FileIn -> FileOut (reads files in resources/docs)
- GET /mcp/health — HealthOut

Frontend demo
1) Start the server (inside venv):

```bash
python3 -m uvicorn app:app --host 127.0.0.1 --port 8000
```

2) Open your browser to: http://127.0.0.1:8000/ — a tiny UI will let you call each lane and show JSON responses. The UI uses the same HTTP endpoints and showcases deterministic fallbacks for offline demos.

Demo mode & orchestration
- The UI includes a "Demo mode" selector (Live/Fallback). When set to Fallback the server will return deterministic fallback values for Weather and Crypto. This is done by sending an `x-demo-fallback: 1` header.
- Use `agent_sim.py` to simulate an LLM chaining the tools. Example:

```bash
# run with live calls (default)
python3 agent_sim.py

# force fallback deterministic mode
python3 agent_sim.py --fallback
```

90s demo narrative
1) Read file: POST /mcp/file name=ai-safety-notes.txt max_chars=200 — deterministic excerpt
2) Fetch weather: POST /mcp/weather city=Chicago days=1 — live fetch with deterministic fallback
3) Live number: POST /mcp/crypto symbol=btc vs=usd — live from CoinGecko with fallback
4) Status: GET /mcp/health — uptime & config


