"""Lead Scorer for calculating lead scores and priorities."""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class ScoringComponents:
    """Individual scoring components for transparency."""
    intent_strength: float  # 0-100
    freshness: float  # 0-100
    company_size: float  # 0-100
    product_confidence: float  # 0-100
    source_trust: float  # 0-100
    geographic_proximity: float  # 0-100 (optional)
    
    def to_dict(self):
        """Convert to dictionary for logging/debugging."""
        return {
            'intent_strength': self.intent_strength,
            'freshness': self.freshness,
            'company_size': self.company_size,
            'product_confidence': self.product_confidence,
            'source_trust': self.source_trust,
            'geographic_proximity': self.geographic_proximity
        }


class LeadScorer:
    """
    Lead Scorer calculates scores and priorities for business opportunities.
    
    Scoring Formula:
    Total Score = (Intent × 0.30) + (Freshness × 0.25) + (Company Size × 0.20) + 
                  (Product Confidence × 0.15) + (Source Trust × 0.10)
    
    Priority Assignment:
    - High: Score ≥ 70
    - Medium: 40 ≤ Score < 70
    - Low: Score < 40
    """
    
    # Scoring weights
    WEIGHT_INTENT = 0.30
    WEIGHT_FRESHNESS = 0.25
    WEIGHT_COMPANY_SIZE = 0.20
    WEIGHT_PRODUCT_CONFIDENCE = 0.15
    WEIGHT_SOURCE_TRUST = 0.10
    
    # Priority thresholds
    PRIORITY_HIGH_THRESHOLD = 70
    PRIORITY_MEDIUM_THRESHOLD = 40
    
    def __init__(self):
        """Initialize the lead scorer."""
        logger.info("Lead scorer initialized")
    
    def calculate_score(
        self,
        intent_strength: float,
        signal_date: datetime,
        company_size_proxy: Optional[str],
        product_confidences: List[float],
        source_trust_score: float,
        location: Optional[str] = None
    ) -> tuple[int, ScoringComponents]:
        """
        Calculate lead score from all components.
        
        Args:
            intent_strength: Intent strength (0.0 to 1.0)
            signal_date: Date when signal was ingested
            company_size_proxy: Company size indicator (turnover/capacity mentions)
            product_confidences: List of confidence scores for product recommendations
            source_trust_score: Trust score of the source (0-100)
            location: Location for geographic proximity calculation (optional)
        
        Returns:
            Tuple of (final_score, scoring_components)
        """
        # Calculate individual components
        intent_score = self._calculate_intent_score(intent_strength)
        freshness_score = self._calculate_freshness_score(signal_date)
        company_size_score = self._calculate_company_size_score(company_size_proxy)
        product_confidence_score = self._calculate_product_confidence_score(product_confidences)
        source_trust = source_trust_score  # Already 0-100
        geographic_score = self._calculate_geographic_proximity_score(location)
        
        # Create components object for transparency
        components = ScoringComponents(
            intent_strength=intent_score,
            freshness=freshness_score,
            company_size=company_size_score,
            product_confidence=product_confidence_score,
            source_trust=source_trust,
            geographic_proximity=geographic_score
        )
        
        # Calculate weighted final score
        final_score = (
            intent_score * self.WEIGHT_INTENT +
            freshness_score * self.WEIGHT_FRESHNESS +
            company_size_score * self.WEIGHT_COMPANY_SIZE +
            product_confidence_score * self.WEIGHT_PRODUCT_CONFIDENCE +
            source_trust * self.WEIGHT_SOURCE_TRUST
        )
        
        # Round to integer and clamp to 0-100
        final_score = max(0, min(100, int(round(final_score))))
        
        logger.info(
            f"Calculated lead score: {final_score} "
            f"(intent={intent_score:.1f}, freshness={freshness_score:.1f}, "
            f"company_size={company_size_score:.1f}, product_conf={product_confidence_score:.1f}, "
            f"source_trust={source_trust:.1f})"
        )
        
        return final_score, components
    
    def _calculate_intent_score(self, intent_strength: float) -> float:
        """
        Calculate intent score from intent strength.
        
        Intent strength interpretation:
        - 1.0 (explicit tender): 100
        - 0.7-0.9 (strong intent): 70-90
        - 0.4-0.6 (moderate intent): 40-60
        - 0.0-0.3 (vague mention): 0-30
        
        Args:
            intent_strength: Intent strength (0.0 to 1.0)
        
        Returns:
            Intent score (0-100)
        """
        return intent_strength * 100
    
    def _calculate_freshness_score(self, signal_date: datetime) -> float:
        """
        Calculate freshness score based on signal age.
        
        Formula: 100 - (days_old × 5), minimum 0
        - 0 days old: 100
        - 5 days old: 75
        - 10 days old: 50
        - 20+ days old: 0
        
        Args:
            signal_date: Date when signal was ingested
        
        Returns:
            Freshness score (0-100)
        """
        now = datetime.now()
        days_old = (now - signal_date).days
        
        freshness = 100 - (days_old * 5)
        return max(0, freshness)
    
    def _calculate_company_size_score(self, company_size_proxy: Optional[str]) -> float:
        """
        Calculate company size score from proxy indicators.
        
        Heuristics:
        - Mentions of "crore" or "million": Extract numeric value
        - "large", "major", "leading": 80
        - "medium", "mid-sized": 60
        - "small", "startup": 40
        - No mention: 50 (neutral)
        
        Args:
            company_size_proxy: Company size indicator text
        
        Returns:
            Company size score (0-100)
        """
        if not company_size_proxy:
            return 50  # Neutral score when no information
        
        text_lower = company_size_proxy.lower()
        
        # Check for numeric indicators (turnover, investment, capacity)
        if 'crore' in text_lower or 'million' in text_lower:
            # Try to extract numeric value
            import re
            numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(?:crore|million)', text_lower)
            if numbers:
                value = float(numbers[0])
                # Scale: 100+ crore = 100, 50-100 = 80, 10-50 = 60, <10 = 40
                if value >= 100:
                    return 100
                elif value >= 50:
                    return 80
                elif value >= 10:
                    return 60
                else:
                    return 40
        
        # Check for qualitative indicators
        if any(word in text_lower for word in ['large', 'major', 'leading', 'multinational']):
            return 80
        elif any(word in text_lower for word in ['medium', 'mid-sized', 'moderate']):
            return 60
        elif any(word in text_lower for word in ['small', 'startup', 'emerging']):
            return 40
        
        return 50  # Default neutral score
    
    def _calculate_product_confidence_score(self, product_confidences: List[float]) -> float:
        """
        Calculate product confidence score from top product recommendations.
        
        Uses average of top 3 product confidence scores.
        
        Args:
            product_confidences: List of confidence scores (0.0 to 1.0)
        
        Returns:
            Product confidence score (0-100)
        """
        if not product_confidences:
            return 50  # Neutral score when no products
        
        # Take top 3 confidences
        top_confidences = sorted(product_confidences, reverse=True)[:3]
        
        # Calculate average and convert to 0-100 scale
        avg_confidence = sum(top_confidences) / len(top_confidences)
        return avg_confidence * 100
    
    def _calculate_geographic_proximity_score(self, location: Optional[str]) -> float:
        """
        Calculate geographic proximity score.
        
        This is a placeholder for future implementation with actual depot/DSRO data.
        Currently returns neutral score.
        
        Args:
            location: Location string
        
        Returns:
            Geographic proximity score (0-100)
        """
        # TODO: Implement actual proximity calculation with depot/DSRO locations
        # For now, return neutral score
        return 50
    
    def assign_priority(self, score: int) -> str:
        """
        Assign priority level based on score.
        
        Priority Assignment:
        - High: Score ≥ 70
        - Medium: 40 ≤ Score < 70
        - Low: Score < 40
        
        Args:
            score: Lead score (0-100)
        
        Returns:
            Priority level ('high', 'medium', 'low')
        """
        if score >= self.PRIORITY_HIGH_THRESHOLD:
            return 'high'
        elif score >= self.PRIORITY_MEDIUM_THRESHOLD:
            return 'medium'
        else:
            return 'low'
    
    def route_to_territory(
        self,
        db: Session,
        location: Optional[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Route lead to appropriate sales officer based on location.
        
        Args:
            db: Database session
            location: Location string from event
        
        Returns:
            Tuple of (assigned_to, territory) or (None, None) if no match
        """
        if not location:
            logger.warning("No location provided for routing")
            return None, None
        
        # Import here to avoid circular dependency
        from app.models.sales_officer import SalesOfficer
        
        # Find sales officer for this territory
        officer = SalesOfficer.get_by_territory(db, location)
        
        if officer:
            logger.info(f"Routed lead to officer {officer.name} for location {location}")
            # Return officer name and first matching territory
            territory = None
            if officer.territories:
                for t in officer.territories:
                    if t.lower() in location.lower() or location.lower() in t.lower():
                        territory = t
                        break
                if not territory:
                    territory = officer.territories[0]
            
            return officer.name, territory
        else:
            logger.warning(f"No sales officer found for location: {location}")
            return None, location  # Return location as territory even if no officer assigned
