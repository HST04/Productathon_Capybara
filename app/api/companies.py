"""Company API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.api.dependencies import get_db
from app.api.schemas import CompanyResponse, ErrorResponse
from app.models.company import Company

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/{company_id}", response_model=CompanyResponse, responses={404: {"model": ErrorResponse}})
def get_company(
    company_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get company card by ID.
    
    Returns complete company information including:
    - Name and variants
    - CIN/GST identifiers
    - Website and industry
    - Locations
    - Key products
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")
    
    return CompanyResponse.model_validate(company)
