import pytest
from fastapi.testclient import TestClient
from app import app, APP_START
import time


client = TestClient(app)


def test_tool_catalog():
    r = client.get("/mcp/tools")
    assert r.status_code == 200
    data = r.json()
    assert any(t["name"] == "weather" for t in data["tools"])


def test_file_summarizer():
    r = client.post("/mcp/file", json={"name": "ai-safety-notes.txt", "max_chars": 50})
    assert r.status_code == 200
    j = r.json()
    assert j["name"] == "ai-safety-notes.txt"
    assert j["chars"] <= 50


def test_health():
    r = client.get("/mcp/health")
    assert r.status_code == 200
    j = r.json()
    assert j["name"].startswith("mcp-demo") or j["name"] == "mcp-demo"
    assert j["uptime_sec"] >= 0
