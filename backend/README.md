# Cross-Commodity Signal API

FastAPI backend serving macro, fundamental, sentiment, and technical trading signals for commodities markets.

## How to Run Locally

### Prerequisites

- Python 3.8 or higher
- pip 

### Setup

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Run the development server:**

```bash
uvicorn backend.app.main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Running with Custom Port

```bash
uvicorn backend.app.main:app --reload --port 8080
```

## API Endpoints

### GET /signals

Get trading signals with optional filtering.

**Query Parameters:**
- `market` (optional): Filter by market name (e.g., "WTI Crude Oil", "Gold", "Brent Crude", "Copper")
- `category` (optional): Filter by category ("Technical", "Macro", "Fundamental", "Sentiment")

**Response:** List of Signal objects

**Examples:**
```bash
# Get all signals
GET /signals

# Filter by market
GET /signals?market=Gold

# Filter by category
GET /signals?category=Technical

# Combined filters
GET /signals?market=WTI Crude Oil&category=Fundamental
```

**Response Format:**
```json
[
  {
    "market": "WTI Crude Oil",
    "category": "Technical",
    "name": "RSI",
    "direction": "Bullish",
    "confidence": "Medium",
    "updated": "2025-12-23",
    "explanation": "Selling pressure appears to be easing."
  }
]
```

**Empty Results:**
Returns an empty array `[]` when no signals match the filters.

---

### GET /markets

Get list of all unique markets that have signals.

**Response:**
```json
{
  "markets": ["Brent Crude", "Copper", "Gold", "WTI Crude Oil"]
}
```

**Example:**
```bash
GET /markets
```

---

### GET /categories

Get list of all unique signal categories.

**Response:**
```json
{
  "categories": ["Fundamental", "Macro", "Sentiment", "Technical"]
}
```

**Example:**
```bash
GET /categories
```

---

## Signal Model

Each signal contains:

- **market** (string): The commodity market name
- **category** (string): Signal category - "Technical", "Macro", "Fundamental", or "Sentiment"
- **name** (string): Signal name/identifier
- **direction** (string): "Bullish", "Bearish", or "Neutral"
- **confidence** (string): "Low", "Medium", or "High"
- **updated** (date): Last update date (YYYY-MM-DD)
- **explanation** (string): Human-readable explanation of the signal

## Current Status

This is an MVP implementation using **mocked/hardcoded signals**. The API currently returns 5 example signals covering all four categories:

- **Technical**: RSI (WTI), Moving Average Crossover (Brent)
- **Macro**: USD Trend (Gold)
- **Fundamental**: Crude Inventories (WTI)
- **Sentiment**: COT Positioning (Copper)

## Development Notes

- No database or external data sources yet
- All signals are hardcoded in `app/routes.py`
- Filtering is case-sensitive and matches exact market/category names
- See `/docs` for interactive API documentation

