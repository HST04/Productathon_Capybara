# HPCL B2B Lead Intelligence Agent

> **Demo / Hackathon Project** — This codebase is a portfolio demonstration.
> It is **not production-ready**: there is no authentication on API endpoints, no rate limiting,
> and credentials must be replaced via `.env` before any real deployment.
> See `.env.example` for required environment variables.

An AI-powered system that automates business opportunity discovery for HPCL sales teams. The system continuously scans public sources, detects business signals, infers product demand, and generates prioritized, sales-ready leads.

## Features

- **Automated Discovery**: Continuously monitors public sources for business opportunities
- **Intelligent Qualification**: Uses AI to classify events and infer product needs
- **Semantic Company Matching**: Resolves company identities across name variants
- **Dynamic Source Trust**: Learns which sources are reliable based on feedback
- **Geographic Routing**: Routes leads to appropriate sales territories
- **Mobile Interface**: Responsive design with offline support
- **WhatsApp Alerts**: Push notifications for high-priority leads

## Architecture

- **Backend**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL for structured data
- **Vector DB**: Pinecone for semantic company matching
- **AI/ML**: OpenAI GPT-4 or local LLM, sentence-transformers
- **Frontend**: React with TypeScript (to be implemented)
- **Deployment**: Docker Compose for local orchestration

### Docker Services

The application runs as four containerized services:

1. **postgres** - PostgreSQL 15 database
   - Port: 5432
   - Persistent volume for data storage
   - Health checks for service dependencies

2. **backend** - FastAPI application server
   - Port: 8000
   - Hot-reload enabled for development
   - Depends on healthy postgres service

3. **worker** - Background signal processing
   - Continuously polls for unprocessed signals
   - Runs entity extraction, company matching, and lead scoring
   - Depends on healthy postgres service

4. **frontend** - React development server
   - Port: 3000
   - Hot-reload enabled for development
   - Proxies API requests to backend

## Setup

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL 15+
- Docker and Docker Compose (optional)
- Pinecone account and API key (v5.0+)
- OpenAI API key (optional, for LLM-based extraction)

### Quick Start with Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd hpcl-lead-intelligence
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration (see Configuration section below)
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```
   
   This will start:
   - PostgreSQL database (port 5432)
   - Backend API server (port 8000)
   - Background worker for signal processing
   - Frontend React app (port 3000)

4. **Initialize the database**
   ```bash
   docker-compose exec backend python scripts/init_db.py
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

6. **View logs**
   ```bash
   docker-compose logs -f
   ```

7. **Stop services**
   ```bash
   docker-compose down
   ```

### Manual Installation

#### Backend Setup

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Note:** This will install all required packages including:
   - Web framework (FastAPI, Uvicorn)
   - Database drivers (SQLAlchemy, psycopg)
   - Vector database client (Pinecone 5.0.0)
   - AI/ML libraries (Google Generative AI, sentence-transformers, PyTorch)
   - Testing frameworks (pytest, hypothesis)
   - HTTP and parsing tools (requests, feedparser, beautifulsoup4)
   
   PyTorch (~2GB) may take several minutes to download depending on your connection.

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials, API keys, etc.
   ```

4. **Initialize database**
   ```bash
   # Ensure PostgreSQL is running
   python scripts/init_db.py
   ```

5. **Run backend services**
   ```bash
   # Terminal 1: Start API server
   uvicorn app.main:app --reload --port 8000

   # Terminal 2: Start background worker
   python app/worker.py
   ```

#### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

```bash
# Start PostgreSQL (if not using Docker)
# Ensure PostgreSQL is running on localhost:5432

# Run backend API
uvicorn app.main:app --reload --port 8000

# Run background worker (in another terminal)
python app/worker.py
```

## Development

### Database Operations

```bash
# Initialize database
python scripts/init_db.py

# Reset database (DEVELOPMENT ONLY - deletes all data)
python scripts/reset_db.py
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run property-based tests only
pytest -m property

# Run specific test file
pytest tests/test_company_resolver.py

# Verify backend components (Task 16 checkpoint)
python tests/verify_backend.py
```

### API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration

Key environment variables (see `.env.example` for full list):

### Database Configuration
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql://user:password@localhost:5432/hpcl_leads`)

### Pinecone Configuration
- `PINECONE_API_KEY`: Pinecone API key for vector database access
- `PINECONE_ENVIRONMENT`: Pinecone environment (e.g., `us-west1-gcp`)
- `PINECONE_INDEX_NAME`: Pinecone index name (default: `hpcl-companies`)

