"""LeadProduct model for product recommendations."""

from sqlalchemy import Column, String, Text, Float, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Session
from typing import List, Optional
import uuid
from app.db.session import Base


class LeadProduct(Base):
    """Product recommendation for a lead."""
    
    __tablename__ = "lead_products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey('leads.id'), nullable=False)
    product_name = Column(String(100), nullable=False)
    confidence_score = Column(Float, nullable=False)  # 0.0 to 1.0
    reasoning = Column(Text, nullable=False)
    reason_code = Column(String(50), nullable=True)  # 'keyword_match', 'operational_cue', etc
    rank = Column(Integer, nullable=True)  # 1, 2, 3 for top 3
    uncertainty_flag = Column(Boolean, default=False)
    
    # Relationships
    lead = relationship("Lead", backref="products")
    
    @classmethod
    def create(
        cls,
        db: Session,
        lead_id: uuid.UUID,
        product_name: str,
        confidence_score: float,
        reasoning: str,
        reason_code: Optional[str] = None,
        rank: Optional[int] = None,
        uncertainty_flag: bool = False
    ) -> "LeadProduct":
        """
        Create a new product recommendation for a lead.
        
        Args:
            db: Database session
            lead_id: UUID of the lead
            product_name: Name of the recommended product
            confidence_score: Confidence score (0.0 to 1.0)
            reasoning: Explanation for the recommendation
            reason_code: Code indicating match type (keyword_match, operational_cue, etc)
            rank: Ranking (1, 2, 3 for top 3)
            uncertainty_flag: True if confidence < 60%
        
        Returns:
            Created LeadProduct instance
        """
        lead_product = cls(
            lead_id=lead_id,
            product_name=product_name,
            confidence_score=confidence_score,
            reasoning=reasoning,
            reason_code=reason_code,
            rank=rank,
            uncertainty_flag=uncertainty_flag
        )
        db.add(lead_product)
        db.commit()
        db.refresh(lead_product)
        return lead_product
    
    @classmethod
    def create_batch(
        cls,
        db: Session,
        lead_id: uuid.UUID,
        products: List[dict]
    ) -> List["LeadProduct"]:
        """
        Create multiple product recommendations for a lead in a single transaction.
        
        Args:
            db: Database session
            lead_id: UUID of the lead
            products: List of product dictionaries with keys:
                - product_name: str
                - confidence_score: float
                - reasoning: str
                - reason_code: Optional[str]
                - rank: Optional[int]
                - uncertainty_flag: bool
        
        Returns:
            List of created LeadProduct instances
        """
        lead_products = []
        for product_data in products:
            lead_product = cls(
                lead_id=lead_id,
                product_name=product_data['product_name'],
                confidence_score=product_data['confidence_score'],
                reasoning=product_data['reasoning'],
                reason_code=product_data.get('reason_code'),
                rank=product_data.get('rank'),
                uncertainty_flag=product_data.get('uncertainty_flag', False)
            )
            db.add(lead_product)
            lead_products.append(lead_product)
        
        db.commit()
        for lp in lead_products:
            db.refresh(lp)
        
        return lead_products
    
    @classmethod
    def get_by_lead_id(
        cls,
        db: Session,
        lead_id: uuid.UUID
    ) -> List["LeadProduct"]:
        """
        Get all product recommendations for a specific lead.
        
        Args:
            db: Database session
            lead_id: UUID of the lead
        
        Returns:
            List of LeadProduct instances ordered by rank
        """
        return db.query(cls).filter(
            cls.lead_id == lead_id
        ).order_by(cls.rank.asc()).all()
    
    @classmethod
    def get_by_id(
        cls,
        db: Session,
        product_id: uuid.UUID
    ) -> Optional["LeadProduct"]:
        """
        Get a product recommendation by ID.
        
        Args:
            db: Database session
            product_id: UUID of the product recommendation
        
        Returns:
            LeadProduct instance or None if not found
        """
        return db.query(cls).filter(cls.id == product_id).first()
    
    @classmethod
    def update(
        cls,
        db: Session,
        product_id: uuid.UUID,
        **kwargs
    ) -> Optional["LeadProduct"]:
        """
        Update a product recommendation.
        
        Args:
            db: Database session
            product_id: UUID of the product recommendation
            **kwargs: Fields to update
        
        Returns:
            Updated LeadProduct instance or None if not found
        """
        lead_product = cls.get_by_id(db, product_id)
        if lead_product:
            for key, value in kwargs.items():
                if hasattr(lead_product, key):
                    setattr(lead_product, key, value)
            db.commit()
            db.refresh(lead_product)
        return lead_product
    
    @classmethod
    def delete(
        cls,
        db: Session,
        product_id: uuid.UUID
    ) -> bool:
        """
        Delete a product recommendation.
        
        Args:
            db: Database session
            product_id: UUID of the product recommendation
        
        Returns:
            True if deleted, False if not found
        """
        lead_product = cls.get_by_id(db, product_id)
        if lead_product:
            db.delete(lead_product)
            db.commit()
            return True
        return False
    
    @classmethod
    def delete_by_lead_id(
        cls,
        db: Session,
        lead_id: uuid.UUID
    ) -> int:
        """
        Delete all product recommendations for a lead.
        
        Args:
            db: Database session
            lead_id: UUID of the lead
        
        Returns:
            Number of deleted records
        """
        count = db.query(cls).filter(cls.lead_id == lead_id).delete()
        db.commit()
        return count
