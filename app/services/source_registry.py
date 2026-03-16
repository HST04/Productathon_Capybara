"""Source Registry Manager for tracking sources and trust scores."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.source import Source
from app.models.feedback import Feedback
from app.models.lead import Lead
from app.models.event import Event
from app.models.signal import Signal


class SourceRegistryManager:
    """Manages source registry with dynamic trust scoring."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def register_source(
        self,
        domain: str,
        category: str,
        access_method: str,
        crawl_frequency_minutes: int = 60,
        robots_txt_allowed: bool = True
    ) -> Source:
        """
        Register a new source in the registry.
        
        Args:
            domain: Source domain (e.g., 'example.com')
            category: Source category ('news', 'tender', 'company_site')
            access_method: Access method ('rss', 'api', 'scrape')
            crawl_frequency_minutes: How often to crawl (default 60)
            robots_txt_allowed: Whether robots.txt allows access (default True)
        
        Returns:
            Created Source object
        """
        source = Source(
            domain=domain,
            category=category,
            access_method=access_method,
            crawl_frequency_minutes=crawl_frequency_minutes,
            trust_score=50.0,  # Neutral starting score
            trust_tier='neutral',
            robots_txt_allowed=robots_txt_allowed
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source
    
    def get_source_by_domain(self, domain: str) -> Optional[Source]:
        """Get source by domain name."""
        return self.db.query(Source).filter(Source.domain == domain).first()
    
    def get_source_by_id(self, source_id: str) -> Optional[Source]:
        """Get source by ID."""
        return self.db.query(Source).filter(Source.id == source_id).first()
    
    def list_sources(
        self,
        category: Optional[str] = None,
        trust_tier: Optional[str] = None
    ) -> List[Source]:
        """
        List sources with optional filters.
        
        Args:
            category: Filter by category (optional)
            trust_tier: Filter by trust tier (optional)
        
        Returns:
            List of Source objects
        """
        query = self.db.query(Source)
        
        if category:
            query = query.filter(Source.category == category)
        
        if trust_tier:
            query = query.filter(Source.trust_tier == trust_tier)
        
        return query.all()
    
    def update_last_crawled(self, source_id: str) -> None:
        """Update the last crawled timestamp for a source."""
        source = self.get_source_by_id(source_id)
        if source:
            source.last_crawled_at = datetime.utcnow()
            self.db.commit()
    
    def update_robots_txt_status(self, source_id: str, allowed: bool) -> None:
        """Update robots.txt allowed status for a source."""
        source = self.get_source_by_id(source_id)
        if source:
            source.robots_txt_allowed = allowed
            self.db.commit()
    
    def update_crawl_frequency(self, source_id: str, minutes: int) -> None:
        """Update crawl frequency for a source."""
        source = self.get_source_by_id(source_id)
        if source:
            source.crawl_frequency_minutes = minutes
            self.db.commit()
    
    def calculate_trust_score(self, source_id: str) -> float:
        """
        Calculate trust score based on feedback history.
        
        Formula: (Accepted + Converted × 2) / Total Feedback × 100
        
        Args:
            source_id: Source ID
        
        Returns:
            Trust score (0-100)
        """
        # Get all feedback for leads from this source
        # Join: Feedback -> Lead -> Event -> Signal -> Source
        feedback_query = (
            self.db.query(Feedback)
            .join(Lead, Feedback.lead_id == Lead.id)
            .join(Event, Lead.event_id == Event.id)
            .join(Signal, Event.signal_id == Signal.id)
            .filter(Signal.source_id == source_id)
        )
        
        total_feedback = feedback_query.count()
        
        if total_feedback == 0:
            return 50.0  # Neutral score for no feedback
        
        accepted_count = feedback_query.filter(
            Feedback.feedback_type == 'accepted'
        ).count()
        
        converted_count = feedback_query.filter(
            Feedback.feedback_type == 'converted'
        ).count()
        
        # Calculate score: (Accepted + Converted × 2) / Total × 100
        score = ((accepted_count + (converted_count * 2)) / total_feedback) * 100
        
        return min(100.0, max(0.0, score))  # Clamp to 0-100
    
    def calculate_trust_tier(self, trust_score: float) -> str:
        """
        Calculate trust tier from trust score.
        
        Args:
            trust_score: Trust score (0-100)
        
        Returns:
            Trust tier ('high', 'medium', 'low', 'neutral')
        """
        if trust_score >= 70:
            return 'high'
        elif trust_score >= 40:
            return 'medium'
        elif trust_score > 0:
            return 'low'
        else:
            return 'neutral'
    
    def update_trust_score(self, source_id: str, feedback_type: str) -> None:
        """
        Update trust score for a source based on new feedback.
        
        Args:
            source_id: Source ID
            feedback_type: Feedback type ('accepted', 'rejected', 'converted')
        """
        # Recalculate trust score from all feedback
        new_score = self.calculate_trust_score(source_id)
        new_tier = self.calculate_trust_tier(new_score)
        
        source = self.get_source_by_id(source_id)
        if source:
            source.trust_score = new_score
            source.trust_tier = new_tier
            self.db.commit()
    
    def get_sources_by_trust_tier(self, tier: str) -> List[Source]:
        """Get all sources with a specific trust tier."""
        return self.db.query(Source).filter(Source.trust_tier == tier).all()
    
    def delete_source(self, source_id: str) -> bool:
        """
        Delete a source from the registry.
        
        Args:
            source_id: Source ID
        
        Returns:
            True if deleted, False if not found
        """
        source = self.get_source_by_id(source_id)
        if source:
            self.db.delete(source)
            self.db.commit()
            return True
        return False
