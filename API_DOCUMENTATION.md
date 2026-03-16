# HPCL Lead Intelligence Agent - API Documentation

## Overview

RESTful API built with FastAPI for the HPCL Lead Intelligence Agent. The API provides endpoints for lead management, company information, source registry, and dashboard statistics.

**Base URL**: `http://localhost:8000`

**API Documentation**: `http://localhost:8000/docs` (Swagger UI)

**Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)

## Authentication

Currently, the API does not require authentication. This should be added before production deployment.

## CORS Configuration

CORS is configured to allow requests from `http://localhost:3000`[FOR LOCAL DEVELOPMENT] (React frontend).

## Endpoints

### Health Check

#### GET /
Health check endpoint.

**Response**:
```json
{
  "status": "ok",
  "message": "HPCL Lead Intelligence Agent API"
}
```

#### GET /health
Alternative health check endpoint.

**Response**:
```json
{
  "status": "healthy"
}
```

---

### Lead Management

#### GET /api/leads/
List leads with optional filters and pagination.

**Query Parameters**:
- `priority` (optional): Filter by priority (`high`, `medium`, `low`)
- `status` (optional): Filter by status (`new`, `contacted`, `qualified`, `converted`, `rejected`)
- `assigned_to` (optional): Filter by assigned sales officer
- `territory` (optional): Filter by territory
- `limit` (optional, default: 50, max: 100): Maximum number of results
- `offset` (optional, default: 0): Number of results to skip

