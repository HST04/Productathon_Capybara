"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID


# Lead Schemas

class LeadBase(BaseModel):
    """Base lead schema with common fields."""
    score: int = Field(..., ge=0, le=100, description="Lead score from 0 to 100")
    priority: str = Field(..., description="Priority level: high, medium, or low")
    assigned_to: Optional[str] = Field(None, description="Sales officer ID/name")
    territory: Optional[str] = Field(None, description="Geographic territory")
    status: str = Field(default="new", description="Lead status")


class LeadResponse(LeadBase):
    """Lead response schema."""
    id: UUID
    event_id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProductRecommendation(BaseModel):
    """Product recommendation schema."""
    id: UUID
    product_name: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    reason_code: Optional[str] = None
    rank: Optional[int] = None
    uncertainty_flag: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class CompanyInfo(BaseModel):
    """Company information schema."""
    id: UUID
    name: str
    name_variants: Optional[List[str]] = None
    cin: Optional[str] = None
    gst: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    locations: Optional[List[str]] = None
    key_products: Optional[List[str]] = None
    
    model_config = ConfigDict(from_attributes=True)


class EventInfo(BaseModel):
    """Event information schema."""
    id: UUID
    event_type: Optional[str] = None
    event_summary: str
    location: Optional[str] = None
    capacity: Optional[str] = None
    deadline: Optional[date] = None
    intent_strength: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


class SignalInfo(BaseModel):
    """Signal information schema."""
    id: UUID
    url: str
    title: Optional[str] = None
    ingested_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class LeadDossier(BaseModel):
    """Complete lead dossier with all related information."""
    lead: LeadResponse
    company: CompanyInfo
    event: EventInfo
    signal: SignalInfo
    products: List[ProductRecommendation]
    feedback: List["FeedbackResponse"] = []


class LeadListItem(BaseModel):
    """Simplified lead for list view."""
    id: UUID
    company_name: str
    event_summary: str
    score: int
    priority: str
    status: str
    created_at: datetime
    top_product: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    """Paginated lead list response."""
    leads: List[LeadListItem]
    total: int
    limit: int
    offset: int


# Feedback Schemas

class FeedbackCreate(BaseModel):
    """Schema for creating feedback."""
    feedback_type: str = Field(..., description="Type: accepted, rejected, or converted")
    notes: Optional[str] = Field(None, description="Optional notes from sales officer")
    submitted_by: Optional[str] = Field(None, description="Sales officer ID/name")


class FeedbackResponse(BaseModel):
    """Feedback response schema."""
    id: UUID
    lead_id: UUID
    feedback_type: str
    notes: Optional[str] = None
    submitted_at: datetime
    submitted_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# Company Schemas

class CompanyResponse(CompanyInfo):
    """Company response with timestamps."""
    created_at: datetime
    updated_at: datetime


# Source Schemas

class SourceBase(BaseModel):
    """Base source schema."""
    domain: str
    category: str = Field(..., description="Category: news, tender, or company_site")
    access_method: str = Field(..., description="Access method: rss, api, or scrape")
    crawl_frequency_minutes: int = Field(default=60, ge=1)
    robots_txt_allowed: bool = True


class SourceResponse(SourceBase):
    """Source response schema."""
    id: UUID
    trust_score: float
    trust_tier: str
    last_crawled_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SourceUpdate(BaseModel):
    """Schema for updating source configuration."""
    crawl_frequency_minutes: Optional[int] = Field(None, ge=1)
    robots_txt_allowed: Optional[bool] = None


class SourceListResponse(BaseModel):
    """Paginated source list response."""
    sources: List[SourceResponse]
    total: int
    limit: int
    offset: int


# Dashboard Schemas

class DashboardStats(BaseModel):
    """Dashboard statistics schema."""
    total_leads: int
    leads_by_priority: dict[str, int]
    leads_by_status: dict[str, int]
    conversion_rate: float
    top_sources: List[dict]
    recent_leads_count: int


# Error Schemas

class ErrorResponse(BaseModel):
    """Error response schema."""
    detail: str
