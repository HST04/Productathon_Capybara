"""Source management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.api.dependencies import get_db
from app.api.schemas import (
    SourceListResponse,
    SourceResponse,
    SourceUpdate,
    ErrorResponse
)
from app.models.source import Source

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("/", response_model=SourceListResponse)
def list_sources(
    category: Optional[str] = Query(None, description="Filter by category: news, tender, company_site"),
    trust_tier: Optional[str] = Query(None, description="Filter by trust tier: high, medium, low, neutral"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """
    List source registry with optional filters and pagination.
    
    Returns sources ordered by trust score (highest first).
    """
    # Get filtered sources
    sources = Source.list_sources(
        db=db,
        category=category,
        trust_tier=trust_tier,
        limit=limit,
        offset=offset
    )
    
    # Get total count
    query = db.query(Source)
    if category:
        query = query.filter(Source.category == category)
    if trust_tier:
        query = query.filter(Source.trust_tier == trust_tier)
    total = query.count()
    
    return SourceListResponse(
        sources=[SourceResponse.model_validate(s) for s in sources],
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("/{source_id}/configure", response_model=SourceResponse, responses={404: {"model": ErrorResponse}})
def configure_source(
    source_id: UUID,
    update: SourceUpdate,
    db: Session = Depends(get_db)
):
    """
    Update source configuration settings.
    
    Allows updating:
    - crawl_frequency_minutes: How often to crawl this source
    - robots_txt_allowed: Whether robots.txt allows access
    """
    # Get source
    source = Source.get_by_id(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    
    # Update fields
    update_data = update.model_dump(exclude_unset=True)
    updated_source = Source.update(db, source_id, **update_data)
    
    return SourceResponse.model_validate(updated_source)
