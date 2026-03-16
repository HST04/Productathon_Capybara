"""Unit tests for Lead Scorer."""

import pytest
from datetime import datetime, timedelta
from app.services.lead_scorer import LeadScorer, ScoringComponents


@pytest.fixture
def scorer():
    """Create a LeadScorer instance."""
    return LeadScorer()


def test_calculate_intent_score(scorer):
    """Test intent score calculation."""
    # Explicit tender (1.0) should give 100
    assert scorer._calculate_intent_score(1.0) == 100
    
    # Strong intent (0.8) should give 80
    assert scorer._calculate_intent_score(0.8) == 80
    
    # Moderate intent (0.5) should give 50
    assert scorer._calculate_intent_score(0.5) == 50
    
    # Vague mention (0.2) should give 20
    assert scorer._calculate_intent_score(0.2) == 20
    
    # No intent (0.0) should give 0
    assert scorer._calculate_intent_score(0.0) == 0


def test_calculate_freshness_score(scorer):
    """Test freshness score calculation."""
    now = datetime.now()
    
    # Fresh signal (today) should give 100
    assert scorer._calculate_freshness_score(now) == 100
    
    # 5 days old should give 75
    five_days_ago = now - timedelta(days=5)
    assert scorer._calculate_freshness_score(five_days_ago) == 75
    
    # 10 days old should give 50
    ten_days_ago = now - timedelta(days=10)
    assert scorer._calculate_freshness_score(ten_days_ago) == 50
    
    # 20 days old should give 0
    twenty_days_ago = now - timedelta(days=20)
    assert scorer._calculate_freshness_score(twenty_days_ago) == 0
    
    # 30 days old should still give 0 (clamped)
    thirty_days_ago = now - timedelta(days=30)
    assert scorer._calculate_freshness_score(thirty_days_ago) == 0


def test_calculate_company_size_score(scorer):
    """Test company size score calculation."""
    # Large company indicators
    assert scorer._calculate_company_size_score("large multinational company") == 80
    assert scorer._calculate_company_size_score("major industry player") == 80
    assert scorer._calculate_company_size_score("leading manufacturer") == 80
    
    # Medium company indicators
    assert scorer._calculate_company_size_score("medium-sized enterprise") == 60
    assert scorer._calculate_company_size_score("mid-sized company") == 60
    
    # Small company indicators
    assert scorer._calculate_company_size_score("small startup") == 40
    assert scorer._calculate_company_size_score("emerging business") == 40
    
    # Numeric indicators - crore
    assert scorer._calculate_company_size_score("investment of 150 crore") == 100
    assert scorer._calculate_company_size_score("turnover of 75 crore") == 80
    assert scorer._calculate_company_size_score("project worth 25 crore") == 60
    assert scorer._calculate_company_size_score("budget of 5 crore") == 40
    
    # Numeric indicators - million
    assert scorer._calculate_company_size_score("investment of 200 million") == 100
    assert scorer._calculate_company_size_score("revenue of 60 million") == 80
    
    # No information
    assert scorer._calculate_company_size_score(None) == 50
    assert scorer._calculate_company_size_score("") == 50


def test_calculate_product_confidence_score(scorer):
    """Test product confidence score calculation."""
    # High confidence products
    high_confidences = [0.95, 0.90, 0.85]
    score = scorer._calculate_product_confidence_score(high_confidences)
    assert 85 <= score <= 95
    
    # Medium confidence products
    medium_confidences = [0.70, 0.65, 0.60]
    score = scorer._calculate_product_confidence_score(medium_confidences)
    assert 60 <= score <= 70
    
    # Low confidence products
    low_confidences = [0.45, 0.40, 0.35]
    score = scorer._calculate_product_confidence_score(low_confidences)
    assert 35 <= score <= 45
    
    # Mixed confidences (should use top 3)
    mixed_confidences = [0.95, 0.85, 0.75, 0.40, 0.30]
    score = scorer._calculate_product_confidence_score(mixed_confidences)
    assert 80 <= score <= 90
    
    # No products
    assert scorer._calculate_product_confidence_score([]) == 50


