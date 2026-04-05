#!/usr/bin/env python3
"""
Daily stock analysis for USO:US (US Oil Fund)
Sends email report with key indicators and recommendations.
"""

import requests
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import time
import sys

# Configuration
EMAIL_SENDER = "hongbin.yu413@gmail.com"
EMAIL_PASSWORD = "Nina201@"  # Consider using app-specific password
EMAIL_RECEIVER = "hongbin.yu413@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Stock symbols
SYMBOLS = {
    "USO": "US Oil Fund ETF",
    "^GSPC": "S&P 500 Index",
    "CL=F": "WTI Crude Oil Futures"
}

def fetch_stock_data(symbol, interval="1d", range="1mo"):
    """Fetch historical data from Yahoo Finance API"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "interval": interval,
        "range": range
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "chart" not in data or "result" not in data["chart"]:
            return None
            
        result = data["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        quotes = result.get("indicators", {}).get("quote", [{}])[0]
        close_prices = quotes.get("close", [])
        
        # Filter out None values
        valid_data = [(ts, price) for ts, price in zip(timestamps, close_prices) 
                     if price is not None]
        
        if not valid_data:
            return None
            
        timestamps, prices = zip(*valid_data)
        return {
            "timestamps": timestamps,
            "prices": prices,
            "current": prices[-1] if prices else None,
            "previous": prices[-2] if len(prices) >= 2 else None
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}", file=sys.stderr)
        return None

def calculate_indicators(prices, period=14):
    """Calculate simple technical indicators"""
    if len(prices) < period:
        return {}
    
    # Simple Moving Average (20-period)
    sma20 = sum(prices[-20:]) / min(20, len(prices)) if len(prices) >= 20 else None
    
    # Price change
    if len(prices) >= 2:
        daily_change = ((prices[-1] - prices[-2]) / prices[-2]) * 100
    else:
        daily_change = None
    
    # Simple RSI calculation
    if len(prices) >= period + 1:
        gains = []
        losses = []
        for i in range(1, period + 1):
            change = prices[-i] - prices[-i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
    else:
        rsi = None
    
    return {
        "sma20": sma20,
        "daily_change_pct": daily_change,
        "rsi": rsi
    }

def generate_analysis_report(data):
    """Generate analysis report text"""
    report = []
    report.append("=" * 60)
    report.append(f"DAILY STOCK ANALYSIS - {datetime.now().strftime('%Y-%m-%d %H:%M EDT')}")
    report.append("=" * 60)
    report.append("")
    
    for symbol, description in SYMBOLS.items():
        symbol_data = data.get(symbol)
        if not symbol_data:
            report.append(f"{symbol} ({description}): DATA UNAVAILABLE")
            continue
        
        current = symbol_data.get("current")
        previous = symbol_data.get("previous")
        indicators = symbol_data.get("indicators", {})
        
        report.append(f"{symbol} ({description}):")
        if current is not None:
            report.append(f"  Current Price: ${current:.2f}")
        
        if previous is not None and current is not None:
            change = current - previous
            change_pct = (change / previous) * 100
            report.append(f"  Daily Change: ${change:+.2f} ({change_pct:+.2f}%)")
        
        if indicators.get("sma20"):
            report.append(f"  20-day SMA: ${indicators['sma20']:.2f}")
            if current:
                sma_diff_pct = ((current - indicators['sma20']) / indicators['sma20']) * 100
                report.append(f"  vs SMA20: {sma_diff_pct:+.2f}%")
        
        if indicators.get("rsi"):
            rsi = indicators['rsi']
            report.append(f"  RSI(14): {rsi:.1f}")
            if rsi > 70:
                report.append("    → OVERBOUGHT (consider taking profits)")
            elif rsi < 30:
                report.append("    → OVERSOLD (potential buying opportunity)")
            else:
                report.append("    → NEUTRAL")
        
        report.append("")
    
    # USO-specific recommendations
    uso_data = data.get("USO")
    if uso_data and uso_data.get("current"):
        current_price = uso_data["current"]
        indicators = uso_data.get("indicators", {})
        
        report.append("=" * 60)
        report.append("USO SPECIFIC RECOMMENDATIONS")
        report.append("=" * 60)
        report.append("")
        
        # Position info (assuming 250 shares)
        shares = 250
        position_value = shares * current_price
        report.append(f"Your Position: {shares} shares @ ${current_price:.2f}")
        report.append(f"Position Value: ${position_value:,.2f}")
        report.append("")
        
        # Generate recommendations
        recs = []
        
        if indicators.get("daily_change_pct"):
            change_pct = indicators["daily_change_pct"]
            if change_pct > 2:
                recs.append("Strong upward momentum - consider holding")
            elif change_pct < -2:
                recs.append("Significant decline - evaluate fundamentals")
            else:
                recs.append("Moderate movement - monitor closely")
        
        if indicators.get("rsi"):
            rsi = indicators["rsi"]
            if rsi > 70:
                recs.append("RSI indicates overbought - partial profit-taking advised")
            elif rsi < 30:
                recs.append("RSI indicates oversold - potential accumulation opportunity")
        
        if indicators.get("sma20") and current_price:
            if current_price > indicators["sma20"]:
                recs.append("Price above 20-day SMA - bullish trend")
            else:
                recs.append("Price below 20-day SMA - bearish trend")
        
        if recs:
            for i, rec in enumerate(recs, 1):
                report.append(f"{i}. {rec}")
        else:
            report.append("No strong signals detected. Maintain current position.")
        
        report.append("")
        report.append("NEXT ACTION:")
        if indicators.get("rsi") and indicators["rsi"] > 70:
            report.append("→ Consider selling 25-50 shares to lock in profits")
        elif indicators.get("rsi") and indicators["rsi"] < 30:
            report.append("→ Hold position, could be buying opportunity if fundamentals strong")
        else:
            report.append("→ Hold current position, monitor oil inventory reports")
    
    report.append("")
    report.append("=" * 60)
    report.append("DISCLAIMER: This is automated analysis, not financial advice.")
    report.append("Consult with a financial advisor before making investment decisions.")
    report.append("=" * 60)
    
    return "\n".join(report)

def send_email(subject, body):
    """Send email via Gmail SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"Email sent successfully to {EMAIL_RECEIVER}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}", file=sys.stderr)
        return False

def main():
    print("Starting daily stock analysis...")
    
    # Fetch data for all symbols
    data = {}
    for symbol in SYMBOLS.keys():
        print(f"Fetching data for {symbol}...")
        symbol_data = fetch_stock_data(symbol)
        
        if symbol_data:
            # Calculate indicators
            indicators = calculate_indicators(symbol_data["prices"])
            symbol_data["indicators"] = indicators
            data[symbol] = symbol_data
        else:
            print(f"  Warning: No data for {symbol}")
    
    if not data:
        print("Error: No data retrieved. Exiting.")
        sys.exit(1)
    
    # Generate report
    report = generate_analysis_report(data)
    
    # Print to console for logging
    print("\n" + report + "\n")
    
    # Send email
    subject = f"Daily Stock Analysis - {datetime.now().strftime('%Y-%m-%d')}"
    success = send_email(subject, report)
    
    if success:
        print("Analysis completed and email sent.")
    else:
        print("Analysis completed but email failed.")
        # Save report to file as backup
        filename = f"stock_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(filename, 'w') as f:
            f.write(report)
        print(f"Report saved to {filename}")

if __name__ == "__main__":
    main()