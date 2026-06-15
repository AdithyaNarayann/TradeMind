# TradeMind - Quick Start & Development Guide

**Version**: 1.0.0  
**Last Updated**: March 5, 2026  

---

## 📋 Table of Contents

1. [Project at a Glance](#project-at-a-glance)
2. [Quick Start (5 Minutes)](#quick-start-5-minutes)
3. [Development Workflow](#development-workflow)
4. [Common Tasks](#common-tasks)
5. [Debugging Tips](#debugging-tips)
6. [Key Files to Know](#key-files-to-know)
7. [API Testing](#api-testing)
8. [Database Queries](#database-queries)

---

## Project at a Glance

**TradeMind** is a profit-aware, multi-agent negotiation engine.

### Core Concept
1. **Seller defines** product costs, pricing constraints, and strategy
2. **Buyer makes offers** in free-text or structured format
3. **Three agents process** the offer:
   - **Context Agent**: Strategic posture analysis
   - **Pricing Agent**: Deterministic counter-offer computation
   - **Conversation Agent**: Natural language response generation
4. **System responds** with ACCEPT/COUNTER/REJECT + explanation
5. **Negotiation continues** for up to N rounds (seller-defined)

### Tech Stack Quick Facts
- **Backend**: FastAPI (Python) + MySQL + OpenRouter LLM
- **Frontend**: React 19.2 + Vite + Tailwind CSS
- **Auth**: JWT tokens + API keys
- **Internationalization**: 50+ languages (Gemini API)

---

## Quick Start (5 Minutes)

### Prerequisites
- Python 3.10+, Node.js 18+, MySQL 8+
- Git clone of this repo

### Step 1: Backend Setup & Run

```bash
cd backend

# Create virtual environment
python -m venv env

# Windows:
env\Scripts\activate
# Linux/macOS:
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with required vars
cat > .env << 'EOF'
ENV=development
DEBUG=true
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DB=trademind
JWT_SECRET=your-secret-key-change-in-production
OPENROUTER_API_KEY=sk-or-...  # Optional, system works without it
EOF

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output**:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Check API is working**:
```bash
curl http://localhost:8000/docs  # Swagger UI
```

### Step 2: Frontend Setup & Run

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local (optional, uses defaults)
cat > .env.local << 'EOF'
VITE_API_URL=http://localhost:8000
EOF

# Start dev server
npm run dev
```

**Expected Output**:
```
  VITE v7.2.4  ready in 123 ms

  ➜  Local:   http://localhost:5173/
```

Open `http://localhost:5173` in browser.

### Step 3: Database Setup

```bash
# Create database
mysql -h localhost -u root -p -e "CREATE DATABASE trademind;"

# Run migration (if schema file exists, else tables auto-create)
# mysql -h localhost -u root -p trademind < backend/app/infrastructure/database/migrations/init.sql
```

### ✓ You're Ready!

- Frontend: http://localhost:5173
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Development Workflow

### Typical Developer Session

#### Morning (Feature Development)

```bash
# 1. Start backend (if not already running)
cd backend
source env/bin/activate  # or env\Scripts\activate on Windows
uvicorn app.main:app --reload

# 2. In another terminal, start frontend
cd frontend
npm run dev

# 3. Make code changes
# Edit backend: app/agents/pricing_agent.py
# Edit frontend: src/pages/NegotiationDashboard.jsx

# 4. Changes auto-reload on save (both backend & frontend)
```

#### Adding a New Backend Feature

```bash
# 1. Create new module in app/
# Example: app/services/recommendation_service.py

# 2. Add Pydantic schema in app/models/schemas.py
class RecommendationRequest(BaseModel):
    session_id: UUID
    ...

# 3. Add route in app/api/v1/
# in app/api/v1/recommendation_routes.py:
@router.post("/recommendations")
async def get_recommendations(req: RecommendationRequest):
    ...

# 4. Import in app/api/router.py to register route

# 5. Write tests
# tests/unit/test_recommendation_service.py
pytest tests/unit/test_recommendation_service.py -v

# 6. Test via API
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"session_id": "..."}'
```

#### Adding a New Frontend Component

```bash
# 1. Create component
# src/components/MyNewComponent.jsx
function MyNewComponent() {
  return <div>Hello</div>;
}
export default MyNewComponent;

# 2. Use it
# src/pages/SomePage.jsx
import MyNewComponent from "@/components/MyNewComponent";

# 3. Vite auto-reloads on save
```

---

## Common Tasks

### Create a Test Negotiation Session

```bash
# 1. Register & login
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "password123"
  }'

# Note JWT from response or login to get it
TOKEN="eyJ0e..."

# 2. Create negotiation session
curl -X POST http://localhost:8000/api/v1/negotiate/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product": {
      "product_id": "TEST-001",
      "product_name": "Test Widget",
      "base_price": 100.0,
      "cost_price": 60.0,
      "min_acceptable_price": 80.0,
      "max_loss_percentage": 0
    },
    "inventory": {
      "available_quantity": 100,
      "requested_quantity": 10,
      "inventory_pressure": "medium",
      "sales_frequency": "medium"
    },
    "strategy": {
      "mode": "MAX_PROFIT"
    }
  }'

# 3. Extract session_id from response
SESSION_ID="550e8400-e29b-41d4-a716-446655440000"

# 4. Send buyer's offer
curl -X POST http://localhost:8000/api/v1/negotiate/sessions/$SESSION_ID/turns \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "offer": {
      "offered_price": 75.0,
      "message": "Can you do $75?"
    }
  }'

# 5. Check response
# System responds with COUNTER at $XX.XX or ACCEPT/REJECT
```

### Check Database

```bash
# Connect to MySQL
mysql -h localhost -u root -p trademind

# View tables
SHOW TABLES;

# Check sessions
SELECT id, status, base_price, min_acceptable_price FROM chat_sessions LIMIT 5;

# Check products
SELECT id, name, base_price, cost_price FROM products;

# Exit
EXIT;
```

### Run Tests

```bash
cd backend

# All tests
pytest

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific test
pytest tests/unit/test_engine.py::test_session_creation -v

# With coverage
pytest --cov=app --cov-report=html
# View: htmlcov/index.html
```

### Check Logs

```bash
# Backend logs are printed to console
# Look for errors or warnings:

# Example error log:
# ERROR negotiation_engine session_error session_id='550e8400-...' error='min_price_violated'

# To add custom logging:
import structlog
logger = structlog.get_logger(__name__)
logger.info("my_event", user_id=123, status="success")
```

### Clear Cache

```bash
# Backend uses TTLCache (in-memory, auto-expires after 1 hour)
# To clear manually, restart server:

# Stop: Ctrl+C
# Restart: uvicorn app.main:app --reload
```

---

## Debugging Tips

### Backend

#### Issue: "ModuleNotFoundError: No module named 'app'"
```bash
# Ensure you're running from backend/ directory
cd backend

# Ensure .env exists with at least:
MYSQL_HOST=localhost
JWT_SECRET=any-value
```

#### Issue: "Connection to MySQL failed"
```bash
# Check MySQL is running
# Windows: Services > MySQL -> Start
# Linux: systemctl start mysql
# macOS: brew services start mysql

# Check credentials in .env
MYSQL_HOST=localhost  # or 127.0.0.1
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DB=trademind

# Test connection directly
mysql -h localhost -u root -p
```

#### Issue: LLM timeout or API key error
```bash
# System has fallbacks for missing LLM
# If you need LLM:
# 1. Get key from https://openrouter.ai/keys
# 2. Add to .env: OPENROUTER_API_KEY=sk-or-...
# 3. Restart server

# To test LLM specifically:
curl -X POST http://localhost:8000/api/v1/debug/llm-test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

#### Issue: "Constraint violated" during negotiation
```bash
# This is intentional! System protects seller constraints.
# Check:
# - Did counter_price drop below min_acceptable_price?
# - In MIN_LOSS mode: did loss_percent exceed max_loss_percent?

# To debug:
# Look at pricing agent output in logs:
# pricing_decision decision='REJECT' constraint_violated=true reason='below_min_price'
```

### Frontend

#### Issue: "API URL undefined" or CORS errors
```bash
# Create frontend/.env.local
VITE_API_URL=http://localhost:8000

# Restart: npm run dev
```

#### Issue: Translation not loading
```bash
# Check browser console (F12 > Console tab)
# Look for:
# - CORS errors: Backend CORS not configured
# - 401 Unauthorized: JWT missing or expired
# - 500 Internal: Backend error

# Frontend falls back to English if translation fails
```

#### Issue: Component not rendering
```bash
# Check browser console for React errors
# Likely causes:
# - Missing import
# - Null/undefined props
# - Event handler error

# Add console.log for debugging:
function MyComponent() {
  console.log("Component mounted", { props });
  return <div>...</div>;
}
```

### General Debugging

#### Enable Debug Logging

**Backend**:
```python
# In .env, set:
DEBUG=true
LOG_LEVEL=DEBUG

# Then logs will include much more detail
```

**Frontend**:
```javascript
// In src/lib/api.js:
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

// Add logging
api.interceptors.request.use((config) => {
  console.log("[API] Request:", config.method.toUpperCase(), config.url);
  return config;
});

api.interceptors.response.use((response) => {
  console.log("[API] Response:", response.status, response.data);
  return response;
});
```

#### Use Postman for API Testing

1. Open Postman
2. Create collection for your project
3. Create requests:
   ```
   POST http://localhost:8000/api/v1/negotiate/sessions
   Headers: Authorization: Bearer <your-jwt>
   Body: {...}
   ```
4. Save & reuse for testing

---

## Key Files to Know

### Backend

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI application factory + startup/shutdown |
| `app/core/engine.py` | **Core negotiation orchestration** (most important) |
| `app/agents/pricing_agent.py` | **Pricing decisions** (READ THIS) |
| `app/agents/conversation_agent.py` | LLM-based responses |
| `app/agents/context_agent.py` | Strategic analysis |
| `app/models/schemas.py` | **All request/response models** (data validation) |
| `app/models/enums.py` | Enumerations (NegotiationMode, OfferDecision, etc.) |
| `app/api/v1/` | Route handlers (endpoints) |
| `app/core/session.py` | Session CRUD + cache |
| `app/infrastructure/database/session.py` | MySQL connection pool |
| `app/infrastructure/llm/openai_client.py` | LLM provider integration |

**Start here**: `app/core/engine.py` → understand `process_negotiation_turn()`

### Frontend

| File | Purpose |
|---|---|
| `src/App.jsx` | Root component + routing |
| `src/pages/NegotiationDashboard.jsx` | **Live negotiation interface** (main UI) |
| `src/context/SessionContext.jsx` | Auth state provider |
| `src/context/I18nContext.jsx` | Translation provider |
| `src/lib/api.js` | **Axios API client** (all backend calls) |
| `src/pages/ProductCatalog.jsx` | Product management |
| `src/pages/BusinessAnalytics.jsx` | Analytics dashboard |

**Start here**: `src/lib/api.js` → understand API calls, then `src/pages/NegotiationDashboard.jsx` → see UI flow

---

## API Testing

### Postman Collection (Quick Setup)

```bash
# 1. Export this as Postman collection JSON:

curl --location 'http://localhost:8000/docs' \
  --header 'Accept: application/json'
# Navigate to Swagger UI and download OpenAPI spec

# 2. Import into Postman
# Postman > Collections > Import > Paste OpenAPI spec

# 3. Set variables in Postman
# Variables tab:
# - {{BASE_URL}}: http://localhost:8000
# - {{TOKEN}}: <your-jwt-token>
# - {{SESSION_ID}}: <session-uuid>

# 4. Use in requests
# GET {{BASE_URL}}/api/v1/negotiate/sessions/{{SESSION_ID}}
# Header: Authorization: Bearer {{TOKEN}}
```

### cURL Examples

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "pass123",
    "full_name": "John Doe"
  }'

# 2. Login (get JWT)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "pass123"
  }'
# Response contains: { "access_token": "eyJ0..." }

# 3. Use JWT in subsequent requests
TOKEN="eyJ0eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer $TOKEN"
```

---

## Database Queries

### Useful SQL Commands

```sql
-- Login
mysql -h localhost -u root -p trademind

-- View all sessions
SELECT id, status, base_price, min_acceptable_price, final_decision
FROM chat_sessions
LIMIT 10;

-- Sessions for specific user
SELECT id, status, created_at
FROM chat_sessions
WHERE user_id = 1
ORDER BY created_at DESC;

-- Products with stats
SELECT name, base_price, cost_price, total_sessions, accepted_deals
FROM products
WHERE user_id = 1;

-- Messages in a session
SELECT round_number, user_message, bot_reply, decision
FROM chat_messages
WHERE session_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY round_number;

-- API keys (masked)
SELECT id, user_id, CONCAT('tm_', SUBSTR(api_key, -4)) as masked_key, is_active
FROM api_keys;

-- Clear old sessions (older than 7 days)
DELETE FROM chat_sessions
WHERE created_at < DATE_SUB(NOW(), INTERVAL 7 DAY)
AND status != 'active';

-- Check database size
SELECT
  table_name,
  ROUND((data_length + index_length) / 1024 / 1024, 2) AS size_mb
FROM information_schema.tables
WHERE table_schema = 'trademind'
ORDER BY size_mb DESC;
```

---

## Next Steps

1. **Read the full documentation**:
   - [README.md](README.md) — full project overview
   - [ARCHITECTURE.md](ARCHITECTURE.md) — deep dive into design

2. **Explore the code**:
   - Start with `backend/app/core/engine.py`
   - Then read `backend/app/agents/pricing_agent.py` (core logic)

3. **Run a test negotiation** (see Common Tasks section)

4. **Write a test**:
   ```bash
   # Create tests/unit/test_my_feature.py
   # Run: pytest tests/unit/test_my_feature.py -v
   ```

5. **Create a feature branch and submit a PR** when ready

---

## Support

- 📧 Email: support@trademind.ai
- 🐛 Issues: GitHub Issues tab
- 📚 Docs: README.md + ARCHITECTURE.md
- 💬 Chat: GitHub Discussions

---

**Happy coding!** 🚀

