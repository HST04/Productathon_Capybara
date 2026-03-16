"""Lead management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.api.dependencies import get_db
from app.api.schemas import (
    LeadListResponse,
    LeadListItem,
    LeadDossier,
    LeadResponse,
    FeedbackCreate,
    FeedbackResponse,
    ErrorResponse,
    CompanyInfo,
    EventInfo,
    SignalInfo,
    ProductRecommendation
)
from app.models.lead import Lead
from app.models.company import Company
from app.models.event import Event
from app.models.signal import Signal
from app.models.lead_product import LeadProduct
from app.models.feedback import Feedback
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("/", response_model=LeadListResponse)
def list_leads(
    priority: Optional[str] = Query(None, description="Filter by priority: high, medium, low"),
    status: Optional[str] = Query(None, description="Filter by status"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned sales officer"),
    territory: Optional[str] = Query(None, description="Filter by territory"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """
    List leads with optional filters and pagination.
    
    Returns a paginated list of leads with basic information for list view.
    """
    # Get filtered leads
    leads = Lead.list_leads(
        db=db,
        priority=priority,
        status=status,
        assigned_to=assigned_to,
        territory=territory,
        limit=limit,
        offset=offset
    )
    
    # Get total count
    total = Lead.count_leads(
        db=db,
        priority=priority,
        status=status,
        assigned_to=assigned_to
    )
    
    # Build list items with company name and top product
    lead_items = []
    for lead in leads:
        # Get company name
        company = db.query(Company).filter(Company.id == lead.company_id).first()
        company_name = company.name if company else "Unknown"
        
        # Get event summary
        event = db.query(Event).filter(Event.id == lead.event_id).first()
        event_summary = event.event_summary if event else ""
        
        # Get top product
        products = LeadProduct.get_by_lead_id(db, lead.id)
        top_product = products[0].product_name if products else None
        
        lead_items.append(LeadListItem(
            id=lead.id,
            company_name=company_name,
            event_summary=event_summary,
            score=lead.score,
            priority=lead.priority,
            status=lead.status,
            created_at=lead.created_at,
            top_product=top_product
        ))
    
    return LeadListResponse(
        leads=lead_items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{lead_id}", response_model=LeadDossier, responses={404: {"model": ErrorResponse}})
def get_lead_dossier(
    lead_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get complete lead dossier with all related information.
    
    Returns:
    - Lead details (score, priority, status)
    - Company information
    - Event details
    - Source signal
    - Top 3 product recommendations with reasoning
    - Feedback history
    """
    # Get lead
    lead = Lead.get_by_id(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
    
    # Get company
    company = db.query(Company).filter(Company.id == lead.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {lead.company_id} not found")
    
    # Get event
    event = db.query(Event).filter(Event.id == lead.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {lead.event_id} not found")
    
    # Get signal
    signal = db.query(Signal).filter(Signal.id == event.signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal {event.signal_id} not found")
    
    # Get product recommendations
    products = LeadProduct.get_by_lead_id(db, lead_id)
    
    # Get feedback
    feedback_list = Feedback.get_by_lead_id(db, lead_id)
    
    # Build dossier
    return LeadDossier(
        lead=LeadResponse.model_validate(lead),
        company=CompanyInfo.model_validate(company),
        event=EventInfo.model_validate(event),
        signal=SignalInfo.model_validate(signal),
        products=[ProductRecommendation.model_validate(p) for p in products],
        feedback=[FeedbackResponse.model_validate(f) for f in feedback_list]
    )


@router.post("/{lead_id}/feedback", response_model=FeedbackResponse, responses={404: {"model": ErrorResponse}})
def submit_feedback(
    lead_id: UUID,
    feedback: FeedbackCreate,
    db: Session = Depends(get_db)
):
    """
    Submit feedback for a lead.
    
    Feedback types:
    - accepted: Sales officer accepted the lead
    - rejected: Sales officer rejected the lead
    - converted: Lead was converted to a sale
    
    This triggers trust score updates for the source.
    """
    # Verify lead exists
    lead = Lead.get_by_id(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
    
    # Create feedback using service (handles trust score updates)
    feedback_service = FeedbackService(db)
    created_feedback = feedback_service.submit_feedback(
        lead_id=lead_id,
        feedback_type=feedback.feedback_type,
        notes=feedback.notes,
        submitted_by=feedback.submitted_by
    )
    
    return FeedbackResponse.model_validate(created_feedback)