**Response**:
```json
{
  "leads": [
    {
      "id": "uuid",
      "company_name": "ABC Industries",
      "event_summary": "Expansion of manufacturing facility",
      "score": 85,
      "priority": "high",
      "status": "new",
      "created_at": "2024-01-15T10:30:00",
      "top_product": "Furnace Oil"
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

#### GET /api/leads/{lead_id}
Get complete lead dossier with all related information.

**Path Parameters**:
- `lead_id` (UUID): Lead identifier

**Response**:
```json
{
  "lead": {
    "id": "uuid",
    "event_id": "uuid",
    "company_id": "uuid",
    "score": 85,
    "priority": "high",
    "assigned_to": "officer_123",
    "territory": "Mumbai",
    "status": "new",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  },
  "company": {
    "id": "uuid",
    "name": "ABC Industries",
    "name_variants": ["ABC Ind", "ABC Industries Ltd"],
    "cin": "U12345MH2020PTC123456",
    "gst": "27AABCU1234A1Z5",
    "website": "https://abcindustries.com",
    "industry": "Manufacturing",
    "address": "Mumbai, Maharashtra",
    "locations": ["Mumbai", "Pune"],
    "key_products": ["Steel", "Machinery"]
  },
  "event": {
    "id": "uuid",
    "event_type": "expansion",
    "event_summary": "ABC Industries announces expansion of manufacturing facility",
    "location": "Mumbai",
    "capacity": "500 TPD",
    "deadline": "2024-06-30",
    "intent_strength": 0.85
  },
  "signal": {
    "id": "uuid",
    "url": "https://example.com/news/abc-expansion",
    "title": "ABC Industries Expands Operations",
    "ingested_at": "2024-01-15T09:00:00"
  },
  "products": [
    {
      "id": "uuid",
      "product_name": "Furnace Oil",
      "confidence_score": 0.92,
      "reasoning": "Manufacturing expansion with boiler operations",
      "reason_code": "operational_cue",
      "rank": 1,
      "uncertainty_flag": false
    }
  ],
  "feedback": []
}
```

**Error Responses**:
- `404 Not Found`: Lead not found

#### POST /api/leads/{lead_id}/feedback
Submit feedback for a lead.

**Path Parameters**:
- `lead_id` (UUID): Lead identifier

**Request Body**:
```json
{
  "feedback_type": "accepted",
  "notes": "Good lead, will follow up tomorrow",
  "submitted_by": "officer_123"
}
```

**Feedback Types**:
- `accepted`: Sales officer accepted the lead
- `rejected`: Sales officer rejected the lead
- `converted`: Lead was converted to a sale

**Response**:
```json
{
  "id": "uuid",
  "lead_id": "uuid",
  "feedback_type": "accepted",
  "notes": "Good lead, will follow up tomorrow",
  "submitted_at": "2024-01-15T11:00:00",
  "submitted_by": "officer_123"
}
```

**Error Responses**:
- `404 Not Found`: Lead not found

---

### Company Management

#### GET /api/companies/{company_id}
Get company card by ID.

**Path Parameters**:
- `company_id` (UUID): Company identifier

**Response**:
```json
{
  "id": "uuid",
  "name": "ABC Industries",
  "name_variants": ["ABC Ind", "ABC Industries Ltd"],
  "cin": "U12345MH2020PTC123456",
  "gst": "27AABCU1234A1Z5",
  "website": "https://abcindustries.com",
  "industry": "Manufacturing",
  "address": "Mumbai, Maharashtra",
  "locations": ["Mumbai", "Pune"],
  "key_products": ["Steel", "Machinery"],
  "created_at": "2024-01-10T08:00:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

**Error Responses**:
- `404 Not Found`: Company not found

---

### Source Management

#### GET /api/sources/
List source registry with optional filters and pagination.

**Query Parameters**:
- `category` (optional): Filter by category (`news`, `tender`, `company_site`)
- `trust_tier` (optional): Filter by trust tier (`high`, `medium`, `low`, `neutral`)
- `limit` (optional, default: 50, max: 100): Maximum number of results
- `offset` (optional, default: 0): Number of results to skip

**Response**:
```json
{
  "sources": [
    {
      "id": "uuid",
      "domain": "economictimes.com",
      "category": "news",
      "access_method": "rss",
      "crawl_frequency_minutes": 60,
      "trust_score": 75.5,
      "trust_tier": "high",
      "robots_txt_allowed": true,
      "last_crawled_at": "2024-01-15T10:00:00",
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 25,
  "limit": 50,
  "offset": 0
}
```

#### POST /api/sources/{source_id}/configure
Update source configuration settings.

**Path Parameters**:
- `source_id` (UUID): Source identifier

**Request Body**:
```json
{
  "crawl_frequency_minutes": 120,
  "robots_txt_allowed": true
}
```

**Response**:
```json
{
  "id": "uuid",
  "domain": "economictimes.com",
  "category": "news",
  "access_method": "rss",
  "crawl_frequency_minutes": 120,
  "trust_score": 75.5,
  "trust_tier": "high",
  "robots_txt_allowed": true,
  "last_crawled_at": "2024-01-15T10:00:00",
  "created_at": "2024-01-01T00:00:00"
}
```

**Error Responses**:
- `404 Not Found`: Source not found

---

### Dashboard

#### GET /api/dashboard/stats
Get dashboard statistics and metrics.

**Query Parameters**:
- `days` (optional, default: 30, min: 1, max: 365): Number of days to include in statistics

**Response**:
```json
{
  "total_leads": 150,
  "leads_by_priority": {
    "high": 45,
    "medium": 75,
    "low": 30
  },
  "leads_by_status": {
    "new": 50,
    "contacted": 40,
    "qualified": 30,
    "converted": 20,
    "rejected": 10
  },
  "conversion_rate": 13.33,
  "top_sources": [
    {
      "domain": "economictimes.com",
      "trust_score": 75.5,
      "trust_tier": "high",
      "category": "news"
    }
  ],
  "recent_leads_count": 25
}
```

---

## Error Handling

All endpoints return consistent error responses:

### 404 Not Found
```json
{
  "detail": "Lead {id} not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "feedback_type"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Running the API

### Development Mode

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python scripts/init_db.py

# Run the API server
uvicorn app.main:app --reload --port 8000
```

### Production Mode

```bash
# Run with Docker Compose
docker-compose up
```

---

## Testing the API

### Interactive Documentation

Visit `http://localhost:8000/docs` for Swagger UI with interactive API testing.

### Manual Testing

```bash
# Run manual test script
python tests/manual_test_api.py
```

### cURL Examples

```bash
# List leads
curl http://localhost:8000/api/leads/

# Get lead dossier
curl http://localhost:8000/api/leads/{lead_id}

# Submit feedback
curl -X POST http://localhost:8000/api/leads/{lead_id}/feedback \
  -H "Content-Type: application/json" \
  -d '{"feedback_type": "accepted", "notes": "Good lead"}'

# Get dashboard stats
curl http://localhost:8000/api/dashboard/stats
```

---

## Next Steps

1. Add authentication and authorization
2. Add rate limiting
3. Add request logging
4. Add API versioning
5. Add WebSocket support for real-time updates
6. Add bulk operations endpoints
7. Add export functionality (CSV, Excel)
