import requests
import json

url = "https://query1.finance.yahoo.com/v8/finance/chart/USO"
params = {"interval": "1d", "range": "1mo"}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

response = requests.get(url, params=params, headers=headers)
print(f"Status: {response.status_code}")
data = response.json()
print(json.dumps(data, indent=2)[:2000])