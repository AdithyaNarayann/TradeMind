# 📡 API Documentation - Amazon Pricing System

Complete API reference for the Amazon Pricing System.

## Base URL

```
http://localhost:8000
```

For production, replace with your deployed URL.

## Authentication

Currently no authentication required (MVP version).

For production: Implement API keys, JWT tokens, or OAuth2.

---

## Endpoints

### 1. Root Endpoint

**GET /** 

Get API information.

**Response:**
```json
{
  "service": "Amazon Pricing System",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs"
}
```

---

### 2. Health Check

**GET /health**

Check if the system is healthy and all agents are operational.

**Response:**
```json
{
  "status": "healthy",
  "agents": {
    "query_builder": "ok",
    "scraper": "ok",
    "data_cleaner": "ok",
    "pricing_agent": "ok",
    "insight_generator": "ok"
  },
  "llm_enabled": false
}
```

**Status Codes:**
- `200 OK` - System is healthy
- `503 Service Unavailable` - System has issues

---

### 3. Get Configuration

**GET /config**

Get current system configuration.

**Response:**
```json
{
  "llm_enabled": false,
  "aggressive_pricing": false,
  "min_products_threshold": 5,
  "scraper": {
    "target_products": 25,
    "max_pages": 2,
    "delay_range": "4-8s"
  }
}
```

---

### 4. Get Price Recommendation ⭐

**POST /price-recommendation**

Get AI-powered pricing recommendation for your product.

**Request Body:**

```json
{
  "product_name": "string",          // Required: Product name
  "category": "string",              // Required: Product category
  "specs": ["string"],               // Optional: Product specifications
  "base_price": number,              // Required: Your cost price (> 0)
  "desired_margin": number           // Required: Target margin % (0-100)
}
```

**Field Details:**

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `product_name` | string | Yes | Product name or title | "Boat Airdopes 141" |
| `category` | string | Yes | Product category | "Electronics" |
| `specs` | array[string] | No | Key specifications | ["Bluetooth 5.0", "IPX4"] |
| `base_price` | number | Yes | Your cost/base price (₹) | 1200 |
| `desired_margin` | number | Yes | Target profit margin (%) | 20 |

**Success Response (200 OK):**

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
  "insight": "Pricing at ₹1,949 positions you competitively in a market where most sellers price around ₹1,999.",
  "reasoning": [
    "Market analysis: 18 comparable products ranging from ₹1,899 to ₹2,149",
    "Margin: 18.5% (target was 20.0%)",
    "Your position: 2.5% below median — slight price advantage over typical competitors",
    "Pro tip: This competitive pricing can help you gain initial traction and reviews"
  ],
  "timestamp": "2026-02-07T12:30:45.123456",
  "query_used": "boat airdopes 141 bluetooth"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether request succeeded |
| `recommended_price` | number | Recommended selling price (₹) |
| `strategy` | string | Pricing strategy used |
| `confidence` | string | Confidence level: "High", "Medium", or "Low" |
| `market_median` | number | Market median price (₹) |
| `market_min` | number | Lowest competitor price (₹) |
| `market_max` | number | Highest competitor price (₹) |
| `competitor_count` | integer | Number of competitors analyzed |
| `margin_achieved` | number | Your profit margin at recommended price (%) |
| `market_position` | string | Your position vs market median |
| `insight` | string | Main recommendation insight |
| `reasoning` | array[string] | Supporting reasoning points |
| `timestamp` | string | When recommendation was generated (ISO 8601) |
| `query_used` | string | Amazon search query used |

**Pricing Strategies:**

- `"Competitive Entry Pricing"` - Priced below market median for competitiveness
- `"Neutral Market Pricing"` - Priced at market median
- `"Premium Positioning"` - Priced above market median
- `"Warning: Market Too Low"` - Market doesn't support desired margins

**Confidence Levels:**

- `"High"` - Strong confidence in recommendation (good data, clear market)
- `"Medium"` - Moderate confidence (some uncertainties)
- `"Low"` - Low confidence (poor data quality or unusual market)

**Error Response (success: false):**

```json
{
  "success": false,
  "error_type": "insufficient_data",
  "message": "Only found 3 products. Need at least 5 for reliable pricing.",
  "details": {
    "products_found": 3
  }
}
```

**Error Types:**

| Error Type | Description | How to Fix |
|------------|-------------|------------|
| `query_invalid` | Could not build valid search query | Provide clearer product name |
| `insufficient_data` | Not enough products found | Make product name more specific |
| `data_quality_poor` | Scraped data failed validation | Try different category or product |
| `pricing_invalid` | Cannot generate valid recommendation | Check base price and margin |
| `pipeline_error` | Unexpected system error | Contact support |

**Status Codes:**

- `200 OK` - Request processed (check `success` field for actual result)
- `400 Bad Request` - Invalid input parameters
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - System unavailable

---

## Request Examples

### Example 1: Electronics Product

```bash
curl -X POST http://localhost:8000/price-recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Boat Rockerz 450",
    "category": "Electronics",
    "specs": ["Bluetooth Headphones", "40mm Drivers", "8 hours battery"],
    "base_price": 1000,
    "desired_margin": 25
  }'
```

### Example 2: Fashion Item

```bash
curl -X POST http://localhost:8000/price-recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Nike Air Max 270",
    "category": "Footwear",
    "specs": ["Men", "Running Shoes", "Size 9"],
    "base_price": 3500,
    "desired_margin": 15
  }'
```

### Example 3: Home Appliance

```bash
curl -X POST http://localhost:8000/price-recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Philips Air Fryer",
    "category": "Home & Kitchen",
    "specs": ["4.1L capacity", "1400W", "Digital display"],
    "base_price": 4500,
    "desired_margin": 20
  }'
```

---

## Python Client Example

```python
import requests
from typing import Dict, List

class PricingClient:
    """Client for Amazon Pricing System API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def get_recommendation(
        self,
        product_name: str,
        category: str,
        base_price: float,
        desired_margin: float,
        specs: List[str] = None
    ) -> Dict:
        """
        Get pricing recommendation
        
        Returns:
            dict: Pricing recommendation or error
        """
        url = f"{self.base_url}/price-recommendation"
        
        payload = {
            "product_name": product_name,
            "category": category,
            "base_price": base_price,
            "desired_margin": desired_margin,
            "specs": specs or []
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        return response.json()
    
    def health_check(self) -> Dict:
        """Check API health"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()


# Usage
client = PricingClient()

result = client.get_recommendation(
    product_name="Boat wireless earbuds",
    category="Electronics",
    base_price=1200,
    desired_margin=20,
    specs=["Bluetooth 5.0", "Touch Controls"]
)

if result["success"]:
    print(f"Recommended Price: ₹{result['recommended_price']}")
    print(f"Strategy: {result['strategy']}")
    print(f"Margin: {result['margin_achieved']}%")
    print(f"\nInsight: {result['insight']}")
else:
    print(f"Error: {result['message']}")
```

---

## Rate Limits

**Default Limits:**
- 60 requests per hour
- 500 requests per day

**Headers (Future):**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1612137600
```

**Exceeding Limits:**

If you exceed rate limits, you'll receive:
```json
{
  "success": false,
  "error_type": "rate_limit_exceeded",
  "message": "Daily limit of 500 requests exceeded. Try again tomorrow."
}
```

---

## Best Practices

### 1. Cache Results
- Recommendations are valid for 24 hours
- Don't re-request for same product frequently
- System has built-in caching

### 2. Handle Errors Gracefully
```python
try:
    result = client.get_recommendation(...)
    if not result["success"]:
        # Handle business logic error
        print(f"Error: {result['message']}")
except requests.RequestException as e:
    # Handle network/HTTP error
    print(f"Request failed: {e}")
```

### 3. Provide Specific Product Info
- ✅ "Boat Airdopes 141 Bluetooth Earbuds"
- ❌ "Earbuds"

### 4. Use Appropriate Categories
- "Electronics"
- "Footwear"
- "Home & Kitchen"
- "Books"
- etc.

### 5. Monitor Confidence Levels
- High confidence → Use recommendation directly
- Medium confidence → Consider additional research
- Low confidence → Manual review recommended

---

## Interactive Documentation

Visit `http://localhost:8000/docs` for:
- Interactive API testing
- Request/response examples
- Schema definitions
- Try-it-out functionality

---

## Support

For issues or questions:
1. Check error message and `error_type`
2. Review troubleshooting section
3. Create an issue in the repository

---

**API Version:** 1.0.0  
**Last Updated:** February 2026
