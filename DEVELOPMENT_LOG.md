# TradeMind — Development Log

> **Project**: TradeMind Negotiation Platform  
> **Date**: February 8, 2026  
> **Stack**: React 19 + Vite + Tailwind (Frontend) · FastAPI + MySQL (Backend) · Neo-Brutalist UI  

---

## Table of Contents

1. [Authority.jsx — Syntax & Logic Fixes](#1-authorityjsx--syntax--logic-fixes)
2. [Product Analytics Popup](#2-product-analytics-popup)
3. [API Access Page & Key Generator](#3-api-access-page--key-generator)
4. [API Key Authentication](#4-api-key-authentication)
5. [UI Polish — Code Snippets Redesign](#5-ui-polish--code-snippets-redesign)
6. [Files Modified / Created](#6-files-modified--created)
7. [Database Schema](#7-database-schema)
8. [API Endpoints Reference](#8-api-endpoints-reference)
9. [Design System](#9-design-system)

---

## 1. Authority.jsx — Syntax & Logic Fixes

### 1.1 Syntax Error Fix
- **Problem**: Orphaned JSX fragment around line 526 caused a Vite SWC compilation error.
- **Fix**: Removed the dangling fragment, restoring valid JSX structure.

### 1.2 Logic Audit & Cleanup
A full audit of the 1,325-line `Authority.jsx` file uncovered several issues:

| Issue | Fix |
|---|---|
| `handleCompetitiveAnalysis` hardcoded `category: 'General'` | Changed to use `product.category` dynamically |
| 12 unused icon imports + `useNavigate` | Removed all unused imports |
| 4 unwanted Performance Signal inputs (Chat Sessions, Orders, Units Sold, Returns) | Removed from the form |
| Dead state: `DEFAULT_PERFORMANCE`, `performance` state, `handlePerformanceChange` | Removed entirely |
| 3rd card misleadingly named "Performance Signals" | Renamed to **"Negotiation Settings"** |

---

## 2. Product Analytics Popup

### 2.1 Frontend — ProductCatalog.jsx
- Added a **"Show Analytics"** button on each product card.
- Built an inline expandable analytics panel, then converted it into a **popup modal** for a cleaner UX.

### 2.2 Backend — Product Stats Endpoint
Created `GET /api/v1/products/{id}/stats` in `product_routes.py` that queries the `chat_sessions` table for real aggregated data.

### 2.3 Store — productStore.js
Added `getProductStats(productId)` function to call the new endpoint.

### 2.4 Modal Content
The analytics modal displays:

- **6 Key Metrics**: Total sessions, accepted deals, rejected deals, active sessions, avg deal price, total revenue
- **Price Positioning**: Visual bar showing average deal price relative to base price
- **Negotiation Room**: Average rounds per session, average buyer/seller offers
- **Deal Funnel**: Accepted / Rejected / Active breakdown
- **Revenue Section**: Total revenue from completed deals
- **Recent Sessions Table**: Last 5 sessions with status, price, and date

---

## 3. API Access Page & Key Generator

### 3.1 New Page — `ApiAccess.jsx`
A full-featured API management page accessible at `/api-access`, containing:

#### Generate API Key
- Label input + generate button
- Keys are prefixed `tm_` followed by 48-character hex token
- One-click copy to clipboard

#### API Keys List
- Displays all active keys with label, creation date, last used timestamp
- Masked key display with reveal toggle (Eye/EyeOff)
- Revoke button per key

#### API Endpoint Reference (top section)
- Responsive 4-column grid of all available endpoints
- Color-coded HTTP method badges (GET = teal, POST = orange, PUT = navy)
- Shows path and description for each endpoint

#### Quick Start Guide (bottom section)
- Switchable code snippets for **Python**, **JavaScript**, and **TypeScript**
- Dark terminal-style code block with line numbers
- Basic syntax highlighting (keywords in orange, comments in teal)
- Active API key automatically injected into snippets
- Copy Code button
- Active key indicator bar at the bottom

### 3.2 Backend — `apikey_routes.py`
New router with three endpoints:

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/api-keys` | Generate a new API key |
| `GET` | `/api/v1/api-keys` | List all keys for current user |
| `DELETE` | `/api/v1/api-keys/{id}` | Revoke (deactivate) a key |

Key generation uses `secrets.token_hex(24)` with `tm_` prefix.

### 3.3 Routing & Navigation
- **App.jsx**: Added `<Route path="/api-access" />` wrapped in `<ProtectedRoute>`
- **Navbar.jsx**: Added `Key` icon + "API" nav link pointing to `/api-access`

---

## 4. API Key Authentication

### Problem
`get_current_user` in `auth_routes.py` only understood JWT tokens. API keys prefixed with `tm_` returned 401 Unauthorized on all endpoints.

### Solution
Updated `get_current_user` to detect `tm_` prefix in the `Authorization: Bearer <token>` header:

```python
if token.startswith("tm_"):
    # Query api_keys table joined with users
    # Update last_used_at timestamp
    # Return user dict
else:
    # Decode as JWT (existing logic)
```

### Verification
Tested with key `tm_b0cff3346b3557ca6622372755afe0a15ae2c905169baf1e` — all endpoints returned 200:
- `GET /api/v1/auth/me` ✅
- `GET /api/v1/products` ✅
- `GET /api/v1/chat-sessions` ✅
- `GET /api/v1/api-keys` ✅

---

## 5. UI Polish — Code Snippets Redesign

### 5.1 Layout Restructure
The original code snippets section used a cramped 3+2 column grid. Redesigned to:

- **Top row**: Generate Key + Keys List side by side (2-column)
- **Endpoint Reference**: Full-width responsive card grid (moved above Quick Start)
- **Quick Start Guide**: Full-width terminal-style code block (moved below Endpoint Reference)

### 5.2 Visual Enhancements
- Tab bar with `Terminal` icon and orange active underline
- Line numbers column with right-aligned monospace numbers
- Basic syntax highlighting: keywords (orange), comments (teal), default (cream)
- Active key indicator bar showing masked key with copy button
- New icon imports: `Terminal`, `BookOpen`, `ArrowRight`, `Hash`

### 5.3 Code Snippet Trimming
Condensed all three language snippets from 30–50+ lines down to ~20 lines each:
- Removed blank lines, long decorative comment separators
- Compacted payload definitions onto fewer lines
- TypeScript: Removed verbose interface definitions, kept inline type annotations
- Each snippet still demonstrates both creating a session and sending an offer

---

## 6. Files Modified / Created

### Created
| File | Purpose |
|---|---|
| `backend/src/api/apikey_routes.py` | API key CRUD endpoints (generate, list, revoke) |
| `frontend/src/pages/ApiAccess.jsx` | API Access page with key management + code snippets |

### Modified
| File | Changes |
|---|---|
| `backend/src/app.py` | Added `apikey_router` import and `include_router` |
| `backend/src/api/auth_routes.py` | `get_current_user` now handles both JWT and `tm_` API keys |
| `frontend/src/App.jsx` | Added `ApiAccess` import + `/api-access` route in `ProtectedRoute` |
| `frontend/src/components/Navbar.jsx` | Added `Key` icon import + API nav link |
| `frontend/src/pages/Authority.jsx` | Syntax fix, removed unused imports, removed performance inputs, fixed category bug |
| `frontend/src/pages/ProductCatalog.jsx` | Added analytics popup modal per product card |
| `frontend/src/lib/productStore.js` | Added `getProductStats()` function |
| `backend/src/api/product_routes.py` | Added `GET /products/{id}/stats` endpoint |

---

## 7. Database Schema

### MySQL — `trademind` database

#### `api_keys` table (new)
```sql
CREATE TABLE api_keys (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    api_key       VARCHAR(64) NOT NULL UNIQUE,
    label         VARCHAR(100) DEFAULT 'Default',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at  TIMESTAMP NULL,
    is_active     TINYINT(1) DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_api_key (api_key),
    INDEX idx_user_id (user_id)
);
```

#### Existing tables
| Table | Purpose |
|---|---|
| `users` | User accounts (id, email, password hash, name) |
| `products` | Product catalog (name, category, prices, strategy) |
| `chat_sessions` | Negotiation sessions (product, prices, status, rounds) |
| `chat_messages` | Individual messages within sessions |
| `api_keys` | API keys for programmatic access |

---

## 8. API Endpoints Reference

### Authentication
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | None | Register a new user |
| `POST` | `/api/v1/auth/login` | None | Login, returns JWT |
| `GET` | `/api/v1/auth/me` | JWT / API Key | Get current user info |

### Products
| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/products` | JWT / API Key | List all products |
| `POST` | `/api/v1/products` | JWT / API Key | Create a product |
| `GET` | `/api/v1/products/{id}/stats` | JWT / API Key | Get product analytics |

### Chat Sessions
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/chat-sessions` | JWT / API Key | Create negotiation session |
| `GET` | `/api/v1/chat-sessions` | JWT / API Key | List all sessions |
| `GET` | `/api/v1/chat-sessions/{id}` | JWT / API Key | Get session with messages |
| `POST` | `/api/v1/chat-sessions/{id}/messages` | JWT / API Key | Send a buyer offer |
| `PUT` | `/api/v1/chat-sessions/{id}/close` | JWT / API Key | Close & finalize session |

### API Keys
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/api-keys` | JWT / API Key | Generate a new API key |
| `GET` | `/api/v1/api-keys` | JWT / API Key | List all your keys |
| `DELETE` | `/api/v1/api-keys/{id}` | JWT / API Key | Revoke a key |

---

## 9. Design System

### Neo-Brutalist Theme
| Token | Hex | Usage |
|---|---|---|
| `neo-navy` | `#001524` | Primary background, text |
| `neo-teal` | `#15616D` | Accents, GET badges, success |
| `neo-cream` | `#FFECD1` | Light backgrounds, secondary text |
| `neo-orange` | `#FF7D00` | CTAs, active states, POST badges |
| `neo-maroon` | `#78290F` | Danger, delete, errors |

### Architecture
```
Frontend (React 19 + Vite)     →  :5181
Backend  (FastAPI)             →  :8000
Analytics Backend (FastAPI)    →  :8001
MySQL    (trademind)           →  :3306
PostgreSQL (negotiation_bot)   →  :5432  (legacy)
```

### Frontend Routes
| Path | Page | Protected |
|---|---|---|
| `/` | Home | No |
| `/login` | Login | No |
| `/register` | Register | No |
| `/products` | Product Catalog | Yes |
| `/authority` | Authority (Analyzer) | Yes |
| `/jury` | Jury (Settings) | Yes |
| `/wallet` | Wallet | Yes |
| `/api-access` | API Access | Yes |
| `/chat` | Chat | Yes |
| `/reporter` | Reporter | Yes |
| `/reputation` | Reputation | Yes |

---

*Generated on February 8, 2026*
