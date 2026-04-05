import smtplib
from email.mime.text import MIMEText

sender = "hongbin.yu413@gmail.com"
password = "Nina201@"
receiver = "hongbin.yu413@gmail.com"

msg = MIMEText("Test email from OpenClaw stock analysis system.")
msg['Subject'] = "Test Email"
msg['From'] = sender
msg['To'] = receiver

try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender, password)
    server.send_message(msg)
    server.quit()
    print("Test email sent successfully!")
except Exception as e:
    print(f"Error: {e}")
    print("Note: You may need to use an 'App Password' instead of your regular Gmail password.")
    print("Go to https://myaccount.google.com/apppasswords to generate one.")