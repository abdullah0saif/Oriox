# TempMailBox

A beautiful, modern temporary email service with stunning UI/UX and smooth transitions.

## Features

- **Instant Email Generation** — One-click disposable email addresses
- **Real-Time Inbox** — Live polling with WebSocket support
- **Beautiful UI** — Glassmorphism design with animated gradients
- **Smooth Transitions** — Framer Motion animations throughout
- **Auto-Expiry** — Emails self-destruct after 10 minutes
- **Copy to Clipboard** — Quick copy with visual feedback
- **Test Emails** — Send test emails to verify your inbox
- **Responsive Design** — Works beautifully on all devices

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Tailwind CSS, Framer Motion |
| Backend | Python, FastAPI, WebSockets |
| Icons | Lucide React |

## Quick Start

### Frontend

```bash
cd temp-mail
npm install
npm run dev
```

### Backend

```bash
cd temp-mail/server
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The frontend dev server proxies API requests to the backend automatically.

## Architecture

```
Frontend (React + Vite)  →  FastAPI Backend
     ↕ WebSocket              ↕
  Real-time updates     In-memory store
```

The backend generates random email addresses, stores messages in memory with TTL-based expiry, and supports WebSocket connections for real-time updates.
