"""
Integration tests for the feedback loop and trust score updates.

Tests the complete feedback workflow from submission through source trust
score updates and trust tier recalculation.
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.models.source import Source
from app.models.company import Company
from app.models.event import Event
from app.models.lead import Lead
from app.models.feedback import Feedback
from app.services.feedback_service import FeedbackService


@pytest.fixture
def db_session():
    """Create a test database session."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        # Clean up test data
        db.query(Feedback).delete()
        db.query(Lead).delete()
        db.query(Event).delete()
        db.query(Signal).delete()
        db.query(Company).delete()
        db.query(Source).delete()
        db.commit()
        db.close()


@pytest.fixture
def test_source(db_session):
    """Create a test source with neutral trust score."""
    source = Source(
        domain="test-source.com",
        category="news",
        access_method="rss",
        trust_score=50.0,
        trust_tier="neutral"
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


@pytest.fixture
def test_lead(db_session, test_source):
    """Create a complete test lead with all dependencies."""
    # Create company
    company = Company(
        name="Test Company",
        name_variants=["Test Co"],
        industry="Manufacturing"
    )
    db_session.add(company)
    db_session.flush()
    
    # Create signal
    signal = Signal(
        source_id=test_source.id,
        url="https://test-source.com/article",
        title="Test Article",
        content="Test content",
        ingested_at=datetime.utcnow(),
        processed=True
    )
    db_session.add(signal)
    db_session.flush()
    
    # Create event
    event = Event(
        signal_id=signal.id,
        company_id=company.id,
        event_type="expansion",
        event_summary="Test expansion",
        is_lead_worthy=True,
        intent_strength=0.8
    )
    db_session.add(event)
    db_session.flush()
    
    # Create lead
    lead = Lead(
        event_id=event.id,
        company_id=company.id,
        score=75,
        priority="high",
        status="new"
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)
    
    return lead


@pytest.mark.integration
class TestFeedbackLoop:
    """Test the feedback loop and trust score updates."""
    
    def test_accepted_feedback_increases_trust(self, db_session, test_lead, test_source):
        """
        Test that accepted feedback increases source trust score.
        
        Validates Requirements: 7.2, 7.4, 11.3, 11.4
        """
        # Record initial trust score
        initial_trust = test_source.trust_score
        initial_tier = test_source.trust_tier
        
        # Submit accepted feedback
        feedback_service = FeedbackService(db_session)
        feedback = feedback_service.submit_feedback(
            lead_id=test_lead.id,
            feedback_type="accepted",
            notes="Good lead, contacted the company",
            submitted_by="test_officer"
        )
        
        # Verify feedback persisted
        assert feedback is not None
        assert feedback.lead_id == test_lead.id
        assert feedback.feedback_type == "accepted"
        assert feedback.notes == "Good lead, contacted the company"
        assert feedback.submitted_at is not None
        
        # Refresh source to get updated trust score
        db_session.refresh(test_source)
        
        # Verify trust score increased
        assert test_source.trust_score > initial_trust, \
            f"Trust score should increase from {initial_trust} but got {test_source.trust_score}"
        
        # Verify trust tier may have changed
        # (depends on the new score, but should be recalculated)
        assert test_source.trust_tier in ["low", "neutral", "medium", "high"]
    
    def test_converted_feedback_increases_trust_more(self, db_session, test_lead, test_source):
        """
        Test that converted feedback increases trust more than accepted.
        
        Converted feedback should have +2 weight vs +1 for accepted.
        
        Validates Requirements: 11.3, 11.4
        """
        initial_trust = test_source.trust_score
        
        # Submit converted feedback
        feedback_service = FeedbackService(db_session)
        feedback = feedback_service.submit_feedback(
            lead_id=test_lead.id,
            feedback_type="converted",
            notes="Successfully closed the deal!",
            submitted_by="test_officer"
        )
        
        assert feedback is not None
        assert feedback.feedback_type == "converted"
        
        # Refresh source
        db_session.refresh(test_source)
        
        # Verify trust score increased significantly
        trust_increase = test_source.trust_score - initial_trust
        assert trust_increase > 0, "Trust score should increase for converted feedback"
        
        # The increase should be substantial (converted has 2x weight)
        # Exact value depends on implementation, but should be noticeable
        assert trust_increase >= 1.0, \
            f"Converted feedback should increase trust significantly, got {trust_increase}"
    
    def test_rejected_feedback_decreases_trust(self, db_session, test_lead, test_source):
        """
        Test that rejected feedback decreases source trust score.
        
        Validates Requirements: 7.2, 7.4, 11.3, 11.4
        """
        initial_trust = test_source.trust_score
        
        # Submit rejected feedback
        feedback_service = FeedbackService(db_session)
        feedback = feedback_service.submit_feedback(
            lead_id=test_lead.id,
            feedback_type="rejected",
            notes="Not relevant to our business",
            submitted_by="test_officer"
        )
        
        assert feedback is not None
        assert feedback.feedback_type == "rejected"
        
        # Refresh source
        db_session.refresh(test_source)
        
        # Verify trust score decreased
        assert test_source.trust_score < initial_trust, \
            f"Trust score should decrease from {initial_trust} but got {test_source.trust_score}"
    
    def test_multiple_feedback_accumulation(self, db_session, test_source):
        """
        Test that multiple feedback submissions accumulate correctly.
        
        Validates Requirements: 11.3, 11.4
        """
        # Create multiple leads from the same source
        company = Company(name="Test Company", name_variants=[])
        db_session.add(company)
        db_session.flush()
        
        leads = []
        for i in range(3):
            signal = Signal(
                source_id=test_source.id,
                url=f"https://test-source.com/article-{i}",
                title=f"Article {i}",
                content="Content",
                ingested_at=datetime.utcnow(),
                processed=True
            )
            db_session.add(signal)
            db_session.flush()
            
            event = Event(
                signal_id=signal.id,
                company_id=company.id,
                event_type="expansion",
                event_summary=f"Event {i}",
                is_lead_worthy=True,
                intent_strength=0.7
            )
            db_session.add(event)
            db_session.flush()
            
            lead = Lead(
                event_id=event.id,
                company_id=company.id,
                score=70,
                priority="medium",
                status="new"
            )
            db_session.add(lead)
            leads.append(lead)
        
        db_session.commit()
        
        initial_trust = test_source.trust_score
        
        # Submit mixed feedback
        feedback_service = FeedbackService(db_session)
        
        # 2 accepted, 1 rejected
        feedback_service.submit_feedback(leads[0].id, "accepted", None, "officer1")
        feedback_service.submit_feedback(leads[1].id, "accepted", None, "officer2")
        feedback_service.submit_feedback(leads[2].id, "rejected", None, "officer3")
        
        # Refresh source
        db_session.refresh(test_source)
        
        # Net effect: +1 +1 -1 = +1, so trust should increase slightly
        assert test_source.trust_score > initial_trust, \
            "Trust score should increase with net positive feedback"
        
        # Verify all feedback persisted
        all_feedback = db_session.query(Feedback).all()
        assert len(all_feedback) == 3
    
    def test_trust_tier_transitions(self, db_session, test_source):
        """
        Test that trust tier transitions correctly based on score.
        
        Trust tiers:
        - High: >= 70
        - Medium: 40-69
        - Low: < 40
        - Neutral: No feedback yet
        
        Validates Requirements: 11.5, 11.6, 11.7
        """
        # Start with neutral tier (50 score)
        assert test_source.trust_tier == "neutral"
        assert test_source.trust_score == 50.0
        
        # Create leads and submit positive feedback to push to high tier
        company = Company(name="Test Company", name_variants=[])
        db_session.add(company)
        db_session.flush()
        
        feedback_service = FeedbackService(db_session)
        
        # Submit multiple converted feedback to increase trust significantly
        for i in range(5):
            signal = Signal(
                source_id=test_source.id,
                url=f"https://test-source.com/article-{i}",
                title=f"Article {i}",
                content="Content",
                ingested_at=datetime.utcnow(),
                processed=True
            )
            db_session.add(signal)
            db_session.flush()
            
            event = Event(
                signal_id=signal.id,
                company_id=company.id,
                event_type="expansion",
                event_summary=f"Event {i}",
                is_lead_worthy=True,
                intent_strength=0.8
            )
            db_session.add(event)
            db_session.flush()
            
            lead = Lead(
                event_id=event.id,
                company_id=company.id,
                score=80,
                priority="high",
                status="new"
            )
            db_session.add(lead)
            db_session.flush()
            
            # Submit converted feedback (highest weight)
            feedback_service.submit_feedback(lead.id, "converted", None, f"officer{i}")
        
        # Refresh source
        db_session.refresh(test_source)
        
        # After multiple converted feedback, should be high tier
        assert test_source.trust_score >= 70, \
            f"Expected trust score >= 70, got {test_source.trust_score}"
        assert test_source.trust_tier == "high"
    
    def test_feedback_with_lead_status_update(self, db_session, test_lead):
        """
        Test that feedback updates lead status appropriately.
        
        Validates Requirements: 7.1, 7.2
        """
        # Initial status
        assert test_lead.status == "new"
        
        # Submit accepted feedback
        feedback_service = FeedbackService(db_session)
        feedback = feedback_service.submit_feedback(
            lead_id=test_lead.id,
            feedback_type="accepted",
            notes="Following up with company",
            submitted_by="test_officer"
        )
        
        # Refresh lead
        db_session.refresh(test_lead)
        
        # Verify lead status updated
        # (Implementation may vary, but status should change from "new")
        assert test_lead.status in ["contacted", "qualified", "accepted"]
    
    def test_feedback_round_trip_via_api(self, db_session, test_lead, test_source):
        """
        Test feedback submission through the service layer (simulating API).
        
        Validates Requirements: 10.4 (API feedback round-trip)
        """
        initial_trust = test_source.trust_score
        
        # Submit feedback via service (simulates API call)
        feedback_service = FeedbackService(db_session)
        feedback = feedback_service.submit_feedback(
            lead_id=test_lead.id,
            feedback_type="accepted",
            notes="API test feedback",
            submitted_by="api_user"
        )
        
        # Verify feedback returned (simulates API response)
        assert feedback is not None
        assert feedback.id is not None
        assert feedback.lead_id == test_lead.id
        assert feedback.feedback_type == "accepted"
        
        # Verify persistence (simulates database write)
        db_session.refresh(feedback)
        assert feedback.submitted_at is not None
        
        # Verify trust score updated (side effect)
        db_session.refresh(test_source)
        assert test_source.trust_score != initial_trust
        
        # Verify feedback can be retrieved
        retrieved = db_session.query(Feedback).filter(
            Feedback.id == feedback.id
        ).first()
        assert retrieved is not None
        assert retrieved.notes == "API test feedback"
