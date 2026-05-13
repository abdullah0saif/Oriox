"""TempMailBox — Backend API server powered by Mail.tm for real email receiving."""

import asyncio
import random
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

MAIL_TM_API = "https://api.mail.tm"
EMAIL_TTL_SECONDS = 600  # 10 minutes
CLEANUP_INTERVAL = 30

email_store: dict[str, dict] = {}
ws_connections: dict[str, list[WebSocket]] = {}

ADJECTIVES = [
    "swift", "bright", "cool", "fast", "bold", "keen", "calm", "pure",
    "wise", "warm", "dark", "soft", "wild", "free", "true", "rare",
    "epic", "nova", "zero", "flux", "neo", "ace", "zen", "max",
]
NOUNS = [
    "fox", "wolf", "hawk", "bear", "star", "moon", "rain", "fire",
    "wave", "wind", "snow", "leaf", "rock", "sage", "byte", "node",
    "core", "link", "dash", "pulse", "pixel", "spark", "storm", "void",
]


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
]

SAMPLE_BODIES = [
    "Hi there,\n\nWelcome to our platform! We're thrilled to have you on board.\n\nTo get started, please verify your email address by clicking the link below:\nhttps://example.com/verify?token=abc123\n\nBest regards,\nThe Team",
    "Hello,\n\nYour one-time verification code is: 847291\n\nThis code will expire in 10 minutes.\n\nThanks,\nSecurity Team",
]

SAMPLE_SENDERS = [
    "noreply@example.com",
    "security@accounts.example.com",
    "support@helpdesk.io",
]

SAMPLE_HTML_TEMPLATES = [
    '<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08);"><div style="background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 40px 30px; text-align: center;"><h1 style="color: white; margin: 0; font-size: 24px;">Welcome! 🎉</h1></div><div style="padding: 30px;"><p style="color: #374151; line-height: 1.6;">{body}</p><div style="text-align: center; margin: 30px 0;"><a href="#" style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">Get Started</a></div></div><div style="background: #f9fafb; padding: 20px 30px; text-align: center;"><p style="color: #9ca3af; font-size: 12px; margin: 0;">This is a test email from TempMailBox</p></div></div>',
]


async def get_available_domains() -> list[str]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{MAIL_TM_API}/domains")
        resp.raise_for_status()
        data = resp.json()
        return [d["domain"] for d in data.get("hydra:member", [])]


async def create_mailtm_account(address: str, password: str) -> tuple[dict, str, str]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{MAIL_TM_API}/accounts",
            json={"address": address, "password": password},
        )
        resp.raise_for_status()
        account = resp.json()
        actual_address = account.get("address", address)

        resp = await client.post(
            f"{MAIL_TM_API}/token",
            json={"address": actual_address, "password": password},
        )
        resp.raise_for_status()
        token_data = resp.json()

        return account, token_data["token"], actual_address


