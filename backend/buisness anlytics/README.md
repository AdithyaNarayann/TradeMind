# 🤖 Amazon Pricing System - Autonomous AI Agents

An **intelligent, agentic pricing system** that autonomously analyzes Amazon market data and provides explainable pricing recommendations for sellers.

## 🎯 What This Is

This is **NOT** just a scraper. This is an **autonomous multi-agent system** where:

- ✅ Agents make decisions independently
- ✅ Each agent has specific expertise
- ✅ Decisions are explainable and trustworthy
- ✅ System is modular and scalable

## 🧱 Architecture

```
User Request
    ↓
API Layer (FastAPI)
    ↓
Agent Orchestrator (The Brain 🧠)
    ↓
┌─────────────────────────────────────┐
│  AGENT PIPELINE                     │
├─────────────────────────────────────┤
│ 1. Query Builder Agent              │
│    ↓ optimized search query         │
│ 2. Amazon Scraper Agent             │
│    ↓ raw market data                │
│ 3. Data Cleaning Agent              │
│    ↓ validated dataset              │
│ 4. Pricing Strategy Agent           │
│    ↓ pricing decision               │
│ 5. Insight Generator Agent          │
│    ↓ explainable insights           │
└─────────────────────────────────────┘
    ↓
Response + Analytics
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Clone repository (or navigate to project directory)
cd amazon-pricing-system

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env as needed (optional - works with defaults)

# Run the API server
python api/main.py
```

The API will be available at `http://localhost:8000`

## 📡 API Usage

### Get Pricing Recommendation

**Endpoint:** `POST /price-recommendation`

**Request:**
```json
{
  "product_name": "Boat Airdopes 141",
  "category": "Electronics",
  "specs": ["Bluetooth 5.0", "Touch Controls", "IPX4"],
  "base_price": 1200,
  "desired_margin": 20
}
```

**Response:**
```json
{
  "success": true,
  "recommended_price": 1949,
  "strategy": "Competitive Entry Pricing",
  "confidence": "High",
  "market_median": 1999,
  "market_min": 1899,
  "market_max": 2149,
  "competitor_count": 18,
  "margin_achieved": 18.5,
  "market_position": "2.5% below median",
  "insight": "Pricing at ₹1,949 positions you competitively...",
  "reasoning": [
    "Market analysis: 18 comparable products ranging from ₹1,899 to ₹2,149",
    "Margin: 18.5% (target was 20.0%)",
    "Your position: 2.5% below median — slight price advantage",
    "Pro tip: This competitive pricing can help you gain initial traction"
  ],
  "timestamp": "2026-02-07T12:30:45",
  "query_used": "boat airdopes 141 bluetooth touch controls"
}
```

### Other Endpoints

- `GET /` - API info
- `GET /health` - Health check
- `GET /config` - Current configuration
- `GET /docs` - Interactive API documentation (Swagger)

## 🧠 The Agents

### 1️⃣ Query Builder Agent
- **Type:** Semi-AI (rule-based + optional LLM)
- **Purpose:** Convert messy product input → optimized Amazon search query
- **Why it matters:** Bad query = bad data = bad pricing

### 2️⃣ Amazon Scraper Agent
- **Type:** Autonomous execution agent
- **Scope:** Search results pages ONLY (no product details, no login)
- **Intelligence:**
  - Decides when to stop scraping (quality-based)
  - Self-throttles to avoid blocks
  - Validates data in real-time

### 3️⃣ Data Cleaning Agent
- **Type:** Rule-based intelligence
- **Purpose:** Clean, validate, and ensure trustworthy data
- **Critical:** Determines if results are reliable enough to use

### 4️⃣ Pricing Strategy Agent 💸
- **Type:** Business logic agent
- **Purpose:** Core pricing intelligence (your IP!)
- **Strategies:**
  - Competitive Entry Pricing
  - Neutral Market Pricing
  - Premium Positioning
  - Warning: Market Too Low

