<div align="center">

# TradeMind — AI-Powered Negotiation Platform

**A profit-aware, multi-agent negotiation engine with a conversational interface for e-commerce sellers.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![MySQL](https://img.shields.io/badge/MySQL-8+-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Core Philosophy](#core-philosophy)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Design System](#design-system)
- [Deployment](#deployment)
- [License](#license)

---

## Overview

TradeMind is **not** a chatbot. It is a **business decision engine** with a natural language interface.

Sellers define their product costs, pricing constraints, and negotiation strategy. TradeMind's multi-agent AI system then conducts negotiations with buyers — computing optimal counter-offers, managing concessions, and generating human-like conversational responses — all while **never violating the seller's hard business rules**.

The platform combines rule-based deterministic pricing logic with LLM-powered intelligence, ensuring that every deal outcome is explainable, auditable, and aligned with the seller's profit objectives.

---

## Core Philosophy

| Principle | Description |
|---|---|
| **Profit > Deal Closure** | The system protects seller margins, even if it means walking away. |
| **Constraints > Intelligence** | Hard business rules override AI suggestions — always. |
| **Rules > Language Models** | LLMs generate language; deterministic logic controls pricing. |
| **Predictability > Creativity** | Same inputs produce same pricing decisions, every time. |
| **Safety > Autonomy** | When in doubt, the system defaults to seller protection. |

> *"If there is ever a trade-off between closing a deal and protecting seller constraints, seller constraints win."*

---

## Features

### Negotiation Engine
- **Multi-agent architecture** — three specialized agents (Context Analysis, Pricing Strategy, Conversation) coordinated by an orchestration engine
- **Two operating modes** — `MAX_PROFIT` (conservative, margin-focused) and `MIN_LOSS` (flexible, break-even-focused)
- **Free-text negotiation** — buyers chat naturally; the system extracts offers via LLM with regex fallback
- **Dynamic acceptance thresholds** — the bot becomes progressively more willing to accept as rounds increase, simulating realistic negotiation behavior
- **Session lifecycle management** — create → negotiate (multi-round) → accept / reject / expire / walk-away
- **LLM output validation** — a safety layer ensures the AI never invents prices, contradicts the pricing agent, or uses forbidden phrases

### Business Analytics
- **Revenue & profitability calculator** — revenue, costs, profit, margins, unit economics, ROI
- **Chart data generation** — pre-formatted for Chart.js / Recharts (bar charts, sales funnel, inventory, cost breakdown)
- **Rule-based insights** — severity-graded recommendations (info / warning / critical / success) with configurable thresholds
- **What-if simulation** — test scenarios without affecting live data
- **Competitive intelligence** — isolated plugin that scrapes public listings and runs LLM-powered market positioning analysis

### Product Catalog
- Full CRUD for products with per-user ownership
- Bulk CSV import
- Product performance stats: total sessions, accepted deals, average margin, revenue
- Frontend-computed **Opportunity Score** (0–100) based on margin, buffer, markup, deal rate, and volume

### Authentication & API Access
- **Dual authentication** — JWT tokens for the UI, `tm_`-prefixed API keys for programmatic access
- Both auth methods accepted on all protected endpoints via `Bearer` header
- API key management: generate, list (masked), revoke
- Interactive API documentation with code snippets in Python, JavaScript, and TypeScript

### Email Notifications
- Per-user SMTP configuration (white-label emails from the seller's own domain)
- Branded HTML email templates for deal notifications, session alerts, and API key events
- Non-blocking async dispatch via `asyncio`

### Internationalization (i18n)
- **50+ languages** supported
- Static translations for English and Hindi
- **Live translation via Gemini API** (2.5-flash-lite) — translates the entire UI in a single API call
- Client-side caching in localStorage
- RTL support for Arabic, Hebrew, Urdu, and more
- Language selection modal on first visit

### Real-Time Dashboard
- Live session list with status filters and search
- In-app chat viewer for ongoing negotiations
- Session export functionality
- Buyer callback request tracking
- Dashboard summary metrics

---

## Architecture

### Multi-Agent System

```
┌─────────────────────────────────────────────────────────┐
│                   Orchestration Engine                    │
│              (Session lifecycle & agent flow)             │
├──────────────┬───────────────────┬───────────────────────┤
│              │                   │                        │
│  ┌───────────▼──────────┐  ┌────▼──────────────┐  ┌─────▼──────────────┐
│  │  Context Analysis     │  │  Pricing Strategy  │  │  Conversation       │
│  │  Agent                │  │  Agent             │  │  Agent              │
│  ├───────────────────────┤  ├────────────────────┤  ├─────────────────────┤
│  │ • Strategic posture   │  │ • Compute offers   │  │ • NL response gen   │
│  │ • Aggressiveness      │  │ • Accept / counter │  │ • Justify decisions  │
│  │ • Concession budget   │  │ • Enforce floors   │  │ • Template fallback  │
│  │ • Risk tolerance      │  │ • Hard guardrails  │  │ • LLM validation     │
│  │                       │  │                    │  │                     │
│  │ LLM + heuristic       │  │ LLM + deterministic│  │ LLM + template      │
│  │ fallback              │  │ safety override    │  │ fallback            │
│  └───────────────────────┘  └────────────────────┘  └─────────────────────┘
│                                                                           │
│  Key: LLM provides intelligence — hard rules CANNOT be overridden by AI   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Triple-Fallback Resilience

Every AI-powered component follows a three-tier fallback chain:

1. **LLM call** (OpenRouter → Gemini / GPT-4 / Claude)
2. **Heuristic fallback** (rule-based computation)
3. **Template fallback** (pre-defined responses)

This ensures the system operates correctly even with **zero API keys configured**.

### Data Flow

```
Buyer Message
     │
     ▼
 ┌─────────────┐    ┌──────────────┐    ┌────────────────┐    ┌──────────────┐
 │ Extract      │───▶│ Context      │───▶│ Pricing        │───▶│ Conversation │
 │ Offer/Intent │    │ Analysis     │    │ Strategy       │    │ Generation   │
 └─────────────┘    └──────────────┘    └────────────────┘    └──────────────┘
                                              │                       │
                                              ▼                       ▼
                                     Decision (price)        Natural language
                                     + constraints           response
                                              │                       │
                                              └──────────┬────────────┘
                                                         ▼
                                                  ┌──────────────┐
                                                  │ LLM Validator│
                                                  │ (price-check)│
                                                  └──────┬───────┘
                                                         ▼
                                                   Response to
                                                     Buyer
```

---

## Tech Stack

### Backend

| Component | Technology |
|---|---|
| Framework | **FastAPI** 0.128 |
| Runtime | Python 3.10+ with **Uvicorn** |
| Database | **MySQL 8+** via `aiomysql` (async connection pool) |
| LLM Provider | **OpenRouter** (Gemini 2.0 Flash, GPT-4, Claude) via `httpx` |
| Authentication | **PyJWT** + **bcrypt** |
| Session Cache | `cachetools.TTLCache` (1hr TTL, 10K max sessions) |
| Validation | **Pydantic v2** |
| Rate Limiting | **SlowAPI** |
| Logging | **structlog** |
| Config | `pydantic-settings` + `.env` |
| Testing | **pytest** |

### Frontend

| Component | Technology |
|---|---|
| Framework | **React 19.2** |
| Bundler | **Vite 7.2** |
| Routing | **react-router-dom** 6.28 |
| Styling | **Tailwind CSS** 3.4 + `tailwindcss-animate` |
| UI Primitives | **Radix UI** + shadcn/ui pattern |
| Icons | **lucide-react** |
| 3D Visuals | **Three.js** + `@react-three/fiber` + `@react-three/drei` |
| Translation | **Gemini API** (2.5-flash-lite) |

### Infrastructure

| Component | Technology |
|---|---|
| Reverse Proxy | **Nginx** |
| Frontend Hosting | **Vercel** |
| Backend Hosting | Railway / Render / any FastAPI host |

---

## Project Structure

```
Negotiation-Bot/
├── backend/
│   ├── app/
│   │   ├── main.py                    # Application factory (create_app)
│   │   ├── server.py                  # Uvicorn entry point
│   │   ├── agents/
│   │   │   ├── context_agent.py       # Strategic posture analysis
│   │   │   ├── pricing_agent.py       # Deterministic pricing decisions
│   │   │   └── conversation_agent.py  # Natural language generation
│   │   ├── analytics/
│   │   │   ├── calculations.py        # Business metrics calculator
│   │   │   ├── insights.py            # Rule-based recommendations
│   │   │   ├── routes.py              # Analytics API endpoints
│   │   │   ├── schemas.py             # Analytics request/response models
│   │   │   └── service.py             # Analytics orchestration
│   │   ├── api/
│   │   │   ├── router.py              # Top-level API router
│   │   │   ├── middleware/             # Request logging, CORS
│   │   │   └── v1/                    # Versioned route modules
│   │   ├── core/
│   │   │   ├── config.py              # Settings via pydantic-settings
│   │   │   ├── engine.py              # Negotiation orchestration engine
│   │   │   ├── session.py             # Session lifecycle management
│   │   │   └── logging.py             # structlog configuration
│   │   ├── infrastructure/
│   │   │   ├── database/              # MySQL pool & queries
│   │   │   ├── external/              # External service integrations
│   │   │   └── llm/                   # OpenRouter LLM client
│   │   ├── models/
│   │   │   ├── schemas.py             # Pydantic request/response models
│   │   │   └── enums.py               # NegotiationMode, Decision enums
│   │   ├── services/
│   │   │   ├── email_service.py       # SMTP email notifications
│   │   │   └── llm_validator.py       # AI output price-checking
│   │   └── tests/
│   │       ├── conftest.py            # Pytest fixtures
│   │       ├── unit/                  # Unit tests
│   │       └── integration/           # Integration tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                    # Root component & routing
│   │   ├── pages/
│   │   │   ├── Landing.jsx            # Marketing homepage
│   │   │   ├── Login.jsx              # Authentication
│   │   │   ├── Register.jsx           # User registration
│   │   │   ├── NegotiationDashboard.jsx  # Live session management
│   │   │   ├── BusinessAnalytics.jsx  # Analytics & competitive intel
│   │   │   ├── ProductCatalog.jsx     # Product CRUD + opportunity score
│   │   │   ├── ApiAccess.jsx          # API key management
│   │   │   ├── EmailSettings.jsx      # SMTP configuration
│   │   │   └── ApiReference.jsx       # API documentation
│   │   ├── components/
│   │   │   ├── Layout.jsx / Navbar.jsx / Footer.jsx
│   │   │   ├── NeoButton.jsx / NeoCard.jsx   # Neo-brutalist components
│   │   │   ├── ProtectedRoute.jsx     # Auth guard
│   │   │   ├── LanguageModal.jsx      # i18n language picker
│   │   │   ├── SourceNetwork.jsx      # 3D Three.js visualization
│   │   │   └── ui/                    # shadcn/ui primitives
│   │   ├── context/
│   │   │   ├── I18nContext.jsx         # Translation provider
│   │   │   └── SessionContext.jsx      # Auth session provider
│   │   └── lib/
│   │       ├── api.js                 # API client (Axios)
│   │       ├── encryption.js          # NaCl client-side encryption
│   │       ├── geminiTranslate.js     # Gemini translation service
│   │       ├── productStore.js        # Product state management
│   │       └── i18n/                  # Static translation files
│   ├── package.json
│   ├── tailwind.config.js
│   └── vercel.json                    # Vercel deployment config
├── infrastructure/
│   └── nginx/                         # Reverse proxy configuration
├── agent_instructions.md              # AI agent design specification
├── products.csv                       # Sample product catalog
└── requirements.txt                   # Python dependencies
```

---

## Getting Started

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **MySQL** 8+
- **OpenRouter API key** (for LLM features — system works without it via fallbacks)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/Negotiation-Bot.git
cd Negotiation-Bot
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv env
# Windows:
env\Scripts\activate
# Linux/macOS:
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `/docs` (Swagger) and `/redoc` (ReDoc).

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The UI will be available at `http://localhost:5173`.

### 4. Database Setup

Create a MySQL database named `trademind` and ensure the backend can connect. Tables are auto-created or can be set up from the schema below.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Example |
|---|---|---|
| `MYSQL_HOST` | MySQL server hostname | `localhost` |
| `MYSQL_PORT` | MySQL server port | `3306` |
| `MYSQL_USER` | MySQL username | `root` |
| `MYSQL_PASSWORD` | MySQL password | `yourpassword` |
| `MYSQL_DB` | Database name | `trademind` |
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM access | `sk-or-...` |
| `JWT_SECRET` | Secret key for JWT token signing | `your-secret-key` |

### Frontend (`frontend/.env`)

| Variable | Description | Example |
|---|---|---|
| `VITE_API_URL` | Backend API base URL | `http://localhost:8000` |
| `VITE_AUTH_API_URL` | Auth API base URL | `http://localhost:8000` |
| `VITE_ANALYTICS_API_URL` | Analytics API base URL | `http://localhost:8000/api/v1` |
| `VITE_GEMINI_API_KEY` | Gemini API key for live translations | `AIza...` |

---

## API Reference

### Authentication

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Create user account | None |
| `POST` | `/api/v1/auth/login` | Login, returns JWT | None |
| `GET` | `/api/v1/auth/me` | Get current user | JWT / API Key |

### Negotiation

| Method | Endpoint | Description | Auth | Rate Limit |
|---|---|---|---|---|
| `POST` | `/api/v1/negotiate/sessions` | Create negotiation session | JWT / API Key | 20/min |
| `GET` | `/api/v1/negotiate/sessions/{id}` | Get session summary | JWT / API Key | 60/min |
| `DELETE` | `/api/v1/negotiate/sessions/{id}` | End session early | JWT / API Key | 30/min |
| `POST` | `/api/v1/negotiate/sessions/{id}/turns` | Submit structured offer | JWT / API Key | 30/min |
| `POST` | `/api/v1/negotiate/sessions/{id}/chat` | Free-text chat message | JWT / API Key | 30/min |

### Products

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v1/products` | List user's products | JWT / API Key |
| `POST` | `/api/v1/products` | Create product | JWT / API Key |
| `PUT` | `/api/v1/products/{id}` | Update product | JWT / API Key |
| `DELETE` | `/api/v1/products/{id}` | Delete product | JWT / API Key |
| `POST` | `/api/v1/products/import` | Bulk CSV import | JWT / API Key |

### Chat Sessions

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/chat-sessions` | Start chat session | JWT / API Key |
| `GET` | `/api/v1/chat-sessions` | List sessions | JWT / API Key |
| `GET` | `/api/v1/chat-sessions/{id}` | Get session + messages | JWT / API Key |
| `POST` | `/api/v1/chat-sessions/{id}/messages` | Save round messages | JWT / API Key |
| `PUT` | `/api/v1/chat-sessions/{id}/close` | Close session | JWT / API Key |
| `GET` | `/api/v1/chat-sessions/dashboard/summary` | Dashboard metrics | JWT / API Key |
| `GET` | `/api/v1/chat-sessions/{id}/export` | Export session | JWT / API Key |
| `POST` | `/api/v1/chat-sessions/callback-request` | Request callback | JWT / API Key |
| `GET` | `/api/v1/chat-sessions/callback-requests` | List callbacks | JWT / API Key |

### API Keys

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/api-keys` | Generate new API key | JWT |
| `GET` | `/api/v1/api-keys` | List keys (masked) | JWT |
| `DELETE` | `/api/v1/api-keys/{id}` | Revoke key | JWT |

### Email

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v1/email/settings` | Get email config | JWT / API Key |
| `PUT` | `/api/v1/email/settings` | Update email config | JWT / API Key |
| `POST` | `/api/v1/email/test` | Send test email | JWT / API Key |

### Analytics

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/analytics/calculate` | Calculate business analytics | JWT / API Key |
| `POST` | `/api/v1/analytics/simulate` | What-if simulation | JWT / API Key |
| `POST` | `/api/v1/analytics/competitive-analysis` | Competitive intelligence | JWT / API Key |
| `GET` | `/api/v1/analytics/health` | Health check | None |
| `GET` | `/api/v1/analytics/schema` | Input schema | None |

### Example: Create a Negotiation Session

```bash
curl -X POST http://localhost:8000/api/v1/negotiate/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-or-api-key>" \
  -d '{
    "product": {
      "product_id": "SKU-001",
      "product_name": "Premium Widget",
      "base_price": 100.00,
      "cost_price": 60.00,
      "min_acceptable_price": 75.00,
      "max_loss_percentage": 0
    },
    "inventory": {
      "available_quantity": 100,
      "requested_quantity": 10,
      "inventory_pressure": "medium",
      "sales_frequency": "medium"
    },
    "strategy": {
      "mode": "MAX_PROFIT",
      "urgency": "medium",
      "relationship_priority": "medium",
      "max_rounds": 5
    }
  }'
```

### Example: Free-Text Negotiation

```bash
curl -X POST http://localhost:8000/api/v1/negotiate/sessions/{session_id}/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-or-api-key>" \
  -d '{
    "message": "That seems expensive. Can you do $80?"
  }'
```

---

## Database Schema

The platform uses **MySQL 8+** with the following tables:

### `users`
| Column | Type | Description |
|---|---|---|
| `id` | INT (PK) | Auto-increment user ID |
| `full_name` | VARCHAR | User's full name |
| `email` | VARCHAR (unique) | Login email |
| `password_hash` | VARCHAR | bcrypt-hashed password |
| `created_at` | DATETIME | Registration timestamp |

### `products`
| Column | Type | Description |
|---|---|---|
| `id` | INT (PK) | Auto-increment product ID |
| `user_id` | INT (FK → users) | Product owner |
| `name` | VARCHAR | Product name |
| `base_price` | DECIMAL | Listed / asking price |
| `cost_price` | DECIMAL | Seller's cost |
| `min_acceptable_price` | DECIMAL | Hard floor price |
| `max_loss_percent` | DECIMAL | Maximum allowed loss % |
| `mode` | ENUM | MAX_PROFIT / MIN_LOSS |
| `max_rounds` | INT | Max negotiation rounds |
| `category` | VARCHAR | Product category |
| `status` | VARCHAR | active / inactive |
| `total_sessions` | INT | Negotiation count |
| `accepted_deals` | INT | Successful deals |
| `avg_margin` | DECIMAL | Average profit margin |
| `revenue` | DECIMAL | Total revenue |

### `chat_sessions`
| Column | Type | Description |
|---|---|---|
| `id` | VARCHAR (PK) | Session UUID |
| `user_id` | INT (FK → users) | Session owner |
| `product_name` | VARCHAR | Product being negotiated |
| `mode` | VARCHAR | MAX_PROFIT / MIN_LOSS |
| `base_price` / `cost_price` / `min_price` | DECIMAL | Price parameters |
| `max_rounds` / `rounds_used` | INT | Round tracking |
| `status` | VARCHAR | active / closed / expired |
| `final_price` / `final_decision` | DECIMAL / VARCHAR | Outcome |
| `deal_closed` | BOOLEAN | Whether deal was accepted |
| `buyer_last_offer` / `seller_last_offer` | DECIMAL | Last offers |

### `chat_messages`
| Column | Type | Description |
|---|---|---|
| `id` | INT (PK) | Message ID |
| `session_id` | VARCHAR (FK → chat_sessions) | Parent session |
| `round_number` | INT | Negotiation round |
| `user_message` / `bot_reply` | TEXT | Conversation content |
| `offered_price` / `counter_price` | DECIMAL | Prices in this round |
| `decision` | VARCHAR | accept / counter / reject |

### `api_keys`
| Column | Type | Description |
|---|---|---|
| `id` | INT (PK) | Key ID |
| `user_id` | INT (FK → users) | Key owner |
| `api_key` | VARCHAR | `tm_`-prefixed key |
| `label` | VARCHAR | User-defined label |
| `is_active` | BOOLEAN | Active status |
| `last_used_at` | DATETIME | Last usage timestamp |

### `email_settings`
| Column | Type | Description |
|---|---|---|
| `id` | INT (PK) | Settings ID |
| `user_id` | INT (FK → users, unique) | Settings owner |
| SMTP fields | VARCHAR | host, port, user, password |
| Notification toggles | BOOLEAN | Per-event notification flags |

### `callback_requests`
| Column | Type | Description |
|---|---|---|
| `id` | INT (PK) | Request ID |
| `user_id` / `session_id` | INT / VARCHAR | Associated user & session |
| `phone_number` | VARCHAR | Buyer's phone |
| `product_name` | VARCHAR | Product name |
| `status` | VARCHAR | pending / contacted / resolved |

---

## Design System

TradeMind uses a **Neo-Brutalist** design language — bold colors, thick borders, and high-contrast typography.

| Token | Hex | Preview |
|---|---|---|
| `neo-navy` | `#001524` | ![#001524](https://via.placeholder.com/15/001524/001524.png) Deep navy background |
| `neo-teal` | `#15616D` | ![#15616D](https://via.placeholder.com/15/15616D/15616D.png) Primary accent |
| `neo-cream` | `#FFECD1` | ![#FFECD1](https://via.placeholder.com/15/FFECD1/FFECD1.png) Light background |
| `neo-orange` | `#FF7D00` | ![#FF7D00](https://via.placeholder.com/15/FF7D00/FF7D00.png) CTA / highlights |
| `neo-maroon` | `#78290F` | ![#78290F](https://via.placeholder.com/15/78290F/78290F.png) Danger / emphasis |

---

## Deployment

### Backend

Deploy to **Railway**, **Render**, or any platform that supports Python + FastAPI:

```bash
# Production start
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Ensure all environment variables are set and the MySQL database is accessible.

### Frontend

Deploy to **Vercel** (recommended — `vercel.json` included) or any static host:

```bash
npm run build    # Outputs to dist/
```

### Production Checklist

- [ ] Set `CORS` origins in `backend/app/main.py` to your frontend domain
- [ ] Use a strong, unique `JWT_SECRET`
- [ ] Configure MySQL with proper credentials and SSL
- [ ] Set `OPENROUTER_API_KEY` for full LLM capability (optional — fallbacks work without it)
- [ ] Configure Nginx reverse proxy for HTTPS termination (see `infrastructure/nginx/`)

---

## License

MIT License
