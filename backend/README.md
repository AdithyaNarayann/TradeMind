# Negotiation Engine Backend

A profit-aware negotiation engine API built with Python and FastAPI.

## Quick Start

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run the server
python -m app.server
```

The API will be available at `http://localhost:8000`

## API Documentation

When running in development mode, access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/negotiate/sessions` | Create negotiation session |
| GET | `/api/v1/negotiate/sessions/{id}` | Get session status |
| DELETE | `/api/v1/negotiate/sessions/{id}` | End session early |
| POST | `/api/v1/negotiate/sessions/{id}/turns` | Submit buyer offer |
| GET | `/api/v1/negotiate/sessions/{id}/analytics` | Get session analytics |
| GET | `/api/v1/negotiate/health` | Health check |

## Example Usage

### Create a Session

```bash
curl -X POST http://localhost:8000/api/v1/negotiate/sessions \
  -H "Content-Type: application/json" \
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

### Submit a Buyer Offer

```bash
curl -X POST http://localhost:8000/api/v1/negotiate/sessions/{session_id}/turns \
  -H "Content-Type: application/json" \
  -d '{
    "offered_price": 85.00,
    "message": "Can you do better?"
  }'
```

## Architecture

```
src/
├── agents/
│   ├── context_agent.py    # Strategic posture analysis
│   ├── pricing_agent.py    # Deterministic pricing decisions
│   └── conversation_agent.py   # Natural language generation
├── api/
│   ├── middleware/
│   │   ├── rate_limiter.py     # Rate limiting
│   │   └── error_handler.py    # Error handling
│   └── routes.py           # API endpoints
├── config/
│   └── settings.py         # Environment configuration
├── core/
│   ├── engine.py           # Main orchestration layer
│   └── session.py          # Session management
├── models/
│   ├── enums.py            # Type definitions
│   └── schemas.py          # Pydantic models
├── app.py                  # FastAPI application
└── server.py               # Entry point
```

## Operating Modes

### MAX_PROFIT Mode
- Conservative concessions
- Early firmness in price
- Walk away if margins degrade
- Prefer fewer negotiation rounds

### MIN_LOSS Mode
- Flexible concessions
- Break-even prioritized
- Controlled loss acceptable
- Faster deal closure

## Rate Limits

| Endpoint Type | Limit |
|--------------|-------|
| Create Session | 20/minute |
| Submit Offer | 30/minute |
| Get Session | 60/minute |
| Analytics | 30/minute |
| Health Check | 120/minute |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| ENV | development | Environment mode |
| DEBUG | true | Enable debug mode |
| HOST | 0.0.0.0 | Server host |
| PORT | 8000 | Server port |
| RATE_LIMIT_PER_MINUTE | 60 | Default rate limit |
| SESSION_TTL_SECONDS | 3600 | Session expiration |

## License

MIT
