"""Simple orchestrator that calls the MCP demo server tools in sequence:
1) fetch tool catalog
2) fetch file summary
3) fetch weather
4) fetch crypto
Prints combined JSON to stdout.
"""
import requests
import json
import sys

BASE = "http://127.0.0.1:8000"

def call(path, json_in, demo_fallback=False):
    headers = {}
    if demo_fallback:
        headers['x-demo-fallback'] = '1'
    r = requests.post(BASE + path, json=json_in, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()

def main():
    demo = '--fallback' in sys.argv
    # catalog
    try:
        cat = requests.get(BASE + '/mcp/tools').json()
    except Exception as e:
        print('Could not fetch catalog:', e)
        return

    file = call('/mcp/file', {'name':'ai-safety-notes.txt','max_chars':200}, demo)
    weather = call('/mcp/weather', {'city':'Chicago','days':1}, demo)
    crypto = call('/mcp/crypto', {'symbol':'btc','vs':'usd'}, demo)

    out = {'summary': file, 'weather': weather, 'crypto': crypto}
    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
