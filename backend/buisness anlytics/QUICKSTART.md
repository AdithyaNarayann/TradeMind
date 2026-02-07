# 🚀 Quick Start Guide - Amazon Pricing System

This guide will get you up and running in 5 minutes.

## Step 1: Install Dependencies

```bash
cd amazon-pricing-system
pip install -r requirements.txt
```

## Step 2: Configure (Optional)

```bash
# Copy environment template
cp .env.example .env

# Edit .env if you want to customize settings
# For basic testing, default settings work fine
```

## Step 3: Test the System

```bash
# Run integration test
python test_system.py
```

This will:
- Initialize all agents
- Test the complete pipeline
- Show sample pricing recommendations

**Expected output:** You should see pricing recommendations for test products.

## Step 4: Start the API Server

```bash
python api/main.py
```

The API will start at `http://localhost:8000`

## Step 5: Make Your First Request

### Option A: Use the Interactive Docs (Easiest)

1. Open browser: `http://localhost:8000/docs`
2. Click on `POST /price-recommendation`
3. Click "Try it out"
4. Use this sample request:

```json
{
  "product_name": "Boat wireless earbuds",
  "category": "Electronics",
  "specs": ["Bluetooth 5.3", "Noise Cancellation"],
  "base_price": 1200,
  "desired_margin": 20
}
```

5. Click "Execute"
6. See your pricing recommendation!

### Option B: Use curl

```bash
curl -X POST http://localhost:8000/price-recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Boat wireless earbuds",
    "category": "Electronics",
    "specs": ["Bluetooth 5.3", "Noise Cancellation"],
    "base_price": 1200,
    "desired_margin": 20
  }'
```

### Option C: Use Python

```python
import requests

response = requests.post(
    "http://localhost:8000/price-recommendation",
    json={
        "product_name": "Boat wireless earbuds",
        "category": "Electronics",
        "specs": ["Bluetooth 5.3", "Noise Cancellation"],
        "base_price": 1200,
        "desired_margin": 20
    }
)

result = response.json()
print(f"Recommended Price: ₹{result['recommended_price']}")
print(f"Strategy: {result['strategy']}")
print(f"Insight: {result['insight']}")
```

## Understanding the Response

```json
{
  "success": true,
  "recommended_price": 1949,          // What to price your product at
  "strategy": "Competitive Entry",     // Pricing strategy used
  "confidence": "High",                // How confident we are
  "market_median": 1999,               // Market median price
  "market_min": 1899,                  // Lowest competitor price
  "market_max": 2149,                  // Highest competitor price
  "competitor_count": 18,              // Number of competitors analyzed
  "margin_achieved": 18.5,             // Your profit margin %
  "market_position": "2.5% below median",
  "insight": "Pricing at ₹1,949...",   // Main recommendation
  "reasoning": [                        // Why this recommendation
    "Market analysis: 18 products...",
    "Margin: 18.5%...",
    "Your position: 2.5% below median...",
    "Pro tip: This competitive pricing..."
  ]
}
```

## Common Use Cases

### 1. New Product Launch

```json
{
  "product_name": "Your Product Name",
  "category": "Your Category",
  "specs": ["Key Feature 1", "Key Feature 2"],
  "base_price": 1000,      // Your cost
  "desired_margin": 25     // Target profit %
}
```

### 2. Repricing Existing Product

Same request format, but use your current cost as `base_price`.

### 3. Competitive Analysis

The system automatically analyzes 15-25 competitors and shows you:
- Market price range
- Your competitive position
- Pricing strategy recommendations

## Advanced Features (Optional)

### Enable LLM for Better Insights

1. Get OpenAI API key from https://platform.openai.com
2. Edit `.env`:
   ```bash
   USE_LLM=True
   OPENAI_API_KEY=sk-your-key-here
   ```
3. Restart server

### Enable Aggressive Pricing Mode

Edit `.env`:
```bash
AGGRESSIVE_PRICING=True
```

This will recommend more competitive pricing to gain market share.

### Configure Scraper Settings

Edit `.env`:
```bash
SCRAPER_TARGET_PRODUCTS=30  # Scrape more products
SCRAPER_MAX_PAGES=3         # Scrape more pages
```

## Docker Deployment (Optional)

```bash
# Build and run with Docker Compose
docker-compose up --build

# API will be at http://localhost:8000
```

## Troubleshooting

### Error: "Insufficient data"

**Cause:** Not enough products found on Amazon  
**Fix:** 
- Make product name more specific
- Try different category
- Reduce `MIN_PRODUCTS_FOR_ANALYSIS` in .env

### Error: "Rate limit exceeded"

**Cause:** Too many requests  
**Fix:** 
- Wait 1 hour
- Increase limits in .env (not recommended)

### Scraper getting blocked

**Cause:** Too aggressive scraping  
**Fix:**
- Increase delays in .env
- Reduce requests per hour
- Wait and try again later

## What's Next?

✅ You now have a working AI pricing system!

**Ideas:**
1. Integrate with your product management system
2. Build a dashboard frontend
3. Set up automated repricing schedules
4. Monitor competitor price changes
5. Add email alerts for market changes

## Need Help?

- Check the main README.md for detailed documentation
- Look at test_system.py for usage examples
- Check individual agent files for implementation details
- Visit http://localhost:8000/docs for API reference

---

**Happy Pricing! 🚀**
