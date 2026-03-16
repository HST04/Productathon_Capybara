"""Source model for tracking data sources and trust scores."""

from sqlalchemy import Column, String, Integer, Float, Boolean, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid
from app.db.session import Base


class Source(Base):
    """Source registry for tracking data sources and trust scores."""
    
    __tablename__ = "sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(255), unique=True, nullable=False)
    category = Column(String(50), nullable=False)  # 'news', 'tender', 'company_site'
    access_method = Column(String(50), nullable=False)  # 'rss', 'api', 'scrape'
    crawl_frequency_minutes = Column(Integer, default=60)
    trust_score = Column(Float, default=50.0)
    trust_tier = Column(String(20), default='neutral')  # 'high', 'medium', 'low', 'neutral'
    robots_txt_allowed = Column(Boolean, default=True)
    last_crawled_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # CRUD Operations
    
    @classmethod
    def create(
        cls,
        db: Session,
        domain: str,
        category: str,
        access_method: str,
        crawl_frequency_minutes: int = 60,
        robots_txt_allowed: bool = True
    ) -> 'Source':
        """
        Create a new source.
        
        Args:
            db: Database session
            domain: Source domain
            category: Source category ('news', 'tender', 'company_site')
            access_method: Access method ('rss', 'api', 'scrape')
            crawl_frequency_minutes: Crawl frequency in minutes
            robots_txt_allowed: Whether robots.txt allows access
        
        Returns:
            Created Source instance
        """
        source = cls(
            domain=domain,
            category=category,
            access_method=access_method,
            crawl_frequency_minutes=crawl_frequency_minutes,
            robots_txt_allowed=robots_txt_allowed
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        return source
    
    @classmethod
    def get_by_id(cls, db: Session, source_id: uuid.UUID) -> Optional['Source']:
        """
        Retrieve a source by ID.
        
        Args:
            db: Database session
            source_id: UUID of the source
        
        Returns:
            Source instance or None if not found
        """
        return db.query(cls).filter(cls.id == source_id).first()
    
    @classmethod
    def get_by_domain(cls, db: Session, domain: str) -> Optional['Source']:
        """
        Retrieve a source by domain.
        
        Args:
            db: Database session
            domain: Source domain
        
        Returns:
            Source instance or None if not found
        """
        return db.query(cls).filter(cls.domain == domain).first()
    
    @classmethod
    def list_sources(
        cls,
        db: Session,
        category: Optional[str] = None,
        trust_tier: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List['Source']:
        """
        List sources with optional filters.
        
        Args:
            db: Database session
            category: Filter by category
            trust_tier: Filter by trust tier
            limit: Maximum number of results
            offset: Number of results to skip
        
        Returns:
            List of Source instances
        """
        query = db.query(cls)
        
        if category:
            query = query.filter(cls.category == category)
        if trust_tier:
            query = query.filter(cls.trust_tier == trust_tier)
        
        return query.order_by(cls.trust_score.desc()).limit(limit).offset(offset).all()
    
    @classmethod
    def update(
        cls,
        db: Session,
        source_id: uuid.UUID,
        **kwargs
    ) -> Optional['Source']:
        """
        Update a source.
        
        Args:
            db: Database session
            source_id: UUID of the source
            **kwargs: Fields to update
        
        Returns:
            Updated Source instance or None if not found
        """
        source = cls.get_by_id(db, source_id)
        if not source:
            return None
        
        for key, value in kwargs.items():
            if hasattr(source, key):
                setattr(source, key, value)
        
        db.commit()
        db.refresh(source)
        return source