async def delete_mailtm_account(account_id: str, token: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.delete(
                f"{MAIL_TM_API}/accounts/{account_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
    except Exception:
        pass


def normalize_message_summary(msg: dict) -> dict:
    from_data = msg.get("from", {})
    to_list = msg.get("to", [])
    return {
        "id": msg["id"],
        "from_address": from_data.get("address", from_data.get("name", "unknown")),
        "to_address": to_list[0]["address"] if to_list else "",
        "subject": msg.get("subject", "(no subject)"),
        "body": msg.get("intro", ""),
        "html": "",
        "received_at": msg.get("createdAt", ""),
        "is_read": msg.get("seen", False),
        "attachments": [],
    }


def normalize_message_detail(msg: dict) -> dict:
    from_data = msg.get("from", {})
    to_list = msg.get("to", [])
    html_content = ""
    for part in msg.get("html", []):
        if isinstance(part, str):
            html_content += part
    if not html_content:
        text = msg.get("text", "")
        if text:
            html_content = f"<pre style='white-space: pre-wrap; font-family: inherit;'>{text}</pre>"
    attachments = []
    for att in msg.get("attachments", []):
        if isinstance(att, dict):
            attachments.append(att.get("filename", "attachment"))
        elif isinstance(att, str):
            attachments.append(att)
    return {
        "id": msg["id"],
        "from_address": from_data.get("address", from_data.get("name", "unknown")),
        "to_address": to_list[0]["address"] if to_list else "",
        "subject": msg.get("subject", "(no subject)"),
        "body": msg.get("text", msg.get("intro", "")),
        "html": html_content,
        "received_at": msg.get("createdAt", ""),
        "is_read": msg.get("seen", True),
        "attachments": attachments,
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
            data = email_store.pop(addr, None)
            if data:
                await delete_mailtm_account(data["account_id"], data["token"])
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
    description="Temporary email service powered by Mail.tm",
    version="2.0.0",
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
    try:
        domains = await get_available_domains()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to fetch domains: {e}")

    if not domains:
        raise HTTPException(status_code=503, detail="No domains available")

    domain = random.choice(domains)
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    num = random.randint(100, 9999)
    address = f"{adj}.{noun}{num}@{domain}"
    password = "Tmp" + secrets.token_hex(8) + "X1!"

    try:
        account, token, actual_address = await create_mailtm_account(address, password)
        address = actual_address
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 422:
            address = f"{adj}{noun}{num}@{domain}"
            try:
                account, token, actual_address = await create_mailtm_account(address, password)
                address = actual_address
            except Exception as e2:
                raise HTTPException(status_code=503, detail=f"Failed to create email: {e2}")
        else:
            raise HTTPException(status_code=503, detail=f"Failed to create email: {e}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to create email: {e}")

    now = time.time()
    now_dt = datetime.now(timezone.utc)

    email_store[address] = {
        "token": token,
        "account_id": account["id"],
        "password": password,
        "created_at_ts": now,
        "created_at": now_dt.isoformat(),
        "domain": domain,
    }

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
        removed = email_store.pop(address, None)
        if removed:
            await delete_mailtm_account(removed["account_id"], removed["token"])
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

    data = email_store[address]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{MAIL_TM_API}/messages",
                headers={"Authorization": f"Bearer {data['token']}"},
            )
            resp.raise_for_status()
            result = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch messages: {e}")

    messages = result.get("hydra:member", [])
    return [EmailMessage(**normalize_message_summary(m)) for m in messages]


@app.get("/api/email/{address}/messages/{message_id}", response_model=EmailMessage)
async def get_message(address: str, message_id: str):
    if address not in email_store:
        raise HTTPException(status_code=404, detail="Email address not found or expired")

    data = email_store[address]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{MAIL_TM_API}/messages/{message_id}",
                headers={"Authorization": f"Bearer {data['token']}"},
            )
            resp.raise_for_status()
            msg = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Message not found")
        raise HTTPException(status_code=502, detail=f"Failed to fetch message: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch message: {e}")

    return EmailMessage(**normalize_message_detail(msg))


@app.delete("/api/email/{address}/messages/{message_id}")
async def delete_message(address: str, message_id: str):
    if address not in email_store:
        raise HTTPException(status_code=404, detail="Email address not found or expired")

    data = email_store[address]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.delete(
                f"{MAIL_TM_API}/messages/{message_id}",
                headers={"Authorization": f"Bearer {data['token']}"},
            )
    except Exception:
        pass
    return {"status": "deleted"}


@app.delete("/api/email/{address}")
async def delete_email(address: str):
    data = email_store.pop(address, None)
    if data:
        await delete_mailtm_account(data["account_id"], data["token"])
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

    subject = request.subject or random.choice(SAMPLE_SUBJECTS)
    body = request.body or random.choice(SAMPLE_BODIES)
    template = random.choice(SAMPLE_HTML_TEMPLATES)
    html = template.replace("{body}", body.replace("\n", "<br>"))

    msg = {
        "id": secrets.token_hex(4),
        "from_address": random.choice(SAMPLE_SENDERS),
        "to_address": request.to_address,
        "subject": subject,
        "body": body,
        "html": html,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "is_read": False,
        "attachments": [],
    }

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
        if address in ws_connections and websocket in ws_connections[address]:
            ws_connections[address].remove(websocket)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "active_emails": len(email_store),
        "version": "2.0.0",
        "provider": "mail.tm",
    }
