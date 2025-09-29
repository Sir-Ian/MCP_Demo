from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Annotated
import httpx
import asyncio
import time
import json
from pathlib import Path
import csv
from datetime import datetime, timezone, date

APP_START = time.time()

app = FastAPI(title="MCP Demo Server", version="0.1")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path(__file__).parent
RESOURCES = ROOT / "resources" / "docs"
RESOURCES.mkdir(parents=True, exist_ok=True)

# Serve a tiny demo frontend from /static
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
STATIC_DIR = ROOT / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")




class WeatherIn(BaseModel):
    city: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    days: Annotated[int, Field(ge=1, le=7)]


class WeatherDay(BaseModel):
    date: str
    t_max: float
    t_min: float
    precip_mm: float


class WeatherOut(BaseModel):
    location: str
    daily: List[WeatherDay]
    source: str


class CryptoIn(BaseModel):
    symbol: str
    vs: str = "usd"


class CryptoOut(BaseModel):
    symbol: str
    vs: str
    price: float
    source: str


class FileIn(BaseModel):
    name: str
    max_chars: Annotated[int, Field(gt=0)]


class FileOut(BaseModel):
    name: str
    chars: int
    text: str


class HealthOut(BaseModel):
    name: str
    uptime_sec: float
    http_timeout_sec: float
    versions: Dict[str, str]


class InvoiceFollowupIn(BaseModel):
    csv_name: str = "Fake_Invoice_Data.csv"
    thresholds: List[int] = [7, 14, 21]
    today: Optional[str] = None  # YYYY-MM-DD; if None, use current UTC date


class FollowupEmail(BaseModel):
    invoice_number: str
    broker: str
    due_date: str
    amount: float
    days_overdue: int
    tier: int
    subject: str
    body: str


class InvoiceFollowupOut(BaseModel):
    processed: int
    overdue: int
    emails: List[FollowupEmail]
    source: str


@app.get("/mcp/tools")
def tool_catalog():
    """Return a small tool catalog describing endpoints and contracts."""
    return {
        "tools": [
            {"name": "weather", "path": "/mcp/weather", "in": "WeatherIn", "out": "WeatherOut"},
            {"name": "crypto", "path": "/mcp/crypto", "in": "CryptoIn", "out": "CryptoOut"},
            {"name": "file", "path": "/mcp/file", "in": "FileIn", "out": "FileOut"},
            {"name": "health", "path": "/mcp/health", "in": "none", "out": "HealthOut"},
            {"name": "invoice_followup", "path": "/mcp/invoice_followup", "in": "InvoiceFollowupIn", "out": "InvoiceFollowupOut"},
        ]
    }

# Also expose /tools at root for Claude compatibility
@app.get("/tools")
def tool_catalog_root():
    return tool_catalog()


async def geocode_city(city: str) -> Optional[Dict[str, float]]:
    # very small local map for demo
    local = {
        "chicago": {"lat": 41.8781, "lon": -87.6298},
        "new york": {"lat": 40.7128, "lon": -74.0060},
        "london": {"lat": 51.5074, "lon": -0.1278},
    }
    key = city.strip().lower()
    return local.get(key)


@app.post("/mcp/weather", response_model=WeatherOut)
async def weather(inp: WeatherIn, request: Request):
    # Resolve location
    if inp.city:
        geo = await geocode_city(inp.city)
        if not geo:
            raise HTTPException(status_code=400, detail="unknown city")
        lat, lon = geo["lat"], geo["lon"]
        location = inp.city
    elif inp.lat is not None and inp.lon is not None:
        lat, lon = inp.lat, inp.lon
        location = f"{lat},{lon}"
    else:
        raise HTTPException(status_code=400, detail="provide city or lat/lon")

    # Call open-meteo (skip network if demo fallback header present)
    days = inp.days
    demo_fallback = request.headers.get("x-demo-fallback", "0").lower() in ("1", "true", "yes")
    source = "open-meteo"
    daily = []
    if demo_fallback:
        source = "fallback"
        for i in range(days):
            day = WeatherDay(date=time.strftime("%Y-%m-%d", time.gmtime(APP_START + 86400 * i)), t_max=20.0 + i, t_min=10.0 + i, precip_mm=0.0)
            daily.append(day)
    else:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=UTC&forecast_days={days}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                r = await c.get(url)
                r.raise_for_status()
                data = r.json()
                dates = data["daily"]["time"]
                tmaxs = data["daily"]["temperature_2m_max"]
                tmins = data["daily"]["temperature_2m_min"]
                precs = data["daily"].get("precipitation_sum", [0.0] * len(dates))
                for i in range(len(dates)):
                    daily.append(WeatherDay(date=dates[i], t_max=float(tmaxs[i]), t_min=float(tmins[i]), precip_mm=float(precs[i])))
        except Exception:
            # fallback: deterministic local mini-forecast
            source = "fallback"
            for i in range(days):
                day = WeatherDay(date=time.strftime("%Y-%m-%d", time.gmtime(APP_START + 86400 * i)), t_max=20.0 + i, t_min=10.0 + i, precip_mm=0.0)
                daily.append(day)

    return WeatherOut(location=location, daily=daily, source=source)


SYMBOL_MAP = {"btc": "bitcoin", "eth": "ethereum", "sol": "solana"}


