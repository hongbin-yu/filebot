#!/usr/bin/env python3
"""
Daily stock analysis report sent via Email and Telegram.
"""

import json
import requests
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Configuration
CONFIG_FILE = '/home/hongb/.openclaw/openclaw.json'
BOT_NAME = 'yusecretarybot'  # Bot to send from
CHAT_ID = '8730338420'       # Your Telegram ID

# Stock symbols to monitor
SYMBOLS = {
    'USO': 'US Oil Fund ETF',
    '^GSPC': 'S&P 500 Index'
}

def get_config():
    """Read OpenClaw configuration"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading config: {e}", file=sys.stderr)
        return {}

def get_bot_token(config):
    """Extract bot token from config"""
    accounts = config.get('channels', {}).get('telegram', {}).get('accounts', {})
    if BOT_NAME in accounts:
        token = accounts[BOT_NAME].get('token')
        if token:
            return token
    
    # Fallback to first available bot
    for account_name, account_data in accounts.items():
        if 'token' in account_data:
            print(f"Using fallback bot: {account_name}", file=sys.stderr)
            return account_data['token']
    
    raise ValueError(f"No bot token found for {BOT_NAME}")

def get_mail_config(config):
    """Extract mail configuration"""
    mail_config = config.get('mail', {})
    if not mail_config:
        raise ValueError("No mail configuration found in openclaw.json")
    
    required = ['smtp', 'port', 'user', 'password']
    for key in required:
        if key not in mail_config:
            raise ValueError(f"Missing mail configuration: {key}")
    
    return mail_config

def fetch_stock_price(symbol):
    """Fetch current and previous close price from Yahoo Finance"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {'interval': '1d', 'range': '5d'}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'chart' not in data or 'result' not in data['chart']:
            return None
        
        result = data['chart']['result'][0]
        quotes = result.get('indicators', {}).get('quote', [{}])[0]
        close_prices = quotes.get('close', [])
        
        # Filter out None values
        valid_prices = [p for p in close_prices if p is not None]
        
        if len(valid_prices) >= 2:
            current = valid_prices[-1]
            previous = valid_prices[-2]
            return {
                'current': current,
                'previous': previous,
                'change': current - previous,
                'change_pct': ((current - previous) / previous) * 100
            }
        elif len(valid_prices) == 1:
            return {
                'current': valid_prices[0],
                'previous': None,
                'change': None,
                'change_pct': None
            }
        else:
            return None
    except Exception as e:
        print(f"Error fetching {symbol}: {e}", file=sys.stderr)
        return None

def generate_report():
    """Generate analysis report"""
    report_lines = []
    report_lines.append(f"📈 Daily Stock Analysis")
    report_lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M EDT')}")
    report_lines.append("")
    
    data = {}
    for symbol, description in SYMBOLS.items():
        data[symbol] = fetch_stock_price(symbol)
    
    # USO Analysis
    uso_data = data.get('USO')
    if uso_data and uso_data['current']:
        current = uso_data['current']
        change_pct = uso_data.get('change_pct')
        
        report_lines.append("US Oil Fund (USO)")
        report_lines.append(f"Current: ${current:.2f}")
        
        if change_pct is not None:
            change_emoji = "📈" if change_pct >= 0 else "📉"
            report_lines.append(f"Daily: {change_emoji} {change_pct:+.2f}%")
        
        # Position info
        shares = 250
        position_value = shares * current
        report_lines.append(f"Your Position: {shares} shares (${position_value:,.2f})")
        
        # Simple trend analysis
        if change_pct is not None:
            if change_pct > 2:
                trend = "Strong upward momentum"
            elif change_pct > 0.5:
                trend = "Moderate gains"
            elif change_pct < -2:
                trend = "Significant decline"
            elif change_pct < -0.5:
                trend = "Moderate losses"
            else:
                trend = "Sideways movement"
            report_lines.append(f"Trend: {trend}")
        
        report_lines.append("")
    
    # S&P 500 Analysis
    spx_data = data.get('^GSPC')
    if spx_data and spx_data['current']:
        current = spx_data['current']
        change_pct = spx_data.get('change_pct')
        
        report_lines.append("S&P 500 Index")
        report_lines.append(f"Current: {current:.2f}")
        
        if change_pct is not None:
            change_emoji = "📈" if change_pct >= 0 else "📉"
            report_lines.append(f"Daily: {change_emoji} {change_pct:+.2f}%")
        
        report_lines.append("")
    
    # Recommendations
    report_lines.append("💡 Recommendations")
    
    if uso_data and uso_data.get('change_pct') is not None:
        change_pct = uso_data['change_pct']
        current = uso_data['current']
        
        if change_pct > 3:
            report_lines.append("1. USO showing strong gains. Consider holding or partial profit-taking if above your target.")
        elif change_pct > 1:
            report_lines.append("1. USO trending upward. Monitor resistance levels.")
        elif change_pct < -3:
            report_lines.append("1. USO under pressure. Review fundamentals before adding more.")
        elif change_pct < -1:
            report_lines.append("1. USO declining. Set stop-loss if holding.")
        else:
            report_lines.append("1. USO relatively stable. Maintain position with stop-loss at 5-10% below entry.")
    
    report_lines.append("2. Remember: You've held for 10 years, just reached break-even. Consider dollar-cost averaging if adding.")
    report_lines.append("3. Oil prices influenced by OPEC decisions, inventory reports, and global demand.")
    report_lines.append("")
    
    report_lines.append("📊 Next Steps")
    report_lines.append("1. Set price alerts for your target exit")
    report_lines.append("2. Review weekly inventory reports")
    report_lines.append("3. Consider diversification if heavily weighted in energy")
    report_lines.append("")
    
    report_lines.append("Disclaimer: This is automated analysis, not financial advice.")
    report_lines.append("Consult a financial advisor for personalized guidance.")
    
    return "\n".join(report_lines)