### 5️⃣ Insight Generator Agent
- **Type:** LLM-based (with rule-based fallback)
- **Purpose:** Translate analytics → human insights
- **Why it matters:** Builds trust, makes output explainable

## 📊 Features

### ✅ Implemented (MVP)

- Complete 5-agent pipeline
- FastAPI REST API
- Autonomous scraping with stopping logic
- Intelligent pricing strategies
- Explainable recommendations
- SQLite caching (avoid re-scraping)
- Rate limiting & safety controls
- Retry logic with exponential backoff
- Comprehensive error handling

### 🔜 Future Enhancements

- Redis cache for production
- Historical price tracking
- Competitor monitoring alerts
- A/B testing recommendations
- Dashboard frontend
- Multi-marketplace support (Flipkart, etc.)
- ML-based demand prediction

## 🛡️ Safety Features

### Rate Limiting
- 60 requests/hour, 500 requests/day (configurable)
- Automatic throttling
- Daily limit protection

### Scraper Protection
- Random delays (4-8 seconds)
- Rotating User-Agent
- Quality-based stopping
- No aggressive scraping

### Data Quality
- Outlier detection
- Minimum product thresholds
- Price validation
- Review count filtering

## 🔧 Configuration

Edit `.env` file to customize:

```bash
# Use LLM for better insights
USE_LLM=True
OPENAI_API_KEY=sk-your-key

# Aggressive pricing mode
AGGRESSIVE_PRICING=True

# Scraper limits
SCRAPER_TARGET_PRODUCTS=30
MAX_REQUESTS_PER_DAY=1000
```

## 📁 Project Structure

```
amazon-pricing-system/
├── agents/                 # The 5 autonomous agents
│   ├── query_builder.py
│   ├── amazon_scraper.py
│   ├── data_cleaning.py
│   ├── pricing_strategy.py
│   ├── insight_generator.py
│   └── orchestrator.py     # The brain
├── api/
│   └── main.py            # FastAPI application
├── models/
│   └── schemas.py         # Pydantic models
├── storage/
│   └── cache.py           # SQLite caching
├── utils/
│   ├── config.py          # Configuration
│   └── rate_control.py    # Safety controls
├── requirements.txt
├── .env.example
└── README.md
```

## 🧪 Testing

```bash
# Test individual agents
python agents/query_builder.py
python agents/amazon_scraper.py
python agents/pricing_strategy.py

# Test full pipeline
python agents/orchestrator.py

# Test API (with server running)
curl -X POST http://localhost:8000/price-recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Boat earbuds",
    "category": "Electronics",
    "specs": ["Bluetooth 5.0"],
    "base_price": 1200,
    "desired_margin": 20
  }'
```

## ⚠️ Important Notes

### Legal & Ethical
- **Respect robots.txt** - This scraper follows ethical guidelines
- **Rate limiting** - Built-in protection against aggressive scraping
- **No authentication** - Only scrapes public search results
- **No personal data** - Only collects public pricing info

### Production Deployment
- Use Redis instead of SQLite for cache
- Set up proper logging
- Configure environment variables
- Use process manager (gunicorn/supervisor)
- Add monitoring (Prometheus, etc.)
- Implement proper error alerting

### Scaling
- Current design: Single server
- For scale: Add message queue (RabbitMQ/Redis)
- Distribute scraping across workers
- Use CDN for API caching

## 💡 Why This Architecture is Strong

✅ **Modular** - Each agent is independent  
✅ **Explainable** - Every decision has reasoning  
✅ **Agentic** - Not just automation, actual intelligence  
✅ **MVP-safe** - Works without complex infrastructure  
✅ **Scalable** - Easy to enhance and extend  

## 🤝 Support

For issues or questions, create an issue in the repository.

## 📄 License

MIT License - Use freely, build amazing things!

---

**Built with Python, FastAPI, and autonomous AI agents** 🤖
