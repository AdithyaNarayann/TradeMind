# TradeMind Negotiation Platform

TradeMind is an AI-powered negotiation platform for e-commerce, built with a modern stack:
- **Frontend:** React 19 + Vite + Tailwind CSS (Neo-Brutalist UI)
- **Backend:** FastAPI + MySQL (async, aiomysql)
- **AI:** Multi-agent negotiation engine using OpenRouter (Gemini, GPT-4, Claude, etc.)

## Features

- Product negotiation chat with AI (seller/buyer simulation)
- Product catalog with analytics and stats
- API key management and secure endpoints
- JWT and API key authentication
- Business analytics and competitive intelligence
- Responsive, modern UI with custom color palette

## Project Structure




```
Negotiation-Bot/
  backend/
    src/
      api/           # FastAPI routes (auth, products, chat, analytics, etc.)
      agents/        # Multi-agent negotiation logic
      core/          # Engine, session management
      db/            # MySQL connection pool
      models/        # Pydantic schemas, enums
      services/      # LLM client, prompts, validators
      config/        # Settings and environment
    requirements.txt
    README.md
  frontend/
    src/
      components/    # React UI components
      pages/         # Main app pages (Chat, Products, API Access, etc.)
      lib/           # API helpers, product store
      test-chat/     # Standalone chat UI
    public/
    package.json
    tailwind.config.js
    .env
  products.csv
```

## Setup Instructions

### 1. Backend

- Python 3.10+ recommended
- Install dependencies:
  ```
  cd backend
  python -m venv env
  env\Scripts\activate  # or source env/bin/activate
  pip install -r requirements.txt
  ```
- Set environment variables (see `.env.example` or below):
  ```
  MYSQL_HOST=localhost
  MYSQL_PORT=3306
  MYSQL_USER=root
  MYSQL_PASSWORD=yourpassword
  MYSQL_DB=trademind
  OPENROUTER_API_KEY=your-openrouter-key
  ```
- Start the server:
  ```
  uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
  ```

### 2. Frontend

- Node.js 18+ recommended
- Install dependencies:
  ```
  cd frontend
  npm install
  ```
- Set environment variables in `frontend/.env`:
  ```
  VITE_API_URL=http://localhost:8000
  VITE_AUTH_API_URL=http://localhost:8000
  VITE_ANALYTICS_API_URL=http://localhost:8000/api/v1
  ```
- Start the dev server:
  ```
  npm run dev
  ```

### 3. Database

- MySQL 8+ required
- Create the database and tables (see schema in DEVELOPMENT_LOG.md or ask for SQL)
- For Railway or cloud: set the correct DB connection variables

## API Overview

- `POST /api/v1/auth/register` — Register user
- `POST /api/v1/auth/login` — Login, returns JWT
- `GET /api/v1/products` — List products (auth required)
- `POST /api/v1/products` — Create product
- `POST /api/v1/chat-sessions` — Start negotiation session
- `POST /api/v1/chat-sessions/{id}/messages` — Send message/offer
- `GET /api/v1/api-keys` — List API keys
- `POST /api/v1/api-keys` — Generate API key

See `frontend/src/pages/ApiAccess.jsx` for a full endpoint reference and code samples.

## Deployment

- Backend can be deployed on Railway, Render, or any FastAPI-compatible host
- Frontend can be deployed on Vercel, Netlify, or any static host
- Set CORS origins in `backend/src/app.py` as needed for production

## Design System

- **neo-navy:** #001524
- **neo-teal:** #15616D
- **neo-cream:** #FFECD1
- **neo-orange:** #FF7D00
- **neo-maroon:** #78290F

## License

MIT License