def generate_email_report():
    """Generate email-friendly report (plain text)"""
    report_lines = []
    report_lines.append("DAILY STOCK ANALYSIS")
    report_lines.append("=" * 50)
    report_lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M EDT')}")
    report_lines.append("")
    
    data = {}
    for symbol, description in SYMBOLS.items():
        data[symbol] = fetch_stock_price(symbol)
    
    # USO Analysis
    uso_data = data.get('USO')
    if uso_data and uso_data['current']:
        current = uso_data['current']
        change_pct = uso_data.get('change_pct')
        
        report_lines.append("US OIL FUND (USO)")
        report_lines.append(f"Current Price: ${current:.2f}")
        
        if change_pct is not None:
            report_lines.append(f"Daily Change: {change_pct:+.2f}%")
        
        shares = 250
        position_value = shares * current
        report_lines.append(f"Your Position: {shares} shares")
        report_lines.append(f"Position Value: ${position_value:,.2f}")
        report_lines.append("")
    
    # S&P 500 Analysis
    spx_data = data.get('^GSPC')
    if spx_data and spx_data['current']:
        current = spx_data['current']
        change_pct = spx_data.get('change_pct')
        
        report_lines.append("S&P 500 INDEX")
        report_lines.append(f"Current: {current:.2f}")
        
        if change_pct is not None:
            report_lines.append(f"Daily Change: {change_pct:+.2f}%")
        
        report_lines.append("")
    
    # Recommendations
    report_lines.append("RECOMMENDATIONS")
    report_lines.append("-" * 50)
    
    if uso_data and uso_data.get('change_pct') is not None:
        change_pct = uso_data['change_pct']
        
        if change_pct > 3:
            report_lines.append("• USO showing strong gains. Consider holding or partial profit-taking.")
        elif change_pct > 1:
            report_lines.append("• USO trending upward. Monitor resistance levels.")
        elif change_pct < -3:
            report_lines.append("• USO under pressure. Review fundamentals before adding.")
        elif change_pct < -1:
            report_lines.append("• USO declining. Set stop-loss if holding.")
        else:
            report_lines.append("• USO relatively stable. Maintain position with stop-loss.")
    
    report_lines.append("• You've held for 10 years, just reached break-even.")
    report_lines.append("• Consider dollar-cost averaging if adding to position.")
    report_lines.append("• Oil prices influenced by OPEC, inventory, and global demand.")
    report_lines.append("")
    
    report_lines.append("NEXT STEPS")
    report_lines.append("-" * 50)
    report_lines.append("1. Set price alerts for target exit levels")
    report_lines.append("2. Review weekly EIA inventory reports")
    report_lines.append("3. Consider diversification if heavily weighted in energy")
    report_lines.append("")
    
    report_lines.append("=" * 50)
    report_lines.append("DISCLAIMER: Automated analysis, not financial advice.")
    report_lines.append("Consult a financial advisor before making investment decisions.")
    
    return "\n".join(report_lines)

def send_email(mail_config, subject, body):
    """Send email via SMTP"""
    try:
        smtp_server = mail_config['smtp']
        smtp_port = int(mail_config['port'])
        user = mail_config['user']
        password = mail_config['password']
        
        receiver = user  # Send to self
        
        msg = MIMEMultipart()
        msg['From'] = user
        msg['To'] = receiver
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
        server.quit()
        
        print(f"Email sent successfully to {receiver}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}", file=sys.stderr)
        return False

def send_telegram_message(token, text):
    """Send message via Telegram Bot API"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending Telegram message: {e}", file=sys.stderr)
        return False

def main():
    print(f"Starting daily stock analysis at {datetime.now()}")
    
    # Read configuration
    config = get_config()
    if not config:
        print("Failed to read configuration", file=sys.stderr)
        sys.exit(1)
    
    # Generate reports
    telegram_report = generate_report()  # For Telegram (with emojis)
    email_report = generate_email_report()  # For Email (plain text)
    
    # Print to console for logging
    print("\n" + email_report + "\n")
    
    # Try sending email first
    email_sent = False
    try:
        mail_config = get_mail_config(config)
        subject = f"Daily Stock Analysis - {datetime.now().strftime('%Y-%m-%d')}"
        email_sent = send_email(mail_config, subject, email_report)
    except Exception as e:
        print(f"Email configuration error: {e}", file=sys.stderr)
    
    # Try sending Telegram as backup (or additional)
    telegram_sent = False
    try:
        token = get_bot_token(config)
        telegram_sent = send_telegram_message(token, telegram_report)
    except Exception as e:
        print(f"Telegram configuration error: {e}", file=sys.stderr)
    
    # If both failed, save to file
    if not email_sent and not telegram_sent:
        print("Both email and Telegram failed", file=sys.stderr)
        filename = f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(filename, 'w') as f:
            f.write(email_report)
        print(f"Report saved to {filename}")
        sys.exit(1)
    
    # Report status
    if email_sent and telegram_sent:
        print("Report sent via both Email and Telegram")
    elif email_sent:
        print("Report sent via Email only")
    elif telegram_sent:
        print("Report sent via Telegram only (Email failed)")
    
    sys.exit(0)

if __name__ == '__main__':
    main()