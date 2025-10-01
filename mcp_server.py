#!/usr/bin/env python
"""
MCP Server for Claude Desktop
Implements the Model Context Protocol for stdio communication
"""
import sys
import json
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import time
import httpx
import csv
from datetime import datetime, timezone, date

# Initialize app start time
APP_START = time.time()

class MCPServer:
    def __init__(self):
        self.initialized = False
        self.root = Path(__file__).parent
        self.resources = self.root / "resources" / "docs"
        
    async def handle_initialize(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle initialization request from Claude"""
        self.initialized = True
        sys.stderr.write("Server initialized\n")
        sys.stderr.flush()
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2025-06-18",  # Match Claude's version
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "mcp-demo",
                    "version": "1.0.0"
                }
            },
            "id": request_id
        }

    async def handle_tools_list(self, request_id: Any) -> Dict[str, Any]:
        """Return list of available tools"""
        sys.stderr.write("Listing tools\n")
        sys.stderr.flush()
        
        tools = [
            {
                "name": "weather",
                "description": "Get weather forecast for a city",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "City name (e.g., Chicago, New York, London)"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days to forecast (1-7)",
                            "minimum": 1,
                            "maximum": 7,
                            "default": 1
                        }
                    },
                    "required": ["city"]
                }
            },
            {
                "name": "invoice_followup",
                "description": "Flag overdue invoices and generate follow-up emails from a CSV",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "csv_name": {
                            "type": "string",
                            "description": "CSV filename in resources/docs",
                            "default": "Fake_Invoice_Data.csv"
                        },
                        "thresholds": {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 1},
                            "description": "Overdue day thresholds",
                            "default": [7, 14, 21]
                        },
                        "today": {
                            "type": "string",
                            "description": "Override current date as YYYY-MM-DD"
                        }
                    }
                }
            },
            {
                "name": "crypto",
                "description": "Get current cryptocurrency price",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Cryptocurrency symbol (btc, eth, sol)",
                            "enum": ["btc", "eth", "sol"]
                        },
                        "vs": {
                            "type": "string",
                            "description": "Currency to compare against",
                            "default": "usd"
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "file",
                "description": "Read and summarize a file from resources",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "File name to read"
                        },
                        "max_chars": {
                            "type": "integer",
                            "description": "Maximum characters to return",
                            "minimum": 1,
                            "default": 200
                        }
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "health",
                "description": "Get server health status",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": tools
            },
            "id": request_id
        }

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle tool execution requests"""
        sys.stderr.write(f"Calling tool: {tool_name} with args: {arguments}\n")
        sys.stderr.flush()
        
        if not self.initialized:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32002,
                    "message": "Server not initialized"
                },
                "id": request_id
            }

        try:
            if tool_name == "weather":
                result = await self.weather_tool(arguments)
            elif tool_name == "crypto":
                result = await self.crypto_tool(arguments)
            elif tool_name == "file":
                result = self.file_tool(arguments)
            elif tool_name == "health":
                result = self.health_tool()
            elif tool_name == "invoice_followup":
                result = self.invoice_followup_tool(arguments)
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Tool '{tool_name}' not found"
                    },
                    "id": request_id
                }

            return {
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                },
                "id": request_id
            }
            
        except Exception as e:
            sys.stderr.write(f"Error in tool {tool_name}: {str(e)}\n")
            sys.stderr.flush()
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": str(e)
                },
                "id": request_id
            }

    async def weather_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get weather forecast (live via open-meteo with graceful fallback)."""
        city = params.get("city", "").strip()
        days = int(params.get("days", 1))
        if days < 1:
            days = 1
        if days > 7:
            days = 7

        # very small local map for demo parity with HTTP server
        local_geo = {
            "chicago": {"lat": 41.8781, "lon": -87.6298},
            "new york": {"lat": 40.7128, "lon": -74.0060},
            "london": {"lat": 51.5074, "lon": -0.1278},
        }

        location = city or "unknown"
        lat = lon = None
        if city:
            geo = local_geo.get(city.lower())
            if geo:
                lat, lon = geo["lat"], geo["lon"]

        daily = []
        source = "fallback"

        if lat is not None and lon is not None:
            url = (
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=UTC&forecast_days={days}"
            )
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
                        daily.append({
                            "date": dates[i],
                            "t_max": float(tmaxs[i]),
                            "t_min": float(tmins[i]),
                            "precip_mm": float(precs[i]),
                        })
                    source = "open-meteo"
            except Exception:
                # fall through to deterministic data below
                pass

        if not daily:
            for i in range(days):
                date_s = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 86400 * i))
                daily.append({
                    "date": date_s,
                    "t_max": 20.0 + i,
                    "t_min": 10.0 + i,
                    "precip_mm": 0.0,
                })

        return {"location": location, "daily": daily, "source": source}

    async def crypto_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get crypto price (live via CoinGecko with graceful fallback)."""
        symbol = str(params.get("symbol", "btc")).lower()
        vs = str(params.get("vs", "usd")).lower()

        symbol_map = {"btc": "bitcoin", "eth": "ethereum", "sol": "solana"}
        coin_id = symbol_map.get(symbol)

        price: Optional[float] = None
        source = "fallback"

        if coin_id:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={vs}"
            try:
                async with httpx.AsyncClient(timeout=5.0) as c:
                    r = await c.get(url)
                    r.raise_for_status()
                    data = r.json()
                    price = float(data[coin_id][vs])
                    source = "coingecko"
            except Exception:
                price = None

        if price is None:
            fixed = {"bitcoin": 50000.0, "ethereum": 3500.0, "solana": 150.0}
            price = fixed.get(coin_id or "", 1.0)

        return {"symbol": symbol, "vs": vs, "price": price, "source": source}

    def file_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read and summarize a file"""
        name = params.get("name", "")
        max_chars = params.get("max_chars", 200)
        
        file_path = self.resources / name
        
        if not file_path.exists():
            # If file doesn't exist, return a demo response
            return {
                "name": name,
                "chars": 50,
                "text": "Demo content: This is a sample file summary."
            }
        
        try:
            text = file_path.read_text(encoding="utf-8")
            # Normalize whitespace
            normalized = " ".join(text.split())
            clipped = normalized[:max_chars]
            
            return {
                "name": name,
                "chars": len(clipped),
                "text": clipped
            }
        except Exception as e:
            return {
                "name": name,
                "chars": 0,
                "text": f"Error reading file: {str(e)}"
            }

    def health_tool(self) -> Dict[str, Any]:
        """Get server health status"""
        uptime = time.time() - APP_START
        return {
            "name": "mcp-demo",
            "uptime_sec": round(uptime, 3),
            "status": "healthy",
            "protocol": "MCP"
        }

    # -----------------------------
    # Invoice follow-up tool (stdio)
    # -----------------------------
    def _parse_date(self, s: str) -> date:
        formats = ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(s.strip(), fmt).date()
            except Exception:
                continue
        raise ValueError(f"unrecognized date format: {s}")

    def invoice_followup_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read CSV and generate overdue follow-up emails.

        CSV required columns: invoice_number, broker, due_date, amount
        Optional columns are ignored.
        """
        csv_name = params.get("csv_name", "Fake_Invoice_Data.csv")
        thresholds_in = params.get("thresholds", [7, 14, 21])
        today_str = params.get("today")

        # today reference
        if today_str:
            try:
                today = self._parse_date(today_str)
            except Exception as e:
                raise ValueError(f"invalid today: {e}")
        else:
            today = datetime.now(timezone.utc).date()

        # normalize thresholds
        try:
            thresholds = sorted({int(t) for t in thresholds_in if int(t) > 0})
        except Exception:
            raise ValueError("thresholds must be positive integers")
        if not thresholds:
            raise ValueError("thresholds must contain at least one positive integer")

        # locate CSV
        csv_path = self.resources / csv_name
        if not csv_path.exists():
            raise FileNotFoundError(f"csv not found: {csv_name}")

        processed = 0
        emails = []

        with csv_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            required = {"invoice_number", "broker", "due_date", "amount"}
            fieldnames = set((reader.fieldnames or []))
            if not required.issubset({c.strip() for c in fieldnames}):
                missing = required - {c.strip() for c in fieldnames}
                raise ValueError(f"csv missing columns: {', '.join(sorted(missing))}")

            for row in reader:
                processed += 1
                try:
                    inv = str(row.get("invoice_number", "")).strip()
                    broker = str(row.get("broker", "")).strip()
                    due = self._parse_date(str(row.get("due_date", "")).strip())
                    amount = float(str(row.get("amount", "0")).replace(",", "").strip())
                except Exception:
                    # skip malformed rows
                    continue

                days_overdue = (today - due).days
                if days_overdue <= 0:
                    continue

                # choose highest tier met
                tier = 0
                for t in thresholds:
                    if days_overdue >= t:
                        tier = t
                    else:
                        break
                if tier == 0:
                    continue

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

                emails.append({
                    "invoice_number": inv,
                    "broker": broker,
                    "due_date": due.isoformat(),
                    "amount": amount,
                    "days_overdue": days_overdue,
                    "tier": tier,
                    "subject": subject,
                    "body": body,
                })

        return {
            "processed": processed,
            "overdue": len(emails),
            "emails": emails,
            "source": csv_path.name,
        }

    async def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Route messages to appropriate handlers"""
        
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params", {})
        
        sys.stderr.write(f"Handling method: {method}\n")
        sys.stderr.flush()
        
        # Handle different MCP methods
        if method == "initialize":
            return await self.handle_initialize(params, request_id)
        elif method == "tools/list":
            return await self.handle_tools_list(request_id)
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            return await self.handle_tool_call(tool_name, arguments, request_id)
        elif method == "notifications/initialized":
            # This is a notification, no response needed
            sys.stderr.write("Received initialized notification\n")
            sys.stderr.flush()
            return None
        elif method == "ping":
            # Respond to ping to keep connection alive
            return {
                "jsonrpc": "2.0",
                "result": {},
                "id": request_id
            }
        else:
            sys.stderr.write(f"Unknown method: {method}\n")
            sys.stderr.flush()
            if request_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found"
                    },
                    "id": request_id
                }
            return None

async def main():
    """Main entry point for the MCP server"""
    server = MCPServer()
    
    # Log to stderr so it doesn't interfere with stdio protocol
    sys.stderr.write("MCP Server starting...\n")
    sys.stderr.flush()
    
    # Main message loop
    while True:
        try:
            # Read line from stdin
            line = sys.stdin.readline()
            if not line:
                sys.stderr.write("No input received, waiting...\n")
                sys.stderr.flush()
                await asyncio.sleep(0.1)
                continue
            
            line = line.strip()
            if not line:
                continue
                
            # Parse JSON-RPC message
            try:
                message = json.loads(line)
            except json.JSONDecodeError as e:
                sys.stderr.write(f"Parse error: {str(e)} for line: {line}\n")
                sys.stderr.flush()
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    },
                    "id": None
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
                continue
            
            # Handle the message
            response = await server.handle_message(message)
            
            # Send response if there is one (some messages are notifications)
            if response:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                
        except KeyboardInterrupt:
            sys.stderr.write("Server shutting down...\n")
            sys.stderr.flush()
            break
        except EOFError:
            sys.stderr.write("EOF received, continuing...\n")
            sys.stderr.flush()
            await asyncio.sleep(0.1)
        except Exception as e:
            sys.stderr.write(f"Unexpected error: {str(e)}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.stderr.write("Server stopped by user\n")
        sys.stderr.flush()