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
        """Get weather forecast (using fallback data for demo)"""
        city = params.get("city", "unknown")
        days = params.get("days", 1)
        
        # For demo purposes, return deterministic fallback data
        # In production, this would call the actual weather API
        daily = []
        for i in range(days):
            day_offset = 86400 * i
            date = time.strftime("%Y-%m-%d", time.gmtime(time.time() + day_offset))
            daily.append({
                "date": date,
                "t_max": 20.0 + i,
                "t_min": 10.0 + i,
                "precip_mm": 0.0
            })
        
        return {
            "location": city,
            "daily": daily,
            "source": "fallback"
        }

    async def crypto_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get crypto prices (using fallback data for demo)"""
        symbol = params.get("symbol", "btc").lower()
        vs = params.get("vs", "usd").lower()
        
        # Fallback prices for demo
        prices = {
            "btc": 50000.0,
            "eth": 3500.0,
            "sol": 150.0
        }
        
        return {
            "symbol": symbol,
            "vs": vs,
            "price": prices.get(symbol, 1.0),
            "source": "fallback"
        }

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