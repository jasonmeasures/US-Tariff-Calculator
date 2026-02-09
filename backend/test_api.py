"""Test API endpoints"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Test calculate endpoint
print("=== Testing /api/calculate ===")
payload = {
    "hts_code": "8708.80.65.90",
    "country": "JP",
    "entry_date": "2025-03-15",
    "value": 10000.0,
    "aluminum_percent": 100.0,
    "mode": "ocean"
}

response = requests.post(f"{BASE_URL}/api/calculate", json=payload)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    print(f"\nHTS Code: {result['hts_code']}")
    print(f"Country: {result['country']}")
    print(f"Entered Value: ${result['entered_value']:,.2f}")
    print(f"\nDuty Rate: {result['total_duty_rate']}%")
    print(f"Total Duty: ${result['total_duty']:,.2f}")
    print(f"\nBreakdown:")
    for item in result['breakdown']:
        if 'material_basis' in item and item['material_basis']:
            print(f"  • {item['name']}: {item['rate']}% × {item['material_percent']}% {item['material_basis']} = ${item['amount']:,.2f}")
        else:
            print(f"  • {item['name']}: ${item['amount']:,.2f}")
    print(f"\nLanded Cost: ${result['landed_cost']:,.2f}")
    print(f"Confidence: {result['confidence']}%")
else:
    print(f"Error: {response.text}")
