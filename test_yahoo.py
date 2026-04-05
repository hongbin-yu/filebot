import requests
import json

url = "https://query1.finance.yahoo.com/v8/finance/chart/USO"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
response = requests.get(url, headers=headers)
if response.status_code == 200:
    data = response.json()
    print(json.dumps(data, indent=2)[:1000])
else:
    print(f"Error: {response.status_code}")
    print(response.text[:500])