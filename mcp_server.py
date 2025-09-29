import sys
import json
import asyncio
from typing import Dict, Any
from app import (
    WeatherIn, 
    CryptoIn, 
    FileIn,
    weather,
    crypto,
    file_summarizer,
    health
)

class MCPServer:
    def __init__(self):
        self.tools = {
            "weather": self.weather_tool,
            "crypto": self.crypto_tool,
            "file": self.file_tool,
            "health": self.health_tool
        }
        self.initialized = False

    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self.initialized = True
        return {
            "jsonrpc": "2.0",
            "result": {
                "name": "mcp-demo",
                "version": "1.0.0",
                "vendor": "demo"
            },
            "id": params.get("id")
        }

    async def handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tools = [
            {
                "name": "weather",
                "description": "Get weather forecast",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                        "lat": {"type": "number"},
                        "lon": {"type": "number"},
                        "days": {"type": "integer", "minimum": 1, "maximum": 7}
                    }
                }
            },
            {
                "name": "crypto",
                "description": "Get cryptocurrency prices",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "vs": {"type": "string", "default": "usd"}
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "file",
                "description": "Read and summarize files",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "max_chars": {"type": "integer", "minimum": 1}
                    },
                    "required": ["name", "max_chars"]
                }
            }
        ]
        return {
            "jsonrpc": "2.0",
            "result": {"tools": tools},
            "id": params.get("id")
        }

    async def weather_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        weather_input = WeatherIn(**params)
        result = await weather(weather_input, None)
        return result.dict()

    async def crypto_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        crypto_input = CryptoIn(**params)
        result = await crypto(crypto_input, None)
        return result.dict()

    async def file_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        file_input = FileIn(**params)
        result = file_summarizer(file_input)
        return result.dict()

    async def health_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        result = health()
        return result.dict()

    async def handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.initialized:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32002, "message": "Server not initialized"},
                "id": params.get("id")
            }

        tool_name = params.get("name")
        tool_params = params.get("parameters", {})

        if tool_name not in self.tools:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"},
                "id": params.get("id")
            }

        try:
            result = await self.tools[tool_name](tool_params)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": params.get("id")
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": str(e)},
                "id": params.get("id")
            }

    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        method = message.get("method")
        params = message.get("params", {})

        handlers = {
            "initialize": self.handle_initialize,
            "list_tools": self.handle_list_tools,
            "call_tool": self.handle_call_tool
        }

        if method not in handlers:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method '{method}' not found"},
                "id": message.get("id")
            }

        return await handlers[method](params)

async def main():
    server = MCPServer()
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            message = json.loads(line)
            response = await server.handle_message(message)
            
            # Write response to stdout
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

        except json.JSONDecodeError:
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": str(e)},
                "id": None
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())