@app.post("/mcp/crypto", response_model=CryptoOut)
async def crypto(inp: CryptoIn, request: Request):
    sym = inp.symbol.lower()
    if sym not in SYMBOL_MAP:
        raise HTTPException(status_code=400, detail="unsupported symbol")
    coin_id = SYMBOL_MAP[sym]
    vs = inp.vs.lower()
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={vs}"
    demo_fallback = request.headers.get("x-demo-fallback", "0").lower() in ("1", "true", "yes")
    source = "coingecko"
    price = None
    if demo_fallback:
        source = "fallback"
        fixed = {"bitcoin": 50000.0, "ethereum": 3500.0, "solana": 150.0}
        price = fixed.get(coin_id, 1.0)
    else:
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                r = await c.get(url)
                r.raise_for_status()
                data = r.json()
                price = float(data[coin_id][vs])
        except Exception:
            source = "fallback"
            fixed = {"bitcoin": 50000.0, "ethereum": 3500.0, "solana": 150.0}
            price = fixed.get(coin_id, 1.0)

    return CryptoOut(symbol=sym, vs=vs, price=price, source=source)


@app.post("/mcp/file", response_model=FileOut)
def file_summarizer(inp: FileIn):
    path = RESOURCES / inp.name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    text = path.read_text(encoding="utf-8")
    # normalize whitespace
    norm = " ".join(text.split())
    clipped = norm[: inp.max_chars]
    return FileOut(name=inp.name, chars=len(clipped), text=clipped)



# Also expose /health at root for Claude compatibility
@app.get("/mcp/health", response_model=HealthOut)
def health():
    uptime = time.time() - APP_START
    return HealthOut(name="mcp-demo", uptime_sec=round(uptime, 3), http_timeout_sec=5.0, versions={"protocol": "MCP", "python": "3.11+"})

@app.get("/health", response_model=HealthOut)
def health_root():
    return health()


@app.get("/")
def root():
    # redirect to the shipped frontend
    return RedirectResponse(url="/static/index.html")


def _parse_date(d: str) -> date:
    fmts = ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"]
    for f in fmts:
        try:
            return datetime.strptime(d.strip(), f).date()
        except Exception:
            continue
    raise HTTPException(status_code=400, detail=f"unrecognized date format: {d}")


@app.post("/mcp/invoice_followup", response_model=InvoiceFollowupOut)
def invoice_followup(inp: InvoiceFollowupIn):
    # Establish 'today' reference
    if inp.today:
        try:
            today = _parse_date(inp.today)
        except HTTPException:
            raise
    else:
        today = datetime.now(timezone.utc).date()

    # Normalize and sort thresholds ascending
    thresholds = sorted({int(t) for t in inp.thresholds if int(t) > 0})
    if not thresholds:
        raise HTTPException(status_code=400, detail="thresholds must contain positive integers")

    # Locate CSV file
    csv_path = RESOURCES / inp.csv_name
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"csv not found: {inp.csv_name}")

    emails: List[FollowupEmail] = []
    processed = 0

    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required_cols = {"invoice_number", "broker", "due_date", "amount"}
        missing = required_cols - set(c.strip() for c in reader.fieldnames or [])
        if missing:
            raise HTTPException(status_code=400, detail=f"csv missing columns: {', '.join(sorted(missing))}")

        for row in reader:
            processed += 1
            try:
                inv = str(row.get("invoice_number", "")).strip()
                broker = str(row.get("broker", "")).strip()
                due = _parse_date(str(row.get("due_date", "")).strip())
                amount = float(str(row.get("amount", "0")).replace(",", "").strip())
            except Exception:
                # Skip malformed rows
                continue

            days_overdue = (today - due).days
            if days_overdue <= 0:
                continue

            # Determine highest threshold tier met
            tier = 0
            for t in thresholds:
                if days_overdue >= t:
                    tier = t
                else:
                    break
            if tier == 0:
                continue

            # Build email template by tier
            subject = f"Invoice {inv} is {days_overdue} days overdue"
            greeting = f"Hi {broker},"
            amount_str = f"${amount:,.2f}"

            if tier >= 21:
                body = (
                    f"{greeting}\n\n"
                    f"This is a third reminder that invoice {inv} for {amount_str} was due on {due.isoformat()} "
                    f"and is now {days_overdue} days overdue. Please arrange payment immediately or reply with an "
                    f"update so we can reconcile our records.\n\n"
                    f"If payment has been made, please share the remittance details.\n\n"
                    f"Thank you,\nAccounts Receivable"
                )
            elif tier >= 14:
                body = (
                    f"{greeting}\n\n"
                    f"Friendly follow-up on invoice {inv} for {amount_str} due {due.isoformat()}. "
                    f"Our records show it is {days_overdue} days overdue. Could you share a quick status or "
                    f"expected payment date?\n\n"
                    f"Thanks so much,\nAccounts Receivable"
                )
            else:  # >=7
                body = (
                    f"{greeting}\n\n"
                    f"Quick reminder: invoice {inv} for {amount_str} was due {due.isoformat()} and appears to be "
                    f"{days_overdue} days overdue. Please let us know if you need the invoice resent or have any "
                    f"questions.\n\n"
                    f"Best,\nAccounts Receivable"
                )

            emails.append(
                FollowupEmail(
                    invoice_number=inv,
                    broker=broker,
                    due_date=due.isoformat(),
                    amount=amount,
                    days_overdue=days_overdue,
                    tier=tier,
                    subject=subject,
                    body=body,
                )
            )

    return InvoiceFollowupOut(
        processed=processed,
        overdue=len(emails),
        emails=emails,
        source=str(csv_path.name),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
