# TradeMind Architecture Documentation

**Version**: 1.0.0  
**Last Updated**: March 5, 2026  
**Status**: Complete & Production-Ready (with noted enhancements pending)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Philosophy](#core-philosophy)
3. [Multi-Agent Architecture](#multi-agent-architecture)
4. [Data Flow](#data-flow)
5. [Technology Stack](#technology-stack)
6. [Directory Structure](#directory-structure)
7. [Key Design Patterns](#key-design-patterns)
8. [Security Architecture](#security-architecture)
9. [Performance & Scalability](#performance--scalability)
10. [Testing Strategy](#testing-strategy)

---

## System Overview

**TradeMind** is a **business decision engine** for automated, profit-constrained negotiations. It combines:

- **Deterministic Pricing Logic**: Rule-based, auditable decisions (no AI randomness)
- **LLM Intelligence**: Natural language generation and contextual analysis
- **Safety Guardrails**: Hard seller constraints that cannot be violated
- **Session Management**: Multi-round negotiation lifecycle with state persistence

### Key Metrics

| Metric | Value | Notes |
|---|---|---|
| Max Concurrent Sessions | 10K | In-memory cache (TTLCache) |
| Session TTL | 1 hour | Configurable in `.env` |
| Max Negotiation Rounds | 5–20 | Seller-configurable |
| API Rate Limit | 60/min, 1000/hour | Per-endpoint limits vary |
| LLM Timeout | 10 seconds | Fallback to heuristics if exceeded |
| Supported Languages | 50+ | Via Gemini Translate API |

---

## Core Philosophy

The system adheres to strict design principles:

| Principle | Implementation |
|---|---|
| **Profit > Deal** | MIN_PROFIT mode protects margins; can walk away |
| **Constraints > AI** | Hard rules override LLM suggestions; validator layer |
| **Rules > Models** | Pricing decisions use deterministic engines, not LLMs |
| **Predictability > Creativity** | Identical inputs produce identical pricing decisions |
| **Safety > Autonomy** | Defaults to seller protection when ambiguous |

**Non-Negotiable Constraint**: The system MUST NEVER:
- Invent prices or discounts
- Violate seller-defined floors (min_acceptable_price, max_loss %)
- Make numeric decisions based solely on LLM output
- Agree to contradictory terms

---

## Multi-Agent Architecture

### Agent Roles & Responsibilities

```
┌────────────────────────────────────────────────────────┐
│           Negotiation Orchestration Engine              │
│    (Session lifecycle, turn routing, constraint check)  │
├──────────────────┬─────────────────┬──────────────────┤
│                  │                 │                  │
│  1. Context      │  2. Pricing     │  3. Conversation │
│     Analysis     │     Strategy    │     Generation   │
│     Agent        │     Agent       │     Agent        │
│                  │                 │                  │
│  Input: Buyer    │  Input: Offer,  │  Input: Decision,│
│  intent, history │  costs, budget  │  context, history│
│                  │                 │                  │
│  Output: Strategic│  Output: Price  │  Output: Natural │
│  posture,        │  decision,      │  language,       │
│  aggressiveness  │  accept/counter │  explanation     │
│                  │                 │                  │
│  Tech: LLM +     │  Tech: Pure     │  Tech: LLM +     │
│  heuristics      │  deterministic  │  template        │
│                  │                 │                  │
│  Validation:     │  Validation:    │  Validation:     │
│  Score reasoned  │  Price > 0,     │  Price not       │
│  using context   │  floor enforced │  invented,       │
│  factors         │                 │  matches decision│
└──────────────────┴─────────────────┴──────────────────┘
```

### Agent Lifecycle

#### 1. Context Analysis Agent

**Purpose**: Analyze negotiation posture and determine aggressiveness.

**Inputs**:
```python
{
  "negotiation_mode": "MAX_PROFIT",          # Seller's strategy
  "inventory_pressure": "MEDIUM",            # Stock urgency
  "sales_frequency": "LOW",                  # How often it sells
  "urgency_level": "HIGH",                   # Seller's time pressure
  "relationship_priority": "LOW",            # Buyer value
  "round_number": 2,                         # Current round (1–max)
  "negotiation_history": [...]               # Previous offers
}
```

**Processing**:
1. LLM analyzes context → scores strategic posture (-1 to +1)
2. If LLM unavailable → heuristic fallback (rule-based rubric)
3. Compute aggressiveness: CONSERVATIVE / MODERATE / AGGRESSIVE
4. Determine concession budget (margin to give)

**Outputs**:
```python
{
  "strategic_posture": 0.6,                  # -1 to +1 (willing to negotiate)
  "aggressiveness": "MODERATE",
  "concession_budget": Decimal("15.00"),     # Max margin to give
  "risk_tolerance": 0.5,                     # 0–1
  "acceptance_threshold": Decimal("85.00")   # Minimum acceptable price
}
```

**Key Logic**:
- **Dynamic Acceptance**: As rounds increase, acceptance threshold decreases (simulate negotiation pressure)
- **Mode-Aware**: MAX_PROFIT is conservative; MIN_LOSS is flexible
- **Inventory-Aware**: High pressure → lower thresholds
- **Relationship-Aware**: VIP buyers get better terms

---

#### 2. Pricing Strategy Agent

**Purpose**: Compute optimal counter-offers with hard constraint enforcement.

**Inputs**:
```python
{
  "offered_price": Decimal("75.00"),         # Buyer's offer
  "base_price": Decimal("100.00"),           # Listed price
  "cost_price": Decimal("60.00"),            # Seller's cost
  "min_acceptable_price": Decimal("80.00"),  # Hard floor
  "max_loss_percent": Decimal("0"),          # Loss tolerance
  "negotiation_mode": "MAX_PROFIT",
  "strategic_posture": 0.6,                  # From Context Agent
  "round_number": 2,
  "max_rounds": 5
}
```

**Processing**:
1. **Validate Input**: Ensure offered_price > 0, respects hierarchy
2. **Compute Metrics**:
   - Profit Margin = (offered_price - cost_price) / offered_price × 100
   - Margin Remaining = profit_margin - min_margin_threshold
3. **Decision Logic** (deterministic, no LLM):
   - If offered_price ≥ base_price → **ACCEPT** (win!)
   - If profit_margin < min_threshold → **REJECT** or **COUNTER** (depends on round)
   - Else → compute optimal counter-offer
4. **Counter-Offer Calculation**:
   - Start from acceptance threshold
   - Move toward buyer's offer based on round number
   - Ensure final price ≥ min_acceptable_price
5. **Constraint Enforcement**:
   - Check min_acceptable_price floor
   - In MIN_LOSS mode: check max_loss_percent
   - If either would be violated → REJECT
6. **Fallback**: If off-path scenario → use template response

**Outputs**:
```python
{
  "decision": "COUNTER",                     # ACCEPT / COUNTER / REJECT
  "counter_price": Decimal("82.50"),         # If counter
  "profit_margin": Decimal("27.5"),          # %
  "margin_remaining": Decimal("2.5"),        # After this offer
  "constraint_violated": False,              # Flag if rules broken
  "justification": "Move toward agreement while protecting margin",
  "fallback_used": False                     # Heuristic vs LLM
}
```

**Safety Guarantees**:
- ✓ `counter_price >= min_acceptable_price` (hard floor)
- ✓ No invented prices (all computed deterministically)
- ✓ Reproducible (same inputs → same output)
- ✓ Auditable (justification always provided)
- ✓ Profit margin always explainable

**Key Logic**:
- **Progressive Flexibility**: As rounds increase, acceptance threshold decreases
- **Mode-Aware**: MAX_PROFIT favors high margins; MIN_LOSS accepts lower margins
- **Round-Based Strategy**: Early rounds are harder; late rounds become flexible
- **Constraint Precedence**: Min price > profit margin > deal closure

---

#### 3. Conversation Agent

**Purpose**: Generate human-like responses explaining pricing decisions.

**Inputs**:
```python
{
  "buyer_message": "Can you do $75?",
  "pricing_decision": {
    "decision": "COUNTER",
    "counter_price": Decimal("82.50"),
    "justification": "..."
  },
  "context": {
    "product_name": "Premium Widget",
    "round_number": 2,
    "negotiation_history": [...]
  },
  "strategic_posture": 0.6
}
```

**Processing**:
1. **LLM Generation** (with prompt template):
   - Generate response explaining counter-offer
   - Reference buyer's original message
   - Justify pricing decision without inventing reasons
   - Match tone to strategic posture
2. **LLM Output Validation**:
   - Extract prices and confirm none invented
   - Check response doesn't contradict decision
   - Verify forbidden phrases not used
   - If validation fails → fallback to template
3. **Fallback Templates** (if LLM unavailable):
   - Generic response matching decision type
   - Pre-written templates for common scenarios

**Outputs**:
```python
{
  "message": "Thanks for the offer! We can meet you at $82.50 per unit. This gives us fair market coverage while ensuring product quality standards.",
  "validation_passed": True,
  "fallback_used": False
}
```

**Tone Modulation**:
- **CONSERVATIVE**: Formal, structured, detail-oriented
- **MODERATE**: Balanced, conversational, flexible
- **AGGRESSIVE**: Friendly, collaborative, open to negotiation

**Safety Checks**:
- ✓ No invented prices (regex check)
- ✓ No contradiction with actual decision
- ✓ No forbidden phrases ("guaranteed", "lowest price ever", etc.)
- ✓ Proper grammar and professionalism
- ✓ Fallback to template if validation fails

---

### Agent Coordination Flow

```
Buyer Message
    │
    ▼
┌─────────────────────────────────────┐
│  Extract Offer & Intent             │ (Regex + LLM fallback)
│  Convert "Can you do $75?" → 75.00  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Context Analysis Agent                                     │
│  Input: Market, history, mode, urgency → Strategic posture  │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Pricing Strategy Agent (DETERMINISTIC)                     │
│  Decision: ACCEPT / COUNTER / REJECT                        │
│  Price: computed & validated (never invented)               │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Conversation Agent (LLM + Validation)                      │
│  Input: Decision, justification → Natural language response │
│  Validation: No invented prices, matches decision           │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  LLM Output Validation (Price-Check Layer)                  │
│  Confirm: No price invention, no contradiction              │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
          Response to Buyer
```

---

## Data Flow

### Session Lifecycle

```
1. CREATE SESSION
   ├─ Seller defines:
   │  ├─ Product (name, costs, pricing)
   │  ├─ Inventory (available qty, pressure)
   │  └─ Strategy (mode, urgency, max rounds)
   └─ System creates session ID, initializes state
   
2. PRESENT INITIAL OFFER
   ├─ System generates opening price
   │  (Context Agent → Pricing Agent → Conversation Agent)
   └─ Initial message sent to buyer
   
3. NEGOTIATE (Multi-Round Loop)
   ├─ Round N:
   │  ├─ Buyer submits counter-offer / message
   │  ├─ Extract price from message
   │  ├─ Route through agents
   │  ├─ Compute decision (ACCEPT / COUNTER / REJECT)
   │  ├─ Generate response
   │  └─ Send to buyer
   │
   ├─ Check termination conditions:
   │  ├─ Rounds exceeded? → EXPIRED
   │  ├─ Buyer accepted? → ACCEPTED
   │  ├─ Seller rejected? → REJECTED
   │  └─ Constraint violated? → WALKED AWAY
   │
   └─ Repeat until termination
   
4. CLOSE SESSION
   ├─ Final price recorded
   ├─ Profit/loss calculated
   ├─ Session marked as closed
   └─ Notifications sent (email, dashboard)
```

### Message Extraction Flow (Free-Text Intelligence)

```
Buyer: "That seems expensive. Can you do $80?"
│
├─ LLM Extraction
│  └─ Parse message → offer price
│     Input to LLM: "Convert to structured format"
│     Output: {"offered_price": 80, "message": "..."}
│
├─ Fallback (Regex Pattern Matching)
│  └─ If LLM fails, regex patterns for:
│     ├─ "$X" → extract X
│     ├─ "X per unit" → extract X
│     ├─ "around X" → extract X
│     └─ If no pattern → ask for clarification
│
└─ Validation
   └─ Ensure 0 < offered_price < 99999
```

---

## Technology Stack

### Backend Layers

```
┌──────────────────────────────────────────────────────────┐
│                     API Layer                             │
│  (FastAPI, CORS, Rate Limiting, Request Validation)      │
├──────────────────────────────────────────────────────────┤
│                   Business Logic Layer                    │
│  (Negotiation Engine, Agents, Analytics)                │
├──────────────────────────────────────────────────────────┤
│                 Infrastructure Layer                      │
│  (Database, LLM, Email, Cache, Session)                 │
├──────────────────────────────────────────────────────────┤
│                   Core Services                           │
│  (Config, Logging, Security, Error Handling)            │
└──────────────────────────────────────────────────────────┘
```

### Technology Choices & Rationale

| Component | Technology | Why |
|---|---|---|
| **Web Framework** | FastAPI | Async-native, Pydantic validation, auto OpenAPI docs |
| **Async Runtime** | asyncio + Uvicorn | Handle concurrent sessions, non-blocking I/O |
| **Database** | MySQL 8+ | Relational, ACID transactions, wide adoption |
| **ORM** | Raw SQL + aiomysql | Fine-grained control, async pooling, simplicity |
| **LLM Provider** | OpenRouter | Unified API (Gemini, GPT-4, Claude), fallback capable |
| **Authentication** | PyJWT + bcrypt | Stateless JWT, bcrypt hashing, no session server |
| **Session Cache** | cachetools.TTLCache | In-memory, TTL auto-purge, fast access |
| **Rate Limiting** | SlowAPI | FastAPI-integrated, per-endpoint granularity |
| **Frontend** | React 19.2 | Component-based, Vite bundling, extensive ecosystem |
| **Styling** | Tailwind CSS | Utility-first, responsive, theme customization |
| **Reverse Proxy** | Nginx | Load balancing, static file serving, caching |

---

## Directory Structure

### Backend Deep Dive

```
backend/app/
├── main.py
│   └─ create_app() → FastAPI instance + routes
│
├── server.py
│   └─ Uvicorn entry point: uvicorn app.main:app
│
├── core/
│   ├── config.py → Settings class, environment loading
│   ├── engine.py → NegotiationEngine orchestration
│   ├── session.py → SessionManager (CRUD + cache)
│   └── logging.py → structlog configuration
│
├── agents/
│   ├── context_agent.py → ContextAnalysisAgent
│   ├── pricing_agent.py → PricingStrategyAgent
│   └── conversation_agent.py → ConversationAgent
│
├── models/
│   ├── schemas.py → Pydantic models (request/response)
│   └── enums.py → NegotiationMode, OfferDecision, etc.
│
├── api/
│   ├── router.py → Top-level API router
│   ├── __init__.py → Exports limiter, middleware, handlers
│   ├── middleware/ → CORS, logging, security headers
│   └── v1/ → Versioned endpoints
│       ├── auth_routes.py
│       ├── negotiate_routes.py
│       ├── product_routes.py
│       ├── chat_routes.py
│       ├── analytics_routes.py
│       └── api_key_routes.py
│
├── services/
│   ├── email_service.py → SMTP notifications
│   └── llm_validator.py → Price-checking validation
│
├── infrastructure/
│   ├── database/
│   │   ├── session.py → aiomysql pool, close_pool()
│   │   ├── queries.py → SQL CRUD helpers
│   │   └── migrations/ → SQL scripts
│   │
│   ├── llm/
│   │   ├── openai_client.py → OpenRouter API calls
│   │   └── prompt_templates.py → Jinja2 templates
│   │
│   ├── external/
│   │   └── email_providers.py → SMTP abstractions
│   │
│   └── cache/
│       └── session_cache.py → TTLCache management
│
├── buisness anlytics/
│   ├── main.py
│   ├── calculations/
│   ├── insights/
│   ├── competitive_intelligence/ → Isolated plugin
│   └── schemas/
│
└── tests/
    ├── conftest.py → pytest fixtures
    ├── unit/ → Agent tests, validator tests
    └── integration/ → End-to-end session tests
```

### Frontend Structure

```
frontend/src/
├── App.jsx → Root component + routing
│
├── pages/
│   ├── Landing.jsx → Marketing homepage
│   ├── Login.jsx / Register.jsx → Auth
│   ├── NegotiationDashboard.jsx → Live sessions
│   ├── ProductCatalog.jsx → CRUD products
│   ├── BusinessAnalytics.jsx → Analytics dashboard
│   ├── ApiAccess.jsx → API key management
│   ├── EmailSettings.jsx → Email config
│   └── ApiReference.jsx → API documentation
│
├── components/
│   ├── Layout.jsx / Navbar.jsx / Footer.jsx
│   ├── ProtectedRoute.jsx → Auth guard
│   ├── NeoButton.jsx / NeoCard.jsx → Custom components
│   ├── LanguageModal.jsx / LanguageSwitcher.jsx
│   ├── AlertBanner.jsx
│   ├── SourceNetwork.jsx → 3D visualization
│   ├── TranslationLoadingOverlay.jsx
│   └── ui/ → shadcn/ui primitives
│
├── context/
│   ├── I18nContext.jsx → Translation provider
│   └── SessionContext.jsx → Auth provider
│
├── lib/
│   ├── api.js → Axios client + auth headers
│   ├── encryption.js → TweetNaCl for PII
│   ├── geminiTranslate.js → Translation service
│   ├── productStore.js → Client-side state
│   ├── utils.js → Helpers
│   └── i18n/ → Static translations (JSON)
│
├── App.jsx → Root + React Router
├── main.jsx → Vite entry
└── index.css → Global styles
```

---

## Key Design Patterns

### Pattern 1: Triple-Fallback Resilience

Every critical component has three-tier fallback:

```
┌─────────────────────────────┐
│  Tier 1: LLM (Fast & Smart) │
└──────────────┬──────────────┘
               │
          (If fails)
               ▼
┌─────────────────────────────┐
│ Tier 2: Heuristic (Reliable)│
└──────────────┬──────────────┘
               │
          (If fails)
               ▼
┌──────────────────────────────┐
│ Tier 3: Template (Always Works)
└──────────────────────────────┘
```

Example: Price extraction:
1. **Try LLM**: Send message to Claude → extract price
2. **Fallback to Regex**: Match patterns like "$X", "X per unit"
3. **Fallback to Template**: "Please specify your offering price"

### Pattern 2: Constraint-First Architecture

```
Decision Logic:
1. Check hard constraints first
   ├─ If violated → REJECT immediately
   └─ If safe → compute offer
2. Compute optimal offer
   ├─ Start from max acceptable
   ├─ Move toward buyer's position
   └─ Ensure never drops below min
3. Validate output
   └─ Confirm still respects constraints
```

### Pattern 3: Separation of Concerns

```
Agent Responsibilities:
├─ Context Agent: ONLY strategic analysis (no pricing)
├─ Pricing Agent: ONLY numeric decisions (no language)
└─ Conversation Agent: ONLY language generation (no pricing)

Clear Boundary:
├─ Input validation at layer boundary
├─ No agent calls other agent directly
├─ All communication through Engine
└─ Allows independent testing & swapping
```

### Pattern 4: Validation Sandwich

```
API Request
    ↓
┌─────────────────────────┐
│ Pydantic Input Validation
└───────────┬─────────────┘
            ↓
    Business Logic
            ↓
┌──────────────────────────┐
│ Pydantic Output Response
└───────────┬──────────────┘
            ↓
┌──────────────────────────┐
│ HTTP Response (JSON)
└──────────────────────────┘
```

---

## Security Architecture

### Authentication & Authorization

```
┌───────────────────────────────────────────────────────────┐
│  Request with Auth Header                                  │
│  Authorization: Bearer <jwt-or-api-key>                   │
└─────────────────┬───────────────────────────────────────┘
                  │
        ┌─────────▼─────────┐
        │  Extract Token    │
        └────────┬──────────┘
                 │
        ┌────────▼────────────────────────────┐
        │ Is JWT Format (has ".")? → JWT Flow  │
        │ Is "tm_" Prefix? → API Key Flow      │
        └────────┬────────────────────────────┘
                 │
        ┌────────▼──────────────────┐
        │  JWT Flow                 │
        ├──────────────────────────┤
        │ 1. Verify signature with  │
        │    JWT_SECRET             │
        │ 2. Check expiration       │
        │ 3. Extract user_id        │
        └────────┬──────────────────┘
                 │
        ┌────────▼──────────────────┐
        │  API Key Flow             │
        ├──────────────────────────┤
        │ 1. Query api_keys table   │
        │ 2. Verify key matches     │
        │ 3. Check is_active        │
        │ 4. Extract user_id        │
        └────────┬──────────────────┘
                 │
        ┌────────▼──────────────────┐
        │  Authorized?              │
        │  ├─ Yes → Proceed         │
        │  └─ No → 401 Unauthorized │
        └──────────────────────────┘
```

### Rate Limiting

```
Endpoint: POST /api/v1/negotiate/sessions
Rate Limit: 20 requests per minute

Client 1 (20 reqs) → ✓ Pass through
Client 2 (25 reqs) → ✗ Exceed limit → 429 Too Many Requests
```

### Data Protection

| Data | Protection |
|---|---|
| Passwords | bcrypt hashing (salt rounds: 12) |
| JWT Secrets | Environment variable, never logged |
| SMTP Credentials | Encrypted at rest in database |
| API Keys | Masked in responses (show only last 4 chars) |
| PII (emails, phones) | Optional client-side encryption via TweetNaCl |

---

## Performance & Scalability

### Current Bottlenecks

| Bottleneck | Cause | Solution (Future) |
|---|---|---|
| Session Memory | cachetools.TTLCache (limited by RAM) | Redis distributed cache |
| LLM Latency | Network round-trip (10s timeout) | Local LLM, caching, batch |
| Database Queries | Single MySQL instance | Read replicas, connection pool tuning |
| Async Tasks | Blocking SMTP calls | Celery + RabbitMQ queue |

### Optimization Strategies

**Current (Immediate)**:
- Pydantic model caching (parsed schemas)
- Structured logging (avoid string interpolation)
- Connection pooling (aiomysql with 10 concurrent connections)
- Rate limiting per user (prevent abuse)

**Planned (Phase 2)**:
- Redis session cache (replace TTLCache)
- Database indexing (user_id, session_id, created_at)
- Async task queue (Celery for email, reports)
- CDN for static assets (Vercel handles this)

**Planned (Phase 3)**:
- Kubernetes horizontal autoscaling
- Load balancing with Nginx
- Database read replicas
- Message queue (RabbitMQ)

---

## Testing Strategy

### Test Pyramid

```
          ┌──▲──┐
          │      │         End-to-End (Few)
          │      │         - Full CI/CD pipeline
          │      │         - Production simulation
          │──────│
          │      │         Integration (Some)
          │      │         - Session creation → closure
          │      │         - Agent coordination
          │      │         - Database CRUD
          │──────│
          │      │
          │      │         Unit (Many)
          │      │         - Agent pricing logic
          │      │         - Validation rules
          │      │         - Email templates
          └──────┘
```

### Test Categories

#### Unit Tests (`tests/unit/`)
- **Agents**: Test pricing logic in isolation
- **Models**: Validate Pydantic constraints
- **Services**: Email templates, encryption
- **Validators**: Price-check validation

#### Integration Tests (`tests/integration/`)
- **Session Lifecycle**: Create → negotiate → close
- **Agent Coordination**: Context → Pricing → Conversation
- **Database**: CRUD operations, transactions
- **API Endpoints**: Full request → response cycle

#### End-to-End Tests (`tests/e2e/`)
- **Negotiation Flow**: Multiple rounds, deal closure
- **Authentication**: JWT + API key flows
- **Rate Limiting**: Exceed limits → 429 responses
- **Error Handling**: Invalid inputs → proper errors

### Running Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific file
pytest tests/unit/test_pricing_agent.py -v

# Run integration tests only
pytest tests/integration/ -v

# Run with print statements (debugging)
pytest -s tests/unit/test_engine.py::test_session_creation
```

---

## Deployment Architecture

### Development

```
Frontend: http://localhost:5173 (Vite dev server)
Backend: http://localhost:8000 (Uvicorn)
Database: localhost:3306 (MySQL)
```

### Production (Recommended)

```
┌──────────────────────────────────────────────┐
│  Domain: trademind.ai                        │
├──────────────────┬───────────────────────────┤
│                  │                           │
│  Frontend        │  Backend                  │
│  (Vercel)        │  (Railway / Render)       │
│                  │                           │
│  nodejs build    │  Python container        │
│  & deployment    │  & FastAPI service       │
│                  │                           │
└──────────┬───────┴────────────┬──────────────┘
           │                    │
           │     Nginx          │
           │  (Load Balancer)   │
           │                    │
           └────────┬───────────┘
                    │
           ┌────────▼────────┐
           │  MySQL          │
           │  (Managed DB)   │
           │  e.g. AWS RDS   │
           └─────────────────┘
```

### Deployment Steps

1. **Backend**:
   ```bash
   # Push to Railway/Render git
   git push railway main
   # Automatic: Build Docker image, run migrations, start service
   ```

2. **Frontend**:
   ```bash
   # Push to GitHub, Vercel auto-deploys
   git push origin main
   # Automatic: npm run build, upload to CDN, domain routing
   ```

3. **Database**:
   ```bash
   # Use managed service (AWS RDS, DigitalOcean Managed DB)
   # Run migrations once: SQL script execution
   ```

---

## Monitoring & Observability

### Logging Strategy

**Backend** (structlog):
```python
logger.info("session_created", session_id="...", user_id=123, mode="MAX_PROFIT")
logger.warning("constraint_approaching", margin_remaining=Decimal("5"))
logger.error("llm_timeout", fallback="heuristic")
```

**Frontend** (console.log + error tracking):
```javascript
console.log("[I18n] Translation loaded", { lang: "es", phrases: 1000 });
console.error("[API] Fetch error", { endpoint: "/api/v1/products", status: 500 });
```

### Metrics to Monitor

| Metric | Tool | Alert Threshold |
|---|---|---|
| API Response Time (p95) | Datadog / New Relic | > 500ms |
| LLM Fallback Rate | structlog | > 5% |
| Database Connection Pool | sqlalchemy metrics | > 80% utilized |
| Memory Usage | Kubernetes / Heroku metrics | > 85% |
| Unhandled Exceptions | Sentry | Any |
| Email Queue Backlog | Celery monitoring | > 100 pending |

---

## Conclusion

TradeMind's architecture prioritizes **safety**, **auditability**, and **scalability**. The multi-agent system ensures clear separation of concerns, while the constraint-first approach guarantees seller protection. The triple-fallback resilience pattern ensures the system operates gracefully even when external services (LLM, SMTP) are unavailable.

For questions or contributions, refer to [README.md](README.md) and the main repository.

