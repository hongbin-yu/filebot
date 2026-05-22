"""
WebBot Mail API — 邮件发送服务
基于 SMTP 的轻量邮件发送接口，支持纯文本和 HTML 邮件
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

router = APIRouter(prefix="/api/v1/mail", tags=["mail"])

# SMTP 配置（从环境变量读取）
SMTP_HOST = os.environ.get("MAIL_SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("MAIL_SMTP_PORT", "25"))
SMTP_USER = os.environ.get("MAIL_SMTP_USER", "")
SMTP_PASS = os.environ.get("MAIL_SMTP_PASS", "")
MAIL_FROM = os.environ.get("MAIL_FROM", "noreply@webbot.local")
MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "WebBot")
SMTP_USE_TLS = os.environ.get("MAIL_SMTP_TLS", "0") == "1"
SMTP_USE_SSL = os.environ.get("MAIL_SMTP_SSL", "0") == "1"


class EmailRequest(BaseModel):
    """邮件发送请求"""
    to: List[str]
    subject: str
    body: str
    body_type: str = "plain"  # "plain" | "html"
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    reply_to: Optional[str] = None


class EmailResponse(BaseModel):
    """邮件发送响应"""
    success: bool
    message: str
    recipients: List[str]


@router.get("/status")
async def mail_status():
    """检查邮件服务配置状态"""
    return {
        "configured": bool(SMTP_HOST and SMTP_HOST != "localhost"),
        "host": SMTP_HOST,
        "port": SMTP_PORT,
        "auth": bool(SMTP_USER),
        "from": f"{MAIL_FROM_NAME} <{MAIL_FROM}>",
        "tls": SMTP_USE_TLS,
        "ssl": SMTP_USE_SSL,
        "note": "Set MAIL_SMTP_HOST/MAIL_SMTP_USER/MAIL_SMTP_PASS env vars to enable"
    }


@router.post("/send", response_model=EmailResponse)
async def send_email(req: EmailRequest):
    """发送邮件"""
    if not req.to:
        raise HTTPException(status_code=400, detail="No recipients specified")

    if not req.body.strip():
        raise HTTPException(status_code=400, detail="Email body is empty")

    all_recipients = list(req.to)
    if req.cc:
        all_recipients.extend(req.cc)
    if req.bcc:
        all_recipients.extend(req.bcc)

    try:
        # 构建邮件
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{Header(MAIL_FROM_NAME, 'utf-8').encode()} <{MAIL_FROM}>"
        msg["To"] = ", ".join(req.to)
        msg["Subject"] = Header(req.subject, "utf-8").encode()

        if req.cc:
            msg["Cc"] = ", ".join(req.cc)
        if req.reply_to:
            msg["Reply-To"] = req.reply_to

        # 附件内容
        if req.body_type == "html":
            msg.attach(MIMEText(req.body, "html", "utf-8"))
        else:
            msg.attach(MIMEText(req.body, "plain", "utf-8"))

        # 发送
        if SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            if SMTP_USE_TLS:
                server.starttls()

        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASS)

        server.sendmail(MAIL_FROM, all_recipients, msg.as_string())
        server.quit()

        return EmailResponse(
            success=True,
            message=f"Email sent to {len(req.to)} recipient(s)",
            recipients=req.to
        )

    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=502, detail="SMTP authentication failed")
    except smtplib.SMTPRecipientsRefused as e:
        raise HTTPException(status_code=502, detail=f"Recipient refused: {e}")
    except smtplib.SMTPException as e:
        raise HTTPException(status_code=502, detail=f"SMTP error: {e}")
    except ConnectionRefusedError:
        raise HTTPException(status_code=502, detail=f"Connection refused to {SMTP_HOST}:{SMTP_PORT}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e}")
