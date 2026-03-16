"""Dashboard statistics API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional

from app.api.dependencies import get_db
from app.api.schemas import DashboardStats
from app.models.lead import Lead
from app.models.feedback import Feedback
from app.models.source import Source

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to include in statistics"),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics and metrics.
    
    Returns:
    - Total leads count
    - Leads by priority (high, medium, low)
    - Leads by status (new, contacted, qualified, converted, rejected)
    - Conversion rate (converted / total)
    - Top sources by trust score
    - Recent leads count (last N days)
    """
    # Calculate date threshold
    date_threshold = datetime.now() - timedelta(days=days)
    
    # Total leads
    total_leads = db.query(Lead).count()
    
    # Leads by priority
    priority_counts = db.query(
        Lead.priority,
        func.count(Lead.id)
    ).group_by(Lead.priority).all()
    
    leads_by_priority = {
        priority: count for priority, count in priority_counts
    }
    
    # Ensure all priorities are present
    for priority in ['high', 'medium', 'low']:
        if priority not in leads_by_priority:
            leads_by_priority[priority] = 0
    
    # Leads by status
    status_counts = db.query(
        Lead.status,
        func.count(Lead.id)
    ).group_by(Lead.status).all()
    
    leads_by_status = {
        status: count for status, count in status_counts
    }
    
    # Calculate conversion rate
    converted_count = leads_by_status.get('converted', 0)
    conversion_rate = (converted_count / total_leads * 100) if total_leads > 0 else 0.0
    
    # Top sources by trust score
    top_sources_query = db.query(Source).order_by(
        Source.trust_score.desc()
    ).limit(10).all()
    
    top_sources = [
        {
            "domain": source.domain,
            "trust_score": source.trust_score,
            "trust_tier": source.trust_tier,
            "category": source.category
        }
        for source in top_sources_query
    ]
    
    # Recent leads count
    recent_leads_count = db.query(Lead).filter(
        Lead.created_at >= date_threshold
    ).count()
    
    return DashboardStats(
        total_leads=total_leads,
        leads_by_priority=leads_by_priority,
        leads_by_status=leads_by_status,
        conversion_rate=round(conversion_rate, 2),
        top_sources=top_sources,
        recent_leads_count=recent_leads_count
    )
