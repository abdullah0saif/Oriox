"""TempMailBox — Backend API server for temporary email service."""

import asyncio
import hashlib
import random
import string
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DOMAINS = [
    "tempbox.email",
    "quickmail.ink",
    "dropmail.cc",
    "flashbox.io",
    "notrack.mail",
]

EMAIL_TTL_SECONDS = 600  # 10 minutes
CLEANUP_INTERVAL = 30

email_store: dict[str, dict] = {}
message_store: dict[str, list[dict]] = {}
ws_connections: dict[str, list[WebSocket]] = {}


class EmailAddress(BaseModel):
    address: str
    created_at: str
    expires_at: str
    ttl_seconds: int
    domain: str


class EmailMessage(BaseModel):
    id: str
    from_address: str
    to_address: str
    subject: str
    body: str
    html: str
    received_at: str
    is_read: bool
    attachments: list[str]


class SendTestRequest(BaseModel):
    to_address: str
    subject: str | None = None
    body: str | None = None


SAMPLE_SUBJECTS = [
    "Welcome to our platform!",
    "Your verification code: 847291",
    "Password reset request",
    "Your order has been confirmed",
    "Meeting reminder: Team standup at 3 PM",
    "Invoice #INV-2024-0042",
    "New login detected on your account",
    "Weekly newsletter — Top stories",
    "Your subscription is about to expire",
    "Important security update",
]

SAMPLE_BODIES = [
    """Hi there,

Welcome to our platform! We're thrilled to have you on board.

To get started, please verify your email address by clicking the link below:
https://example.com/verify?token=abc123

If you didn't create an account, please ignore this email.

Best regards,
The Team""",
    """Hello,

Your one-time verification code is: 847291

This code will expire in 10 minutes. Please do not share this code with anyone.

If you didn't request this code, please contact our support team immediately.

Thanks,
Security Team""",
    """Hi,

We received a request to reset your password. Click the link below to create a new password:

https://example.com/reset-password?token=xyz789

This link will expire in 24 hours.

If you didn't request a password reset, you can safely ignore this email.

Best,
Account Security""",
    """Dear Customer,

Your order #ORD-2024-8847 has been confirmed and is being processed.

Order Summary:
- Premium Plan (Annual) — $99.00
- Tax — $8.91
- Total — $107.91

Estimated delivery: 3-5 business days

Track your order: https://example.com/track/ORD-2024-8847

Thank you for your purchase!""",
    """Hi Team,

This is a reminder that our daily standup meeting is scheduled for today at 3:00 PM EST.

Agenda:
1. Yesterday's progress
2. Today's goals
3. Blockers and dependencies

Join link: https://meet.example.com/standup-daily

See you there!""",
]

SAMPLE_SENDERS = [
    "noreply@example.com",
    "security@accounts.example.com",
    "support@helpdesk.io",
    "billing@payments.example.com",
    "newsletter@updates.example.com",
    "no-reply@notifications.app",
    "team@workspace.example.com",
    "hello@startup.io",
]

SAMPLE_HTML_TEMPLATES = [
    """<div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08);">
  <div style="background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 40px 30px; text-align: center;">
    <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 700;">Welcome! 🎉</h1>
    <p style="color: rgba(255,255,255,0.85); margin: 10px 0 0;">We're glad to have you here</p>
  </div>
  <div style="padding: 30px;">
    <p style="color: #374151; line-height: 1.6;">{body}</p>
    <div style="text-align: center; margin: 30px 0;">
      <a href="#" style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">Get Started</a>
    </div>
  </div>
  <div style="background: #f9fafb; padding: 20px 30px; text-align: center; border-top: 1px solid #e5e7eb;">
    <p style="color: #9ca3af; font-size: 12px; margin: 0;">This is a test email from TempMailBox</p>
  </div>
</div>""",
    """<div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0f172a; border-radius: 12px; overflow: hidden;">
  <div style="padding: 40px 30px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1);">
    <div style="width: 60px; height: 60px; background: linear-gradient(135deg, #22d3ee, #6366f1); border-radius: 12px; margin: 0 auto 16px; display: flex; align-items: center; justify-content: center;">
      <span style="font-size: 28px;">🔐</span>
    </div>
    <h1 style="color: #f8fafc; margin: 0; font-size: 22px;">Security Alert</h1>
  </div>
  <div style="padding: 30px;">
    <p style="color: #cbd5e1; line-height: 1.7;">{body}</p>
    <div style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px; padding: 16px; margin: 20px 0; text-align: center;">
      <span style="color: #a5b4fc; font-size: 32px; letter-spacing: 8px; font-family: monospace; font-weight: 700;">847291</span>
    </div>
  </div>
  <div style="padding: 20px 30px; text-align: center;">
    <p style="color: #64748b; font-size: 12px; margin: 0;">TempMailBox — Secure temporary email</p>
  </div>
</div>""",
]


def generate_email_address() -> tuple[str, str]:
    adjectives = [
        "swift", "bright", "cool", "fast", "bold", "keen", "calm", "pure",
        "wise", "warm", "dark", "soft", "wild", "free", "true", "rare",
        "epic", "nova", "zero", "flux", "neo", "ace", "zen", "max",
    ]
    nouns = [
        "fox", "wolf", "hawk", "bear", "star", "moon", "rain", "fire",
        "wave", "wind", "snow", "leaf", "rock", "sage", "byte", "node",
        "core", "link", "dash", "pulse", "pixel", "spark", "storm", "void",
    ]
    adj = random.choice(adjectives)
    noun = random.choice(nouns)
    num = random.randint(100, 9999)
    domain = random.choice(DOMAINS)
    address = f"{adj}.{noun}{num}@{domain}"
    return address, domain


