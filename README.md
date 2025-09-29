# MCP_Demo

Tiny demo server to prove the MCP concept (tools+JSON+STDIO/http). This repository contains a minimal FastAPI app that exposes three "data lanes" (weather, crypto, file summarizer) plus a health endpoint.

Run (recommended in a venv)

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


