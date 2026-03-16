"""FastAPI application entry point.

NOTE: This is a portfolio/hackathon demo. Before any production use:
  - Add authentication (JWT or API key) to all endpoints
  - Add rate limiting (e.g. slowapi)
  - Replace all placeholder credentials with secrets manager
  - Enforce HTTPS
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.utils.config import settings
from app.api import leads, companies, sources, dashboard

app = FastAPI(
    title="HPCL Lead Intelligence Agent",
    description="AI-powered business opportunity discovery for HPCL sales teams",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leads.router)
app.include_router(companies.router)
app.include_router(sources.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "HPCL Lead Intelligence Agent API"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