### AI/ML Configuration
- `GEMINI_API_KEY`: Google Gemini API key for LLM-based entity extraction and classification
- `EMBEDDING_MODEL`: Sentence transformer model for embeddings (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `COMPANY_SIMILARITY_THRESHOLD`: Similarity threshold for company matching (default: `0.85`)

### WhatsApp Configuration (Optional)
- `WHATSAPP_API_URL`: WhatsApp Business API base URL (default: `https://graph.facebook.com/v18.0`)
- `WHATSAPP_ACCESS_TOKEN`: WhatsApp Business API access token
- `WHATSAPP_PHONE_NUMBER_ID`: WhatsApp phone number ID for sending messages

### Application Configuration
- `API_HOST`: API server host (default: `0.0.0.0`)
- `API_PORT`: API server port (default: `8000`)
- `FRONTEND_URL`: Frontend URL for CORS (default: `http://localhost:3000`)

### Worker Configuration
- `WORKER_POLL_INTERVAL_SECONDS`: Worker polling frequency in seconds (default: `10`)
- `SIGNAL_PROCESSING_TIMEOUT_MINUTES`: Max processing time per signal in minutes (default: `2`)

## Core Components

### Entity Extractor

The `EntityExtractor` (`app/services/entity_extractor.py`) extracts structured information from unstructured signal text using LLM:

**Key Features:**
- OpenAI GPT-4 integration with structured output (Pydantic models)
- Extracts company names with CIN/GST identifiers
- Extracts locations (city, state, country)
- Extracts dates, deadlines, and timelines
- Extracts capacity and scale information
- Identifies direct product keywords (FO, LDO, HSD, bitumen, etc.)
- Identifies operational cues (boiler, furnace, genset, etc.)
- Regex-based identifier extraction (CIN, GST patterns)
- Fallback to rule-based extraction when LLM unavailable

**Extracted Entity Types:**
- `CompanyMention`: Company name, CIN, GST, website, industry, address, locations
- `Location`: City, state, country, full location string
- `DateMention`: Date string, type (deadline/start/completion), parsed ISO date
- `Capacity`: Value, unit, type (production/investment/project size)
- Product keywords: Direct mentions of petroleum products
- Operational cues: Industrial equipment and processes

**API Methods:**
- `extract_entities(text, title)` - Extract all entities from signal text
- `extract_companies(text)` - Extract company mentions only
- `extract_location(text)` - Extract primary location
- `extract_dates(text)` - Extract dates and deadlines
- `extract_capacity(text)` - Extract capacity/scale information
- `extract_product_keywords(text)` - Find direct product keywords
- `extract_operational_cues(text)` - Find operational indicators

**Usage Example:**
```python
from app.services.entity_extractor import EntityExtractor

extractor = EntityExtractor()

# Extract all entities from signal
entities = extractor.extract_entities(
    text="ABC Industries Ltd (CIN: U12345AB2020PTC123456) is setting up a new boiler facility in Mumbai...",
    title="New Industrial Expansion"
)

# Access extracted information
for company in entities.companies:
    print(f"Company: {company.name}")
    print(f"CIN: {company.cin}")
    print(f"Locations: {company.locations}")

if entities.location:
    print(f"Location: {entities.location.city}, {entities.location.state}")

print(f"Product keywords: {entities.product_keywords}")
print(f"Operational cues: {entities.operational_cues}")

# Extract specific entity types
companies = extractor.extract_companies(text)
location = extractor.extract_location(text)
dates = extractor.extract_dates(text)
```

### Event Classifier

The `EventClassifier` (`app/services/event_classifier.py`) analyzes signals to determine if they represent business opportunities:

**Key Features:**
- Gemini LLM integration with structured output (Pydantic models)
- Lead-worthiness determination (filters out non-opportunities)
- Event type classification (tender, expansion, procurement, new_project, etc.)
- Intent strength scoring (0.0 to 1.0 scale)
- Location, capacity, and deadline extraction
- Reasoning generation explaining classification decisions
- Fallback to rule-based classification when LLM unavailable
- Comprehensive error handling with automatic fallback

**Classification Output:**

The classifier returns an `EventClassification` object with:
- `is_lead_worthy`: Boolean indicating if this represents a business opportunity
- `event_type`: Category like 'expansion', 'tender', 'procurement', 'new_project'
- `event_summary`: Brief 1-2 sentence summary of the business event
- `location`: Where the event is happening (if mentioned)
- `capacity`: Scale or size information (e.g., '500 MW', '10,000 sq ft')
- `deadline`: Deadline date in ISO format YYYY-MM-DD (if mentioned)
- `intent_strength`: Score from 0.0 to 1.0 indicating purchase intent
- `reasoning`: Brief explanation of the classification decision

**Intent Strength Scale:**
- **1.0**: Explicit tender or bid with clear requirements
- **0.7-0.9**: Announced expansion or project with details
- **0.4-0.6**: Planned or proposed project
- **0.1-0.3**: Vague mention or consideration

**Lead-Worthy Indicators:**
- Tenders, bids, procurement announcements
- Expansion plans, capacity additions
- New projects, construction activities
- Installations, modernization, upgrades
- New plants or facilities
- Investment announcements (capex)
- Commissioning activities

**Non-Lead Indicators:**
- Opinion pieces, editorials, analysis
- Historical articles, retrospectives
- Conferences, seminars, workshops
- Award ceremonies, celebrations
- Training events

**API Methods:**
- `classify_event(signal, company_name)` - Classify a signal and determine lead-worthiness
- `is_lead_worthy(signal)` - Quick check if signal is lead-worthy (returns boolean)
- `calculate_intent_strength(signal)` - Calculate intent strength score only

**Usage Example:**
```python
from app.services.event_classifier import EventClassifier
from app.db.session import get_db

# Initialize classifier
classifier = EventClassifier()

# Classify a signal
classification = classifier.classify_event(
    signal=signal,
    company_name="ABC Industries Ltd"
)

# Check results
if classification.is_lead_worthy:
    print(f"Lead-worthy event detected!")
    print(f"Type: {classification.event_type}")
    print(f"Summary: {classification.event_summary}")
    print(f"Intent strength: {classification.intent_strength:.2f}")
    print(f"Location: {classification.location}")
    print(f"Capacity: {classification.capacity}")
    print(f"Deadline: {classification.deadline}")
    print(f"Reasoning: {classification.reasoning}")
else:
    print(f"Not lead-worthy: {classification.reasoning}")

# Quick lead-worthiness check
if classifier.is_lead_worthy(signal):
    print("This signal represents a business opportunity")

# Get intent strength only
intent = classifier.calculate_intent_strength(signal)
print(f"Intent strength: {intent:.2f}")
```

**LLM-Based Classification:**

When Gemini API key is configured, the classifier uses LLM for intelligent analysis:

```python
# Classifier automatically uses LLM if API key is available
classifier = EventClassifier()  # Uses settings.gemini_api_key

# LLM analyzes:
# 1. Signal title and content
# 2. Company context (if provided)
# 3. Lead-worthy indicators vs non-lead indicators
# 4. Event type and category
# 5. Intent strength based on language and specificity
# 6. Extracts location, capacity, deadline from text
# 7. Generates human-readable reasoning

# Returns structured EventClassification object
classification = classifier.classify_event(signal)
```

**Rule-Based Classification (Fallback):**

When LLM is unavailable or fails, the classifier uses keyword-based heuristics:

```python
# Rule-based classification uses:
# - Keyword matching for lead-worthy indicators
# - Keyword matching for non-lead indicators
# - Score comparison to determine lead-worthiness
# - Simple intent strength calculation based on keywords
# - Event type inference from keywords

# Automatically falls back on LLM errors
classification = classifier.classify_event(signal)
```

**Integration with Pipeline:**

The Event Classifier is a critical stage in the background worker pipeline:

```python
from app.services.event_classifier import EventClassifier
from app.services.event_service import EventService

classifier = EventClassifier()
event_service = EventService(db)

# Stage 3 of pipeline: Classify event
classification = classifier.classify_event(
    signal=signal,
    company_name=company.name
)

# Create Event record
event = event_service.create_event(
    signal_id=signal.id,
    company_id=company.id,
    event_type=classification.event_type,
    event_summary=classification.event_summary,
    location=classification.location,
    capacity=classification.capacity,
    deadline=classification.deadline,
    intent_strength=classification.intent_strength,
    is_lead_worthy=classification.is_lead_worthy
)

# Stage 4: Check if lead-worthy
if not classification.is_lead_worthy:
    # Skip lead generation for non-opportunities
    mark_signal_as_processed(signal)
    return

# Continue to product inference and lead generation...
```

**Error Handling:**

```python
from app.services.event_classifier import EventClassifier

classifier = EventClassifier()

try:
    classification = classifier.classify_event(signal)
except RuntimeError as e:
    # Classification failed completely
    print(f"Classification error: {e}")
    # Handle error (retry, skip, etc.)

# LLM errors automatically fall back to rule-based
# No exception raised - fallback is transparent
```

**Configuration:**

Set Gemini API key in `.env`:

```bash
# AI/ML Configuration
GEMINI_API_KEY=your-gemini-api-key-here

# If not set, classifier uses rule-based classification only
```

**Performance Considerations:**

- LLM classification: ~1-3 seconds per signal (depends on API latency)
- Rule-based classification: <10ms per signal
- Automatic fallback ensures pipeline never blocks on LLM failures
- Structured output (JSON) ensures consistent parsing
- Temperature set to 0.3 for consistent, deterministic results

### Product Inference Engine

The `ProductInferenceEngine` (`app/services/product_inference.py`) maps business events to HPCL product recommendations:

**Key Features:**
- Comprehensive product keyword dictionary (FO, LDO, HSD, bitumen, bunker, solvents, etc.)
- Operational cue to product inference rules (boiler→FO, genset→HSD, road project→bitumen)
- Confidence scoring (0.0-1.0) based on match type and evidence strength
- Reasoning generation explaining each recommendation
- Top-N product selection (default: top 3)
- Multiple evidence source support (keywords + operational cues)

**HPCL Products Supported:**
- Furnace Oil (FO)
- Light Diesel Oil (LDO)
- High Speed Diesel (HSD)
- Low Sulphur Heavy Stock (LSHS)
- Bitumen
- Bunker Fuel
- Marine Diesel Oil
- Hexane
- Industrial Solvents
- Jute Batching Oil
- Steel Wash Oil
- Liquefied Petroleum Gas (LPG)

**Inference Rules Examples:**
- Boiler/Furnace → FO (85% confidence), LDO (75% confidence)
- Genset/Generator → HSD (90% confidence), LDO (70% confidence)
- Road Project/Highway → Bitumen (90% confidence), HSD (80% confidence)
- Shipping/Port/Vessel → Bunker Fuel (85% confidence), Marine Diesel (80% confidence)
- Jute Mill → Jute Batching Oil (95% confidence)
- Steel Plant → Wash Oil (90% confidence), FO (80% confidence)
- Warehouse/Logistics → HSD (85-90% confidence)

**Confidence Levels:**
- Direct keyword match: 90-100%
- Strong operational cue: 70-89%
- Weak operational cue: 50-69%
- Speculative inference: 30-49%

**API Methods:**
- `infer_products(text, keywords, cues, top_n)` - Generate top N product recommendations
- `apply_keyword_rules(text)` - Apply direct keyword matching
- `apply_operational_rules(cues)` - Apply operational cue inference
- `calculate_confidence(match, context)` - Calculate/adjust confidence scores
- `generate_reasoning(match)` - Generate human-readable reasoning
- `get_product_name(code)` - Get full product name from code
- `get_all_products()` - Get all available products

**ProductMatch Data Structure:**

Each product recommendation is returned as a `ProductMatch` object with the following fields:
- `product_name`: Full HPCL product name (e.g., "High Speed Diesel")
- `confidence`: Confidence score (0.0 to 1.0)
- `reason_code`: Match type ('keyword_match', 'operational_cue', 'inference')
- `reasoning`: Human-readable explanation for the recommendation
- `keywords_found`: List of direct product keywords that triggered this match
- `cues_found`: List of operational cues that support this match
- `uncertainty_flag`: Boolean flag set to `True` when confidence < 60% (indicates low-confidence recommendations that may need review)

**Usage Example:**
```python
from app.services.product_inference import ProductInferenceEngine

engine = ProductInferenceEngine()

# Infer products from extracted entities
product_keywords = ['diesel', 'bitumen']
operational_cues = ['road project', 'genset']

recommendations = engine.infer_products(
    text=signal_text,
    product_keywords=product_keywords,
    operational_cues=operational_cues,
    top_n=3
)

for match in recommendations:
    print(f"Product: {match.product_name}")
    print(f"Confidence: {match.confidence:.2%}")
    print(f"Reasoning: {match.reasoning}")
    print(f"Keywords: {match.keywords_found}")
    print(f"Cues: {match.cues_found}")
    print(f"Reason Code: {match.reason_code}")
    
    # Check uncertainty flag for low-confidence recommendations
    if match.uncertainty_flag:
        print(f"⚠️ Low confidence - may need manual review")
```

### Signal Service

The `SignalService` (`app/services/signal_service.py`) manages signal ingestion and CRUD operations:

**Key Features:**
- Create and store signals from various sources (RSS, API, web scraping)
- Track signal processing status (processed/unprocessed)
- Query signals by URL, source, processing status, or time range
- Bulk signal creation for batch ingestion
- Provenance tracking for compliance and debugging

**API Methods:**
- `create_signal()` - Create a new signal with URL, content, title, source, and provenance
- `get_signal_by_id()` - Retrieve signal by UUID
- `get_signal_by_url()` - Retrieve signal by URL
- `list_signals()` - List signals with filters (processed status, source, pagination)
- `get_unprocessed_signals()` - Get signals ready for background worker processing
- `mark_as_processed()` - Mark signal as processed after pipeline completion
- `update_signal()` - Update signal fields (title, content, processed status)
- `delete_signal()` - Remove signal from database
- `count_signals()` - Count signals with optional filters
- `bulk_create_signals()` - Create multiple signals in a single transaction
- `get_signals_by_source()` - Get all signals from a specific source
- `signal_exists()` - Check if URL already exists (deduplication)
- `get_recent_signals()` - Get signals ingested within last N hours

**Usage Example:**
```python
from app.services.signal_service import SignalService
from app.db.session import get_db

db = next(get_db())
service = SignalService(db)

# Create a new signal
signal = service.create_signal(
    url="https://example.com/article",
    content="Company XYZ announces new facility...",
    title="New Manufacturing Plant",
    source_id=source_uuid,
    provenance={
        "method": "rss",
        "fetched_at": "2024-01-15T10:30:00Z",
        "rate_limit_waited": 0.5
    }
)

# Check for duplicates before creating
if not service.signal_exists(url):
    signal = service.create_signal(url=url, content=content)

# Get unprocessed signals for worker
unprocessed = service.get_unprocessed_signals(limit=50)
for signal in unprocessed:
    # Process signal through pipeline...
    service.mark_as_processed(signal.id)

# Bulk create signals from RSS feed
signals_data = [
    {"url": url1, "content": content1, "title": title1},
    {"url": url2, "content": content2, "title": title2}
]
signals = service.bulk_create_signals(signals_data)

# Get recent signals for monitoring
recent = service.get_recent_signals(hours=24, processed=False)
```

### Ingestion Service

The `IngestionService` (`app/services/ingestion.py`) handles signal collection from public sources:

**Key Features:**
- RSS/Atom feed parsing with feedparser
- API-based content fetching with configurable authentication and pagination
- Automatic retry logic for transient failures (3 retries with exponential backoff)
- Automatic source registration for new domains
- Graceful error handling - individual feed/API failures don't stop processing
- Content extraction from multiple feed formats (Atom, RSS 2.0, RSS 1.0)
- Flexible API response parsing (list, nested data fields, single items)
- Timestamp extraction from published/updated fields
- Provenance tracking for compliance and debugging
- Integration with Policy Checker for rate limiting

**API Methods:**
- `fetch_rss_feeds(feed_urls)` - Fetch and parse multiple RSS/Atom feeds, returns list of Signal objects
- `fetch_from_api(api_config)` - Fetch content from API endpoint with optional pagination
- `_parse_single_feed(feed_url)` - Parse a single feed and extract signals
- `_create_signal_from_entry(entry, source, feed_url)` - Convert feed entry to Signal object
- `_extract_content(entry)` - Extract content from feed entry (tries content, summary, description fields)
- `_extract_timestamp(entry)` - Extract publication timestamp from feed entry
- `_get_or_create_source(feed_url, access_method)` - Get or create Source for feed domain

**APIConfig Class:**

Configure API-based content fetching with flexible authentication and pagination:

```python
from app.services.ingestion import APIConfig

# Basic API configuration
config = APIConfig(
    base_url='https://api.example.com',
    endpoint='data',
    method='GET'
)

# With authentication (basic auth)
config = APIConfig(
    base_url='https://api.example.com',
    endpoint='protected',
    auth=('username', 'password')
)

# With bearer token authentication
config = APIConfig(
    base_url='https://api.example.com',
    auth_token='your-secret-token'
)

# With custom headers and query parameters
config = APIConfig(
    base_url='https://api.example.com',
    endpoint='items',
    headers={'X-API-Key': 'secret-key'},
    params={'category': 'news', 'limit': 50}
)

# With pagination support
config = APIConfig(
    base_url='https://api.example.com',
    endpoint='items',
    pagination_param='page',  # Parameter name for page number
    max_pages=10  # Maximum pages to fetch
)
```

**Usage Examples:**

```python
from app.services.ingestion import IngestionService, APIConfig
from app.services.policy_checker import PolicyChecker
from app.db.session import get_db

db = next(get_db())
policy_checker = PolicyChecker()
service = IngestionService(db, policy_checker)

# Fetch signals from multiple RSS feeds
feed_urls = [
    "https://example.com/news/rss",
    "https://tenders.gov.in/feed",
    "https://industry-news.com/atom.xml"
]

signals = service.fetch_rss_feeds(feed_urls)

# Signals are returned as Signal objects (not yet persisted)
for signal in signals:
    db.add(signal)
db.commit()

# Fetch from API endpoint
api_config = APIConfig(
    base_url='https://api.newssite.com',
    endpoint='articles',
    auth_token='your-api-token',
    params={'category': 'business', 'limit': 100}
)

api_signals = service.fetch_from_api(api_config)
for signal in api_signals:
    db.add(signal)
db.commit()

# Fetch from paginated API
paginated_config = APIConfig(
    base_url='https://api.tenders.gov.in',
    endpoint='tenders',
    pagination_param='page',
    max_pages=5,
    headers={'Authorization': 'Bearer token'}
)

paginated_signals = service.fetch_from_api(paginated_config)

# Service handles errors gracefully - if one feed/API fails, others continue
```

### Pinecone Client

The `PineconeClient` (`app/db/pinecone_client.py`) manages vector database operations for semantic company matching:

**Key Features:**
- Automatic index creation with 384-dimensional vectors (all-MiniLM-L6-v2)
- Cosine similarity metric for semantic matching
- Namespace support for data isolation (default: "companies")
- Metadata filtering for advanced queries
- Threshold-based result filtering (default: 0.85)
- Company embedding CRUD operations (upsert, search, delete)
- Index statistics and monitoring

**API Methods:**
- `get_index()` - Get or create Pinecone index with auto-configuration
- `upsert_company_embedding(company_id, embedding, metadata, namespace)` - Store company embedding with metadata
- `search_similar_companies(embedding, top_k, threshold, namespace, metadata_filter)` - Search for similar companies with optional filtering
- `delete_company_embedding(company_id, namespace)` - Remove company embedding from index
- `get_index_stats()` - Get index statistics (vector count, dimension, etc.)

**Index Configuration:**
- Dimension: 384 (matches all-MiniLM-L6-v2 model)
- Metric: Cosine similarity
- Cloud: AWS Serverless
- Region: us-west-2 (configurable)
- Default namespace: "companies"

**Usage Examples:**

```python
from app.db.pinecone_client import pinecone_client

# Store company embedding
pinecone_client.upsert_company_embedding(
    company_id=str(company.id),
    embedding=embedding.tolist(),  # Convert numpy array to list
    metadata={
        "company_id": str(company.id),
        "company_name": "ABC Industries Ltd",
        "name_variants": ["ABC Ltd", "ABC Corp"],
        "industry": "Manufacturing"
    },
    namespace="companies"
)

# Search for similar companies
matches = pinecone_client.search_similar_companies(
    embedding=query_embedding.tolist(),
    top_k=5,
    threshold=0.85,
    namespace="companies"
)

for match in matches:
    print(f"Company: {match.metadata['company_name']}")
    print(f"Similarity: {match.score:.3f}")
    print(f"ID: {match.id}")

# Search with metadata filtering
matches = pinecone_client.search_similar_companies(
    embedding=query_embedding.tolist(),
    top_k=10,
    threshold=0.80,
    namespace="companies",
    metadata_filter={"industry": "Manufacturing"}
)

# Delete company embedding
pinecone_client.delete_company_embedding(
    company_id=str(company.id),
    namespace="companies"
)

# Get index statistics
stats = pinecone_client.get_index_stats()
print(f"Total vectors: {stats.total_vector_count}")
print(f"Namespaces: {stats.namespaces}")
```

**Integration with Company Resolver:**

The Company Resolver uses the Pinecone client for semantic matching:

```python
from app.services.company_resolver import CompanyResolver
from app.db.session import get_db

db = next(get_db())
resolver = CompanyResolver(db)

# Resolve company with semantic matching
company = resolver.resolve_company(
    company_name="ABC Industries Ltd",
    name_variants=["ABC Ltd", "ABC Corp"],
    industry="Manufacturing"
)

# Behind the scenes:
# 1. Generate embedding for company name + variants
# 2. Search Pinecone for similar companies (threshold 0.85)
# 3. If match found, link to existing company
# 4. If no match, create new company and store embedding
```

**Metadata Filtering:**

Pinecone supports metadata filtering for advanced queries:

```python
# Filter by industry
matches = pinecone_client.search_similar_companies(
    embedding=embedding,
    metadata_filter={"industry": "Manufacturing"}
)

# Filter by multiple criteria (AND logic)
matches = pinecone_client.search_similar_companies(
    embedding=embedding,
    metadata_filter={
        "industry": "Manufacturing",
        "name_variants": {"$contains": "Ltd"}
    }
)
```

**Error Handling:**

```python
from pinecone.exceptions import PineconeException

try:
    matches = pinecone_client.search_similar_companies(
        embedding=embedding,
        threshold=0.85
    )
except PineconeException as e:
    print(f"Pinecone error: {e}")
    # Handle error (retry, fallback, etc.)
```

**Configuration:**

Set these environment variables in `.env`:

```bash
# Pinecone configuration
PINECONE_API_KEY=your-api-key-here
PINECONE_INDEX_NAME=hpcl-companies
COMPANY_SIMILARITY_THRESHOLD=0.85
```

### Embedding Generator

The `EmbeddingGenerator` (`app/utils/embeddings.py`) generates semantic embeddings for text using sentence-transformers:

**Key Features:**
- Uses all-MiniLM-L6-v2 model (384-dimensional embeddings)
- Lazy model loading for efficient memory usage
- Batch embedding generation with configurable batch size
- Company name embedding with variant support (mean of all variants)
- Cosine similarity calculation for semantic matching
- Automatic normalization for consistent similarity scores
- Singleton pattern for model reuse across application
- Comprehensive error handling and logging

**Model Specifications:**
- Model: `all-MiniLM-L6-v2` (sentence-transformers)
- Embedding dimension: 384
- Optimized for semantic similarity tasks
- Normalized embeddings (L2 norm = 1)
- Cosine similarity range: -1.0 to 1.0

**API Methods:**
- `generate_embedding(text, normalize=True)` - Generate embedding for single text string
- `generate_embeddings(texts, normalize=True, batch_size=32)` - Generate embeddings for multiple texts
- `generate_company_embedding(company_name, name_variants=None)` - Generate company embedding with optional variants
- `calculate_similarity(embedding1, embedding2)` - Calculate cosine similarity between two embeddings
- `get_embedding_generator(model_name=None)` - Get singleton instance (factory function)

**Usage Examples:**

```python
from app.utils.embeddings import get_embedding_generator

# Get singleton instance
generator = get_embedding_generator()

# Generate single embedding
text = "ABC Industries Ltd"
embedding = generator.generate_embedding(text)
print(f"Embedding shape: {embedding.shape}")  # (384,)

# Generate multiple embeddings (batch processing)
texts = ["ABC Industries", "XYZ Corporation", "DEF Ltd"]
embeddings = generator.generate_embeddings(texts, batch_size=32)
print(f"Embeddings shape: {embeddings.shape}")  # (3, 384)

# Generate company embedding with name variants
company_name = "ABC Industries Ltd"
variants = ["ABC Ltd", "ABC Corp", "ABC Industries"]
company_embedding = generator.generate_company_embedding(
    company_name,
    name_variants=variants
)
# Returns mean of all variant embeddings, normalized

# Calculate similarity between two companies
emb1 = generator.generate_embedding("ABC Industries Ltd")
emb2 = generator.generate_embedding("ABC Industries Limited")
similarity = generator.calculate_similarity(emb1, emb2)
print(f"Similarity: {similarity:.3f}")  # 0.950 (high similarity)

# Use in company matching
threshold = 0.85
if similarity >= threshold:
    print("Companies are likely the same entity")
```

**Integration with Company Resolver:**

The `CompanyResolver` uses the embedding generator for semantic company matching:

```python
from app.services.company_resolver import CompanyResolver
from app.db.session import get_db

db = next(get_db())
resolver = CompanyResolver(db)

# Generate embedding for new company
company_name = "ABC Industries Ltd"
variants = ["ABC Ltd", "ABC Corp"]

embedding, embedding_id = resolver.generate_embedding(
    company_name,
    name_variants=variants
)

# embedding_id format: "company_<16-char-hex>"
# Used as Pinecone vector ID for semantic search
```

**Error Handling:**

```python
from app.utils.embeddings import EmbeddingGenerator

generator = EmbeddingGenerator()

# Empty text raises ValueError
try:
    embedding = generator.generate_embedding("")
except ValueError as e:
    print(f"Error: {e}")  # "Text cannot be empty"

# Empty list raises ValueError
try:
    embeddings = generator.generate_embeddings([])
except ValueError as e:
    print(f"Error: {e}")  # "Texts list cannot be empty"

# Model loading errors raise RuntimeError
try:
    _ = generator.model
except RuntimeError as e:
    print(f"Error: {e}")  # "Failed to load embedding model: ..."

# Mismatched embedding shapes raise ValueError
try:
    emb1 = np.random.rand(384)
    emb2 = np.random.rand(256)
    similarity = generator.calculate_similarity(emb1, emb2)
except ValueError as e:
    print(f"Error: {e}")  # "Embedding shapes must match: (384,) vs (256,)"
```

**Performance Considerations:**

- Model is loaded lazily on first use (not at initialization)
- Singleton pattern ensures model is loaded only once per application
- Batch processing is more efficient than individual calls for multiple texts
- Normalized embeddings enable fast cosine similarity via dot product
- Default batch size of 32 balances memory usage and throughput

**Dependencies:**

```bash
# Required packages
pip install sentence-transformers numpy

# sentence-transformers will automatically download the model on first use
# Model size: ~90MB (cached in ~/.cache/torch/sentence_transformers/)
```

### Event Service

The `EventService` (`app/services/event_service.py`) manages Event entities with CRUD operations:

**Key Features:**
- Create and store classified business events from signals
- Link events to signals and companies
- Track lead-worthiness and intent strength
- Query events by signal, company, or lead-worthiness
- Update event classification and metadata
- Count and filter events for analytics

**Event Fields:**
- `signal_id`: UUID of the source signal
- `company_id`: Optional UUID of associated company
- `event_type`: Event category (expansion, tender, procurement, new_project, etc.)
- `event_summary`: Brief summary of the business event
- `location`: Location where the event is taking place
- `capacity`: Capacity, scale, or size information
- `deadline`: Deadline or timeline (datetime)
- `intent_strength`: Intent strength score (0.0 to 1.0)
- `is_lead_worthy`: Whether this event represents a business opportunity

**API Methods:**
- `create_event(signal_id, event_summary, company_id, event_type, location, capacity, deadline, intent_strength, is_lead_worthy)` - Create new Event
- `get_event_by_id(event_id)` - Retrieve event by UUID
- `get_events_by_signal(signal_id)` - Get all events for a signal
- `get_events_by_company(company_id)` - Get all events for a company
- `get_lead_worthy_events(limit, offset)` - Get all lead-worthy events with pagination
- `update_event(event_id, **kwargs)` - Update event fields
- `delete_event(event_id)` - Remove event from database
- `count_events(lead_worthy_only, company_id)` - Count events with optional filters

**Usage Example:**
```python
from app.services.event_service import EventService
from app.services.event_classifier import EventClassifier
from app.db.session import get_db
from datetime import datetime

db = next(get_db())
event_service = EventService(db)
classifier = EventClassifier()

# Classify a signal
classification = classifier.classify_event(signal, company_name="ABC Industries")

# Create event from classification
event = event_service.create_event(
    signal_id=signal.id,
    event_summary=classification.event_summary,
    company_id=company.id,
    event_type=classification.event_type,
    location=classification.location,
    capacity=classification.capacity,
    deadline=datetime.fromisoformat(classification.deadline) if classification.deadline else None,
    intent_strength=classification.intent_strength,
    is_lead_worthy=classification.is_lead_worthy
)

# Query lead-worthy events
lead_worthy_events = event_service.get_lead_worthy_events(limit=50, offset=0)

for event in lead_worthy_events:
    print(f"Event: {event.event_summary}")
    print(f"Type: {event.event_type}")
    print(f"Intent: {event.intent_strength:.2f}")
    print(f"Company: {event.company_id}")

# Get all events for a company
company_events = event_service.get_events_by_company(company.id)

# Update event classification
event_service.update_event(
    event_id=event.id,
    is_lead_worthy=True,
    intent_strength=0.95,
    event_type="tender"
)

# Count lead-worthy events
lead_count = event_service.count_events(lead_worthy_only=True)
print(f"Total lead-worthy events: {lead_count}")

# Count events for specific company
company_event_count = event_service.count_events(company_id=company.id)
print(f"Events for company: {company_event_count}")
```

**Integration with Event Classifier:**

The Event Service works closely with the Event Classifier to store classification results:

```python
from app.services.event_classifier import EventClassifier
from app.services.event_service import EventService

classifier = EventClassifier()
event_service = EventService(db)

# Classify signal
classification = classifier.classify_event(signal)

# Store classification as event
if classification.is_lead_worthy:
    event = event_service.create_event(
        signal_id=signal.id,
        event_summary=classification.event_summary,
        event_type=classification.event_type,
        location=classification.location,
        capacity=classification.capacity,
        deadline=parse_deadline(classification.deadline),
        intent_strength=classification.intent_strength,
        is_lead_worthy=True
    )
```

**Filtering and Pagination:**

```python
# Get first 50 lead-worthy events
page1 = event_service.get_lead_worthy_events(limit=50, offset=0)

# Get next 50 lead-worthy events
page2 = event_service.get_lead_worthy_events(limit=50, offset=50)

# Get all events for a signal (typically 1, but could be multiple)
signal_events = event_service.get_events_by_signal(signal.id)

# Count events with filters
total_leads = event_service.count_events(lead_worthy_only=True)
company_leads = event_service.count_events(
    lead_worthy_only=True,
    company_id=company.id
)
```

### Background Worker

The `BackgroundWorker` (`app/worker.py`) orchestrates the complete signal-to-lead pipeline:

**Key Features:**
- Continuous polling of PostgreSQL for unprocessed signals
- Complete 7-stage pipeline from signal ingestion to lead generation
- Robust error handling with retry logic for transient failures
- Exponential backoff for failed operations (1s → 2s → 4s, max 60s)
- Failed signal tracking for manual review
- Graceful handling of individual signal failures (doesn't stop pipeline)
- Comprehensive logging at each pipeline stage
- Processing time tracking for performance monitoring

**Pipeline Stages:**
1. **Poll Database** - Retrieves unprocessed signals from PostgreSQL (batch of 100)
2. **Extract Entities** - Uses EntityExtractor to identify companies, locations, products, operational cues
3. **Resolve Company** - Semantic matching via CompanyResolver and Pinecone
4. **Classify Event** - Determines lead-worthiness and intent strength via EventClassifier
5. **Infer Products** - Maps business events to HPCL products (top 3 recommendations)
6. **Score & Route** - Calculates lead score (0-100), assigns priority, routes to territory
7. **Create Lead** - Generates Lead record with product recommendations in PostgreSQL

**Error Handling:**

The worker classifies errors into two categories:

**Transient Errors** (retried with exponential backoff):
- Network timeouts and connection errors
- Database connection issues (OperationalError)
- API rate limits (RateLimitError)
- API timeouts (APITimeoutError)
- 5xx server errors from external APIs

**Permanent Errors** (logged for manual review):
- Parsing errors
- Validation failures
- 4xx client errors
- Business logic failures

**Retry Strategy:**
- Maximum 3 retry attempts per signal
- Exponential backoff: 1s → 2s → 4s (capped at 60s)
- Automatic database rollback and fresh session on retry
- Failed signals queued for manual review after max retries

**Configuration:**

Worker behavior controlled via environment variables in `.env`:

```bash
# Worker configuration
WORKER_POLL_INTERVAL_SECONDS=10  # How often to check for new signals
SIGNAL_PROCESSING_TIMEOUT_MINUTES=2  # Max processing time per signal

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/hpcl_leads

# AI/ML
OPENAI_API_KEY=your-openai-key  # For entity extraction and classification

# Pinecone
PINECONE_API_KEY=your-pinecone-key  # For company matching
PINECONE_INDEX_NAME=hpcl-companies
```

**Running the Worker:**

```bash
# Run worker directly
python app/worker.py

# Or via Docker Compose (when configured)
docker-compose up worker

# Run in background (Linux/Mac)
nohup python app/worker.py > worker.log 2>&1 &

# Run in background (Windows)
start /B python app/worker.py
```

**Monitoring:**

The worker provides comprehensive logging:

```python
# INFO: Batch summaries, successful processing, routing decisions
# Example: "Found 15 unprocessed signals"
# Example: "Batch complete: 14 processed, 1 failed"

# WARNING: Transient errors, retry attempts, failed signals count
# Example: "[signal-123] Transient error on attempt 1/3: Connection timeout. Retrying in 1.0s..."

# ERROR: Permanent failures, unexpected errors, detailed stack traces
# Example: "[signal-456] Permanent error after 3 attempts: Invalid JSON response"

# DEBUG: Individual pipeline stages, entity extraction results
# Example: "[signal-789] Stage 1: Extracting entities"
# Example: "[signal-789] Resolved to company: ABC Industries Ltd"
```

**Failed Signal Management:**

The worker tracks failed signals for manual review:

```python
from app.worker import BackgroundWorker

worker = BackgroundWorker()

# Get all failed signals
failed = worker.get_failed_signals()
# Returns: Dict[signal_id, failure_info]

# Each failure_info contains:
# - signal_id: UUID of failed signal
# - url: Source URL
# - error: Error message
# - error_type: Exception class name
# - attempts: Number of retry attempts made
# - timestamp: When failure occurred
# - title: Signal title

# Clear failed signals queue after manual review
worker.clear_failed_signals()
```

**Usage Example:**

```python
from app.worker import BackgroundWorker

# Initialize and run worker
worker = BackgroundWorker()
worker.run()

# Worker will continuously:
# 1. Poll for unprocessed signals every 10 seconds (configurable)
# 2. Process each signal through the 7-stage pipeline
# 3. Retry transient failures with exponential backoff
# 4. Log permanent failures for manual review
# 5. Continue processing other signals on individual failures
# 6. Handle graceful shutdown on Ctrl+C
```

**Integration with Services:**

The worker integrates with all core services:

```python
# Services used by worker:
from app.services.signal_service import SignalService  # Database operations
from app.services.entity_extractor import EntityExtractor  # LLM-based extraction
from app.services.company_resolver import CompanyResolver  # Semantic matching
from app.services.event_classifier import EventClassifier  # Lead-worthiness
from app.services.product_inference import ProductInferenceEngine  # Product recommendations
from app.services.lead_scorer import LeadScorer  # Scoring and routing
from app.services.event_service import EventService  # Event management

# Each service is initialized once in __init__ for efficiency
# Database sessions are managed per batch for transaction safety
```

**Performance Considerations:**

- Batch processing: 100 signals per poll (configurable)
- Configurable poll interval balances responsiveness vs load
- Processing timeout prevents hanging on slow operations
- Efficient database queries via service layer
- Connection pooling handled by SQLAlchemy
- Lazy loading of AI models (loaded once, reused)

**Error Recovery:**

The worker is designed for resilience:

```python
# Database connection errors don't crash worker
# Example: PostgreSQL temporarily unavailable
# Worker logs error and retries on next poll

# Individual signal failures don't stop batch processing
# Example: Signal 1 fails, signals 2-100 still processed

# Unexpected errors in main loop don't crash worker
# Example: Unhandled exception caught, logged, worker continues

# Graceful shutdown on KeyboardInterrupt
# Example: Ctrl+C stops worker cleanly, logs final summary
```

**Testing:**

```bash
# Run worker tests
pytest tests/unit/test_worker.py

# Test with mock signals
pytest tests/integration/test_worker_pipeline.py

# Property-based tests (optional)
pytest tests/property/test_lead_generation_timeliness.py
```

**Next Steps:**

The worker is ready for:
- Task 14: FastAPI REST endpoints to expose leads
- Task 15: WhatsApp notification integration (TODO in worker)
- Deployment: Docker Compose configuration for worker service

### Feedback Service

The `FeedbackService` (`app/services/feedback_service.py`) manages lead feedback collection and source trust score updates:

**Key Features:**
- Collect feedback from sales officers on lead quality
- Three feedback types: accepted, rejected, converted
- Automatic source trust score updates based on feedback
- Feedback history tracking per lead
- Feedback statistics and analytics
- Optional notes and submitter tracking

**Feedback Types:**
- `accepted`: Lead was valid and pursued (trust score +1)
- `rejected`: Lead was not relevant (trust score -1)
- `converted`: Lead resulted in a sale (trust score +2)

**Feedback Model Fields:**
- `id`: UUID primary key
- `lead_id`: UUID of the associated lead (foreign key)
- `feedback_type`: Type of feedback (accepted/rejected/converted)
- `notes`: Optional text notes from sales officer
- `submitted_at`: Timestamp when feedback was submitted
- `submitted_by`: Optional sales officer ID/name

**API Methods:**
- `submit_feedback(lead_id, feedback_type, notes, submitted_by)` - Submit feedback and update source trust
- `get_feedback_for_lead(lead_id)` - Get all feedback for a specific lead
- `get_feedback_stats(submitted_by)` - Get feedback statistics (counts by type)

**Usage Example:**
```python
from app.services.feedback_service import FeedbackService
from app.db.session import get_db

db = next(get_db())
service = FeedbackService(db)

# Submit accepted feedback
feedback = service.submit_feedback(
    lead_id=lead.id,
    feedback_type='accepted',
    notes='Good lead, contacted customer',
    submitted_by='John Doe'
)

# Submit converted feedback (highest trust boost)
feedback = service.submit_feedback(
    lead_id=lead.id,
    feedback_type='converted',
    notes='Deal closed - 500L FO order',
    submitted_by='Jane Smith'
)

# Submit rejected feedback
feedback = service.submit_feedback(
    lead_id=lead.id,
    feedback_type='rejected',
    notes='Company already has supplier',
    submitted_by='John Doe'
)

# Get all feedback for a lead
feedbacks = service.get_feedback_for_lead(lead.id)
for fb in feedbacks:
    print(f"{fb.feedback_type}: {fb.notes} by {fb.submitted_by}")

# Get feedback statistics for a sales officer
stats = service.get_feedback_stats(submitted_by='John Doe')
print(f"Accepted: {stats['accepted']}")
print(f"Rejected: {stats['rejected']}")
print(f"Converted: {stats['converted']}")
print(f"Total: {stats['total']}")

# Get overall feedback statistics
all_stats = service.get_feedback_stats()
```

**Integration with Source Trust Scoring:**

When feedback is submitted, the service automatically:
1. Traverses the relationship chain: Lead → Event → Signal → Source
2. Updates the source's trust score using the feedback type
3. Recalculates the trust tier (high/medium/low/neutral)

```python
# Behind the scenes when you submit feedback:
feedback = service.submit_feedback(
    lead_id=lead.id,
    feedback_type='converted'
)

# Automatically triggers:
# 1. Create Feedback record
# 2. Find source via: lead.event.signal.source_id
# 3. Call source_registry.update_trust_score(source_id, 'converted')
# 4. Recalculate trust score from all feedback history
# 5. Update trust tier based on new score
```

**Error Handling:**
```python
from app.services.feedback_service import FeedbackService

service = FeedbackService(db)

# Invalid feedback type raises ValueError
try:
    service.submit_feedback(
        lead_id=lead.id,
        feedback_type='invalid'
    )
except ValueError as e:
    print(f"Error: {e}")  # "Invalid feedback type. Must be one of: ['accepted', 'rejected', 'converted']"

# Non-existent lead raises ValueError
try:
    service.submit_feedback(
        lead_id=uuid.uuid4(),
        feedback_type='accepted'
    )
except ValueError as e:
    print(f"Error: {e}")  # "Lead with ID ... not found"
```

**Feedback Model CRUD Operations:**

The `Feedback` model (`app/models/feedback.py`) provides direct database operations:

```python
from app.models.feedback import Feedback

# Create feedback directly
feedback = Feedback.create(
    db=db,
    lead_id=lead.id,
    feedback_type='accepted',
    notes='Good lead',
    submitted_by='John Doe'
)

# Get feedback by ID
feedback = Feedback.get_by_id(db, feedback_id)

# Get all feedback for a lead
feedbacks = Feedback.get_by_lead_id(db, lead_id)

# List feedback with filters
feedbacks = Feedback.list_feedback(
    db=db,
    feedback_type='converted',
    submitted_by='John Doe',
    limit=50,
    offset=0
)

# Count feedback by type
accepted_count = Feedback.count_by_type(
    db=db,
    feedback_type='accepted',
    submitted_by='John Doe'
)
```

### Source Registry Manager

The `SourceRegistryManager` (`app/services/source_registry.py`) manages data sources and their trust scores:

**Key Features:**
- Register and manage data sources (news sites, tender portals, company pages)
- Dynamic trust scoring based on sales officer feedback (0-100 scale)
- Automatic trust tier assignment (high/medium/low/neutral)
- Source filtering by category and trust tier
- Track crawl frequency and robots.txt compliance status

**Trust Score Calculation:**
- Formula: `(Accepted + Converted × 2) / Total Feedback × 100`
- Neutral starting score: 50.0 (no feedback yet)
- Recalculated from all historical feedback on each update
- Clamped to 0-100 range

**Trust Tiers:**
- High: score ≥ 70
- Medium: 40 ≤ score < 70
- Low: 0 < score < 40
- Neutral: score = 0 (no feedback)

**API Methods:**
- `register_source()` - Add new source to registry
- `get_source_by_domain()` - Retrieve source by domain name
- `get_source_by_id()` - Retrieve source by ID
- `list_sources()` - List sources with optional filters
- `update_last_crawled()` - Update crawl timestamp
- `update_robots_txt_status()` - Update robots.txt compliance
- `update_crawl_frequency()` - Adjust crawl frequency
- `calculate_trust_score()` - Compute score from feedback history
- `calculate_trust_tier()` - Map score to tier
- `update_trust_score()` - Recalculate and update trust metrics
- `get_sources_by_trust_tier()` - Filter by trust tier
- `delete_source()` - Remove source from registry

**Usage Example:**
```python
from app.services.source_registry import SourceRegistryManager
from app.db.session import get_db

db = next(get_db())
manager = SourceRegistryManager(db)

# Register a new source
source = manager.register_source(
    domain="example.com",
    category="news",
    access_method="rss",
    crawl_frequency_minutes=60,
    robots_txt_allowed=True
)

# Update trust score after feedback
manager.update_trust_score(
    source_id=source.id,
    feedback_type="converted"
)

# List high-trust sources
high_trust_sources = manager.list_sources(trust_tier="high")

# Update crawl settings
manager.update_crawl_frequency(source.id, minutes=30)
manager.update_robots_txt_status(source.id, allowed=True)
```

## Project Structure

```
.
├── app/
│   ├── models/          # SQLAlchemy database models
│   │   ├── feedback.py  # Feedback model for lead quality tracking
│   │   ├── lead.py      # Lead model
│   │   ├── source.py    # Source model
│   │   └── ...
│   ├── services/        # Business logic layer
│   │   ├── feedback_service.py  # Feedback collection and trust updates
│   │   ├── source_registry.py   # Source trust management
│   │   └── ...
│   ├── api/             # FastAPI route handlers
│   ├── db/              # Database configuration
│   ├── utils/           # Shared utilities
│   ├── main.py          # FastAPI application
│   └── worker.py        # Background worker
├── tests/
│   ├── unit/            # Unit tests
│   │   ├── test_feedback_service.py  # Feedback service tests
│   │   ├── test_source_registry.py
│   │   └── ...
│   ├── property/        # Property-based tests
│   └── integration/     # Integration tests
├── scripts/
│   ├── init_db.py       # Database initialization
│   └── reset_db.py      # Database reset
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## License

Proprietary - HPCL Internal Use Only
