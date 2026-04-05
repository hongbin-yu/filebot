#!/usr/bin/env python3
import json
import smtplib
from email.mime.text import MIMEText

def test_smtp():
    # Read config
    with open('/home/hongb/.openclaw/openclaw.json', 'r') as f:
        config = json.load(f)
    
    mail_config = config.get('mail', {})
    print(f"Mail config: {mail_config}")
    
    if not mail_config:
        print("No mail configuration found")
        return False
    
    try:
        smtp_server = mail_config['smtp']
        smtp_port = int(mail_config['port'])
        user = mail_config['user']
        password = mail_config['password']
        
        print(f"Testing connection to {smtp_server}:{smtp_port}...")
        
        # Simple test
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        print("TLS started")
        server.login(user, password)
        print("Login successful")
        
        # Send test email
        receiver = user
        msg = MIMEText("Test email from OpenClaw SMTP configuration.")
        msg['Subject'] = "SMTP Test"
        msg['From'] = user
        msg['To'] = receiver
        
        server.send_message(msg)
        server.quit()
        
        print(f"Test email sent to {receiver}")
        return True
        
    except Exception as e:
        print(f"SMTP error: {type(e).__name__}: {e}")
        print("\nCommon Gmail issues:")
        print("1. Enable 'Less secure app access' (not recommended)")
        print("2. Use App Password: https://myaccount.google.com/apppasswords")
        print("3. Enable 2-Step Verification first, then generate App Password")
        return False

if __name__ == '__main__':
    success = test_smtp()
    exit(0 if success else 1)