def generate_message_id() -> str:
    return str(uuid.uuid4())[:8]


def create_test_email(to_address: str, subject: str | None = None, body: str | None = None) -> dict:
    chosen_subject = subject or random.choice(SAMPLE_SUBJECTS)
    chosen_body = body or random.choice(SAMPLE_BODIES)
    template = random.choice(SAMPLE_HTML_TEMPLATES)
    html = template.replace("{body}", chosen_body.replace("\n", "<br>"))

    return {
        "id": generate_message_id(),
        "from_address": random.choice(SAMPLE_SENDERS),
        "to_address": to_address,
        "subject": chosen_subject,
        "body": chosen_body,
        "html": html,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "is_read": False,
        "attachments": [],
    }


async def cleanup_expired():
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        now = time.time()
        expired = [
            addr for addr, data in email_store.items()
            if now - data["created_at_ts"] > EMAIL_TTL_SECONDS
        ]
        for addr in expired:
            email_store.pop(addr, None)
            message_store.pop(addr, None)
            conns = ws_connections.pop(addr, [])
            for ws in conns:
                try:
                    await ws.close()
                except Exception:
                    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(cleanup_expired())
    yield
    task.cancel()


app = FastAPI(
    title="TempMailBox API",
    description="Temporary email service API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/email/generate", response_model=EmailAddress)
async def generate_email():
    address, domain = generate_email_address()
    now = time.time()
    now_dt = datetime.now(timezone.utc)

    email_store[address] = {
        "created_at_ts": now,
        "created_at": now_dt.isoformat(),
        "domain": domain,
    }
    message_store[address] = []

    return EmailAddress(
        address=address,
        created_at=now_dt.isoformat(),
        expires_at=datetime.fromtimestamp(now + EMAIL_TTL_SECONDS, tz=timezone.utc).isoformat(),
        ttl_seconds=EMAIL_TTL_SECONDS,
        domain=domain,
    )


@app.get("/api/email/{address}/info", response_model=EmailAddress)
async def get_email_info(address: str):
    if address not in email_store:
        raise HTTPException(status_code=404, detail="Email address not found or expired")

    data = email_store[address]
    elapsed = time.time() - data["created_at_ts"]
    remaining = max(0, EMAIL_TTL_SECONDS - int(elapsed))

    if remaining == 0:
        email_store.pop(address, None)
        message_store.pop(address, None)
        raise HTTPException(status_code=404, detail="Email address expired")

    return EmailAddress(
        address=address,
        created_at=data["created_at"],
        expires_at=datetime.fromtimestamp(
            data["created_at_ts"] + EMAIL_TTL_SECONDS, tz=timezone.utc
        ).isoformat(),
        ttl_seconds=remaining,
        domain=data["domain"],
    )


@app.get("/api/email/{address}/messages", response_model=list[EmailMessage])
async def get_messages(address: str):
    if address not in email_store:
        raise HTTPException(status_code=404, detail="Email address not found or expired")
    return [EmailMessage(**msg) for msg in message_store.get(address, [])]


@app.get("/api/email/{address}/messages/{message_id}", response_model=EmailMessage)
async def get_message(address: str, message_id: str):
    if address not in email_store:
        raise HTTPException(status_code=404, detail="Email address not found or expired")

    messages = message_store.get(address, [])
    for msg in messages:
        if msg["id"] == message_id:
            msg["is_read"] = True
            return EmailMessage(**msg)

    raise HTTPException(status_code=404, detail="Message not found")


@app.delete("/api/email/{address}/messages/{message_id}")
async def delete_message(address: str, message_id: str):
    if address not in email_store:
        raise HTTPException(status_code=404, detail="Email address not found or expired")

    messages = message_store.get(address, [])
    message_store[address] = [m for m in messages if m["id"] != message_id]
    return {"status": "deleted"}


@app.delete("/api/email/{address}")
async def delete_email(address: str):
    email_store.pop(address, None)
    message_store.pop(address, None)
    conns = ws_connections.pop(address, [])
    for ws in conns:
        try:
            await ws.close()
        except Exception:
            pass
    return {"status": "deleted"}


@app.post("/api/email/send-test", response_model=EmailMessage)
async def send_test_email(request: SendTestRequest):
    if request.to_address not in email_store:
        raise HTTPException(status_code=404, detail="Email address not found or expired")

    msg = create_test_email(request.to_address, request.subject, request.body)
    message_store.setdefault(request.to_address, []).insert(0, msg)

    for ws in ws_connections.get(request.to_address, []):
        try:
            await ws.send_json({"type": "new_message", "message": msg})
        except Exception:
            pass

    return EmailMessage(**msg)


@app.websocket("/ws/{address}")
async def websocket_endpoint(websocket: WebSocket, address: str):
    await websocket.accept()
    ws_connections.setdefault(address, []).append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_connections.get(address, []).remove(websocket) if websocket in ws_connections.get(address, []) else None


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "active_emails": len(email_store),
        "total_messages": sum(len(msgs) for msgs in message_store.values()),
    }
