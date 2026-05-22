"""
WebBot Feedback API — 加拿大政府网站反馈表单后端
接收 Canada.ca 标准页面反馈（"Did you find what you were looking for?"）
通过邮件通知管理员，并记录到数据库
"""

from fastapi import APIRouter, HTTPException, Request, Form
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import smtplib
import sqlite3
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])

DB_PATH = os.environ.get("WEBBOT_DB_PATH", "app/webbot.db")

# 反馈邮件目标地址（环境变量配置）
FEEDBACK_TO = os.environ.get("FEEDBACK_TO", "")
FEEDBACK_FROM = os.environ.get("FEEDBACK_FROM", "feedback@webbot.local")
FEEDBACK_SUBJECT_PREFIX = os.environ.get("FEEDBACK_SUBJECT_PREFIX", "[Page Feedback]")

# 复用 mail 模块的 SMTP 配置
SMTP_HOST = os.environ.get("MAIL_SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("MAIL_SMTP_PORT", "25"))
SMTP_USER = os.environ.get("MAIL_SMTP_USER", "")
SMTP_PASS = os.environ.get("MAIL_SMTP_PASS", "")
SMTP_USE_TLS = os.environ.get("MAIL_SMTP_TLS", "0") == "1"
SMTP_USE_SSL = os.environ.get("MAIL_SMTP_SSL", "0") == "1"


# ========== Pydantic 模型（JSON API） ==========

class FeedbackProblemCreate(BaseModel):
    """Canada.ca 页面反馈 — 提交表单数据"""
    helpful: str  # "Yes-Oui" | "No-Non"
    details: Optional[str] = None
    # 页面元数据（通过 data-wb-json 自动填充）
    submissionPage: Optional[str] = None
    pageTitle: Optional[str] = None
    language: Optional[str] = None
    oppositelang: Optional[str] = None
    themeopt: Optional[str] = None
    sectionopt: Optional[str] = None
    institutionopt: Optional[str] = None


class FeedbackResponse(BaseModel):
    """反馈提交响应"""
    success: bool
    message: str


# ========== 数据库 ==========

def _get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_feedback_table():
    """确保反馈表存在"""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS webbot_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            helpful TEXT,
            details TEXT,
            submission_page TEXT,
            page_title TEXT,
            language TEXT,
            oppositelang TEXT,
            theme TEXT,
            section TEXT,
            institution TEXT,
            status TEXT DEFAULT 'new',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# ========== 邮件发送 ==========

def _send_feedback_email(feedback, db_id: int):
    """通过 SMTP 发送反馈通知邮件"""
    if not FEEDBACK_TO:
        return

    is_yes = feedback.get("helpful") == "Yes-Oui"
    helpful_label = "✅ Found what I was looking for" if is_yes else "❌ Did NOT find what I was looking for"
    emoji = "✅" if is_yes else "❌"

    details = feedback.get("details", "")
    page_url = feedback.get("submissionPage", "N/A")
    page_title = feedback.get("pageTitle", "N/A")
    lang = feedback.get("language", "en").upper()
    theme = feedback.get("themeopt", "")
    section = feedback.get("sectionopt", "")
    institution = feedback.get("institutionopt", "")

    email_body_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 20px auto;">
    <h2 style="color: #333;">{emoji} Page Feedback #{db_id}</h2>
    <table style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee; font-weight: bold; color: #555; width: 120px;">Feedback</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{helpful_label}</td>
        </tr>
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee; font-weight: bold; color: #555;">Page</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;"><a href="{page_url}">{page_title or page_url}</a></td>
        </tr>
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee; font-weight: bold; color: #555;">Lang</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{lang}</td>
        </tr>"""

    if theme:
        email_body_html += f"""
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee; font-weight: bold; color: #555;">Theme</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{theme}</td>
        </tr>"""
    if section:
        email_body_html += f"""
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee; font-weight: bold; color: #555;">Section</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{section}</td>
        </tr>"""
    if institution:
        email_body_html += f"""
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee; font-weight: bold; color: #555;">Institution</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{institution}</td>
        </tr>"""

    if details:
        email_body_html += f"""
    </table>
    <h3 style="color: #333; margin-top: 20px;">Details</h3>
    <div style="background: #f5f5f5; padding: 15px; border-radius: 6px; white-space: pre-wrap;">{details}</div>"""
    else:
        email_body_html += """
    </table>
    <p style="color: #888; margin-top: 15px;">(No additional details provided)</p>"""

    email_body_html += """
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
    <p style="color: #999; font-size: 12px;">This email was sent by the WebBot Feedback System</p>
</body>
</html>"""

    # 纯文本备用
    plain_body = f"""[{emoji}] Page Feedback #{db_id}
Feedback: {helpful_label}
Page: {page_url}
Title: {page_title}
Lang: {lang}
"""
    if details:
        plain_body += f"\nDetails:\n{details}"

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"Page Feedback <{FEEDBACK_FROM}>"
        msg["To"] = FEEDBACK_TO
        subject = f"{FEEDBACK_SUBJECT_PREFIX} #{db_id} - {page_title or page_url}"
        msg["Subject"] = Header(subject[:200], "utf-8").encode()

        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(email_body_html, "html", "utf-8"))

        if SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            if SMTP_USE_TLS:
                server.starttls()

        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASS)

        server.sendmail(FEEDBACK_FROM, [FEEDBACK_TO], msg.as_string())
        server.quit()
    except Exception as e:
        print(f"⚠️  Feedback email notification failed: {e}")


def _store_and_notify(feedback_dict: dict) -> int:
    """存储反馈到数据库并发送通知"""
    _init_feedback_table()
    conn = _get_db()
    cursor = conn.cursor()
    try:
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO webbot_feedback
            (helpful, details, submission_page, page_title, language, oppositelang,
             theme, section, institution, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feedback_dict.get("helpful"),
            feedback_dict.get("details"),
            feedback_dict.get("submissionPage"),
            feedback_dict.get("pageTitle"),
            feedback_dict.get("language"),
            feedback_dict.get("oppositelang"),
            feedback_dict.get("themeopt"),
            feedback_dict.get("sectionopt"),
            feedback_dict.get("institutionopt"),
            "new",
            now
        ))
        conn.commit()
        db_id = cursor.lastrowid

        # 发邮件通知
        _send_feedback_email(feedback_dict, db_id)

        return db_id
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()


# ========== API 端点 ==========

@router.get("/status")
async def feedback_status():
    """反馈服务状态"""
    return {
        "configured": bool(FEEDBACK_TO),
        "email_to": FEEDBACK_TO or "not configured",
        "smtp_configured": bool(SMTP_HOST and SMTP_HOST != "localhost" and SMTP_USER),
        "format": "matches Canada.ca page feedback form (QueueProblemForm)"
    }


@router.post("/submit")
async def submit_feedback_json(feedback: FeedbackProblemCreate):
    """提交反馈（JSON 格式）"""
    if feedback.helpful not in ("Yes-Oui", "No-Non"):
        raise HTTPException(status_code=400, detail="Invalid helpful value. Must be 'Yes-Oui' or 'No-Non'")

    db_id = _store_and_notify(feedback.model_dump())

    return FeedbackResponse(
        success=True,
        message=f"Thank you for your feedback."
    )


@router.post("/QueueProblemForm")
async def submit_feedback_form(
    request: Request,
    helpful: str = Form("Yes-Oui"),
    details: Optional[str] = Form(None),
    submissionPage: Optional[str] = Form(None),
    pageTitle: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    oppositelang: Optional[str] = Form(None),
    themeopt: Optional[str] = Form(None),
    sectionopt: Optional[str] = Form(None),
    institutionopt: Optional[str] = Form(None)
):
    """兼容 Canada.ca 表单提交（form-urlencoded）
    与 GCWeb 的 wb-postback 和 data-wb-json 配合使用。
    前端表单直接 action="/api/v1/feedback/QueueProblemForm"
    """
    if helpful not in ("Yes-Oui", "No-Non"):
        raise HTTPException(status_code=400, detail="Invalid helpful value")

    feedback_dict = {
        "helpful": helpful,
        "details": details,
        "submissionPage": submissionPage,
        "pageTitle": pageTitle,
        "language": language,
        "oppositelang": oppositelang,
        "themeopt": themeopt,
        "sectionopt": sectionopt,
        "institutionopt": institutionopt
    }

    db_id = _store_and_notify(feedback_dict)

    # 返回 HTML 片段供 wb-postback 处理
    return f"""<div class="gc-pft-thnk">
    <p class="mrgn-tp-sm mrgn-bttm-0" role="status">
        <span class="glyphicon glyphicon-ok text-success mrgn-rght-sm" aria-hidden="true"></span>
        Thank you for your feedback.
    </p>
</div>"""


@router.get("/list", include_in_schema=False)
async def list_feedback(limit: int = 50, offset: int = 0):
    """查看反馈列表（管理员用）"""
    _init_feedback_table()
    conn = _get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM webbot_feedback")
        total = cursor.fetchone()["total"]
        cursor.execute("""
            SELECT id, helpful, details, submission_page, page_title,
                   language, theme, section, institution, created_at
            FROM webbot_feedback
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = [dict(r) for r in cursor.fetchall()]
        return {"total": total, "limit": limit, "offset": offset, "items": rows}
    finally:
        conn.close()
