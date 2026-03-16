"""Sales Officer model for storing sales team information and territories."""

from sqlalchemy import Column, String, Boolean, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid
from app.db.session import Base


class SalesOfficer(Base):
    """Sales Officer represents a member of the HPCL sales team."""
    
    __tablename__ = "sales_officers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)
    whatsapp_opt_in = Column(Boolean, default=False)
    territories = Column(ARRAY(String), nullable=True)  # Geographic coverage areas
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # CRUD Operations
    
    @classmethod
    def create(
        cls,
        db: Session,
        name: str,
        phone_number: Optional[str] = None,
        whatsapp_opt_in: bool = False,
        territories: Optional[List[str]] = None
    ) -> 'SalesOfficer':
        """
        Create a new sales officer.
        
        Args:
            db: Database session
            name: Officer name
            phone_number: Phone number (optional)
            whatsapp_opt_in: WhatsApp notification consent (default: False)
            territories: List of geographic territories (optional)
        
        Returns:
            Created SalesOfficer instance
        """
        officer = cls(
            name=name,
            phone_number=phone_number,
            whatsapp_opt_in=whatsapp_opt_in,
            territories=territories or []
        )
        db.add(officer)
        db.commit()
        db.refresh(officer)
        return officer
    
    @classmethod
    def get_by_id(cls, db: Session, officer_id: uuid.UUID) -> Optional['SalesOfficer']:
        """
        Retrieve a sales officer by ID.
        
        Args:
            db: Database session
            officer_id: UUID of the officer
        
        Returns:
            SalesOfficer instance or None if not found
        """
        return db.query(cls).filter(cls.id == officer_id).first()
    
    @classmethod
    def get_by_territory(cls, db: Session, location: str) -> Optional['SalesOfficer']:
        """
        Find a sales officer responsible for a given location.
        
        Args:
            db: Database session
            location: Location string to match against territories
        
        Returns:
            SalesOfficer instance or None if no match found
        """
        # Query officers whose territories array contains the location
        officers = db.query(cls).filter(cls.territories.any(location)).all()
        
        if officers:
            return officers[0]  # Return first match
        
        # Try partial match if exact match fails
        location_lower = location.lower() if location else ""
        for officer in db.query(cls).all():
            if officer.territories:
                for territory in officer.territories:
                    if territory.lower() in location_lower or location_lower in territory.lower():
                        return officer
        
        return None
    
    @classmethod
    def list_officers(
        cls,
        db: Session,
        whatsapp_opt_in: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List['SalesOfficer']:
        """
        List sales officers with optional filters.
        
        Args:
            db: Database session
            whatsapp_opt_in: Filter by WhatsApp opt-in status
            limit: Maximum number of results
            offset: Number of results to skip
        
        Returns:
            List of SalesOfficer instances
        """
        query = db.query(cls)
        
        if whatsapp_opt_in is not None:
            query = query.filter(cls.whatsapp_opt_in == whatsapp_opt_in)
        
        return query.order_by(cls.name).limit(limit).offset(offset).all()
    
    @classmethod
    def update(
        cls,
        db: Session,
        officer_id: uuid.UUID,
        **kwargs
    ) -> Optional['SalesOfficer']:
        """
        Update a sales officer.
        
        Args:
            db: Database session
            officer_id: UUID of the officer
            **kwargs: Fields to update
        
        Returns:
            Updated SalesOfficer instance or None if not found
        """
        officer = cls.get_by_id(db, officer_id)
        if not officer:
            return None
        
        for key, value in kwargs.items():
            if hasattr(officer, key):
                setattr(officer, key, value)
        
        db.commit()
        db.refresh(officer)
        return officer
    
    @classmethod
    def delete(cls, db: Session, officer_id: uuid.UUID) -> bool:
        """
        Delete a sales officer.
        
        Args:
            db: Database session
            officer_id: UUID of the officer
        
        Returns:
            True if deleted, False if not found
        """
        officer = cls.get_by_id(db, officer_id)
        if not officer:
            return False
        
        db.delete(officer)
        db.commit()
        return True
