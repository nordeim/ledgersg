import requests

# Test 1: Simple GET request
print("=== TEST 1: GET without CORS ===")
try:
    resp = requests.get('http://localhost:8000/api/v1/auth/me/')
    print(f"Status: {resp.status_code}")
    print(f"Headers: {dict(resp.headers)}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== TEST 2: OPTIONS preflight ===")
try:
    resp = requests.options(
        'http://localhost:8000/api/v1/auth/me/',
        headers={
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Content-Type, Authorization'
        }
    )
    print(f"Status: {resp.status_code}")
    print(f"CORS Headers:")
    for key, val in resp.headers.items():
        if 'Access-Control' in key or 'Origin' in key:
            print(f"  {key}: {val}")
except Exception as e:
    print(f"Error: {e}")
