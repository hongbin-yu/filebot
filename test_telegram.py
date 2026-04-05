import json
import requests
import sys

# Read config
with open('/home/hongb/.openclaw/openclaw.json', 'r') as f:
    config = json.load(f)

# Get bot token (try yusecretarybot first)
accounts = config.get('channels', {}).get('telegram', {}).get('accounts', {})
bot_name = 'yusecretarybot'
if bot_name in accounts:
    token = accounts[bot_name].get('token')
    if token:
        print(f"Found token for {bot_name}")
    else:
        print(f"No token found for {bot_name}")
        sys.exit(1)
else:
    print(f"Account {bot_name} not found")
    sys.exit(1)

# Telegram API
chat_id = "8730338420"  # Your Telegram ID from metadata
message = "Test message from OpenClaw stock analysis system"
url = f"https://api.telegram.org/bot{token}/sendMessage"

payload = {
    'chat_id': chat_id,
    'text': message,
    'parse_mode': 'Markdown'
}

response = requests.post(url, json=payload)
if response.status_code == 200:
    print("Telegram message sent successfully!")
    print(response.json())
else:
    print(f"Failed to send message: {response.status_code}")
    print(response.text)