def test_calculate_score_high_priority(scorer):
    """Test score calculation for high-priority lead."""
    now = datetime.now()
    
    score, components = scorer.calculate_score(
        intent_strength=0.95,  # Explicit tender
        signal_date=now,  # Fresh signal
        company_size_proxy="investment of 200 crore",  # Large company
        product_confidences=[0.95, 0.90, 0.85],  # High confidence products
        source_trust_score=85  # High trust source
    )
    
    # Should be high priority (>= 70)
    assert score >= 70
    assert isinstance(components, ScoringComponents)
    assert components.intent_strength == 95
    assert components.freshness == 100


def test_calculate_score_medium_priority(scorer):
    """Test score calculation for medium-priority lead."""
    five_days_ago = datetime.now() - timedelta(days=5)
    
    score, components = scorer.calculate_score(
        intent_strength=0.60,  # Moderate intent
        signal_date=five_days_ago,  # 5 days old
        company_size_proxy="medium-sized company",  # Medium company
        product_confidences=[0.70, 0.65, 0.60],  # Medium confidence
        source_trust_score=55  # Medium trust
    )
    
    # Should be medium priority (40-69)
    assert 40 <= score < 70
    assert components.freshness == 75


def test_calculate_score_low_priority(scorer):
    """Test score calculation for low-priority lead."""
    twenty_days_ago = datetime.now() - timedelta(days=20)
    
    score, components = scorer.calculate_score(
        intent_strength=0.30,  # Vague mention
        signal_date=twenty_days_ago,  # Old signal
        company_size_proxy="small startup",  # Small company
        product_confidences=[0.45, 0.40, 0.35],  # Low confidence
        source_trust_score=30  # Low trust
    )
    
    # Should be low priority (< 40)
    assert score < 40


def test_assign_priority(scorer):
    """Test priority assignment based on score."""
    # High priority
    assert scorer.assign_priority(100) == 'high'
    assert scorer.assign_priority(85) == 'high'
    assert scorer.assign_priority(70) == 'high'
    
    # Medium priority
    assert scorer.assign_priority(69) == 'medium'
    assert scorer.assign_priority(55) == 'medium'
    assert scorer.assign_priority(40) == 'medium'
    
    # Low priority
    assert scorer.assign_priority(39) == 'low'
    assert scorer.assign_priority(20) == 'low'
    assert scorer.assign_priority(0) == 'low'


def test_score_clamping(scorer):
    """Test that scores are clamped to 0-100 range."""
    now = datetime.now()
    
    # Test with extreme values that might push score over 100
    score, _ = scorer.calculate_score(
        intent_strength=1.0,
        signal_date=now,
        company_size_proxy="investment of 500 crore",
        product_confidences=[1.0, 1.0, 1.0],
        source_trust_score=100
    )
    
    assert 0 <= score <= 100


def test_scoring_components_to_dict(scorer):
    """Test ScoringComponents to_dict method."""
    components = ScoringComponents(
        intent_strength=95.0,
        freshness=100.0,
        company_size=80.0,
        product_confidence=90.0,
        source_trust=85.0,
        geographic_proximity=50.0
    )
    
    result = components.to_dict()
    
    assert result['intent_strength'] == 95.0
    assert result['freshness'] == 100.0
    assert result['company_size'] == 80.0
    assert result['product_confidence'] == 90.0
    assert result['source_trust'] == 85.0
    assert result['geographic_proximity'] == 50.0


def test_geographic_proximity_placeholder(scorer):
    """Test geographic proximity score (placeholder implementation)."""
    # Currently returns neutral score (50)
    score = scorer._calculate_geographic_proximity_score("Mumbai")
    assert score == 50
    
    score = scorer._calculate_geographic_proximity_score(None)
    assert score == 50


def test_score_weights_sum_to_one(scorer):
    """Test that scoring weights sum to approximately 1.0."""
    total_weight = (
        scorer.WEIGHT_INTENT +
        scorer.WEIGHT_FRESHNESS +
        scorer.WEIGHT_COMPANY_SIZE +
        scorer.WEIGHT_PRODUCT_CONFIDENCE +
        scorer.WEIGHT_SOURCE_TRUST
    )
    
    # Should sum to 1.0 (allowing for floating point precision)
    assert abs(total_weight - 1.0) < 0.001
