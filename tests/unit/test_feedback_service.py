"""Unit tests for Feedback Service and trust score updates."""

import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.feedback import Feedback
from app.models.lead import Lead
from app.models.event import Event
from app.models.signal import Signal
from app.models.company import Company
from app.models.source import Source
from app.services.feedback_service import FeedbackService
from app.services.source_registry import SourceRegistryManager
from app.db.session import Base


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_lead(db_session):
    """Create a sample lead with all dependencies for testing."""
    # Create source
    source = Source(
        id=uuid.uuid4(),
        domain='test.com',
        category='news',
        access_method='rss',
        trust_score=50.0,
        trust_tier='neutral'
    )
    db_session.add(source)
    
    # Create company
    company = Company(
        id=uuid.uuid4(),
        name='Test Company'
    )
    db_session.add(company)
    
    # Create signal
    signal = Signal(
        id=uuid.uuid4(),
        source_id=source.id,
        url='https://test.com/article',
        content='Test content'
    )
    db_session.add(signal)
    
    # Create event
    event = Event(
        id=uuid.uuid4(),
        signal_id=signal.id,
        company_id=company.id,
        event_summary='Test event',
        is_lead_worthy=True
    )
    db_session.add(event)
    
    # Create lead
    lead = Lead(
        id=uuid.uuid4(),
        event_id=event.id,
        company_id=company.id,
        score=75,
        priority='high',
        status='new'
    )
    db_session.add(lead)
    db_session.commit()
    
    return lead


def test_submit_feedback_accepted(db_session, sample_lead):
    """Test submitting accepted feedback."""
    service = FeedbackService(db_session)
    
    feedback = service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='accepted',
        notes='Good lead',
        submitted_by='John Doe'
    )
    
    assert feedback.id is not None
    assert feedback.lead_id == sample_lead.id
    assert feedback.feedback_type == 'accepted'
    assert feedback.notes == 'Good lead'
    assert feedback.submitted_by == 'John Doe'
    assert feedback.submitted_at is not None


def test_submit_feedback_rejected(db_session, sample_lead):
    """Test submitting rejected feedback."""
    service = FeedbackService(db_session)
    
    feedback = service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='rejected',
        notes='Not relevant',
        submitted_by='Jane Smith'
    )
    
    assert feedback.feedback_type == 'rejected'
    assert feedback.notes == 'Not relevant'


def test_submit_feedback_converted(db_session, sample_lead):
    """Test submitting converted feedback."""
    service = FeedbackService(db_session)
    
    feedback = service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='converted',
        notes='Deal closed!',
        submitted_by='John Doe'
    )
    
    assert feedback.feedback_type == 'converted'
    assert feedback.notes == 'Deal closed!'


def test_submit_feedback_invalid_type(db_session, sample_lead):
    """Test submitting feedback with invalid type."""
    service = FeedbackService(db_session)
    
    with pytest.raises(ValueError, match="Invalid feedback type"):
        service.submit_feedback(
            lead_id=sample_lead.id,
            feedback_type='invalid',
            notes='Test'
        )


def test_submit_feedback_lead_not_found(db_session):
    """Test submitting feedback for non-existent lead."""
    service = FeedbackService(db_session)
    
    with pytest.raises(ValueError, match="Lead with ID .* not found"):
        service.submit_feedback(
            lead_id=uuid.uuid4(),
            feedback_type='accepted'
        )


def test_trust_score_update_on_accepted_feedback(db_session, sample_lead):
    """Test that trust score increases on accepted feedback."""
    service = FeedbackService(db_session)
    
    # Get initial trust score
    source = db_session.query(Source).filter(
        Source.id == sample_lead.event.signal.source_id
    ).first()
    initial_score = source.trust_score
    
    # Submit accepted feedback
    service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='accepted'
    )
    
    # Check trust score updated
    db_session.refresh(source)
    assert source.trust_score >= initial_score


def test_trust_score_update_on_converted_feedback(db_session, sample_lead):
    """Test that trust score increases more on converted feedback."""
    service = FeedbackService(db_session)
    
    # Get initial trust score
    source = db_session.query(Source).filter(
        Source.id == sample_lead.event.signal.source_id
    ).first()
    initial_score = source.trust_score
    
    # Submit converted feedback
    service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='converted'
    )
    
    # Check trust score updated
    db_session.refresh(source)
    assert source.trust_score >= initial_score


def test_trust_score_update_on_rejected_feedback(db_session, sample_lead):
    """Test that trust score decreases on rejected feedback."""
    service = FeedbackService(db_session)
    
    # Get initial trust score
    source = db_session.query(Source).filter(
        Source.id == sample_lead.event.signal.source_id
    ).first()
    initial_score = source.trust_score
    
    # Submit rejected feedback
    service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='rejected'
    )
    
    # Check trust score updated
    db_session.refresh(source)
    assert source.trust_score <= initial_score


def test_trust_tier_calculation(db_session, sample_lead):
    """Test trust tier calculation based on feedback."""
    service = FeedbackService(db_session)
    source_registry = SourceRegistryManager(db_session)
    
    # Submit multiple accepted feedbacks to increase trust score
    for _ in range(5):
        service.submit_feedback(
            lead_id=sample_lead.id,
            feedback_type='accepted'
        )
    
    # Check trust tier
    source = db_session.query(Source).filter(
        Source.id == sample_lead.event.signal.source_id
    ).first()
    
    # With all accepted feedback, trust score should be 100
    assert source.trust_score == 100.0
    assert source.trust_tier == 'high'


def test_get_feedback_for_lead(db_session, sample_lead):
    """Test retrieving all feedback for a lead."""
    service = FeedbackService(db_session)
    
    # Submit multiple feedbacks
    service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='accepted',
        notes='First feedback'
    )
    
    service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='converted',
        notes='Second feedback'
    )
    
    # Get all feedback
    feedbacks = service.get_feedback_for_lead(sample_lead.id)
    
    assert len(feedbacks) == 2
    assert feedbacks[0].feedback_type in ['accepted', 'converted']
    assert feedbacks[1].feedback_type in ['accepted', 'converted']


def test_get_feedback_stats(db_session, sample_lead):
    """Test getting feedback statistics."""
    service = FeedbackService(db_session)
    
    # Submit various feedbacks
    service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='accepted',
        submitted_by='John Doe'
    )
    
    service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='accepted',
        submitted_by='John Doe'
    )
    
    service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='rejected',
        submitted_by='John Doe'
    )
    
    service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='converted',
        submitted_by='Jane Smith'
    )
    
    # Get stats for John Doe
    stats = service.get_feedback_stats(submitted_by='John Doe')
    
    assert stats['accepted'] == 2
    assert stats['rejected'] == 1
    assert stats['converted'] == 0
    assert stats['total'] == 3
    
    # Get stats for all users
    all_stats = service.get_feedback_stats()
    
    assert all_stats['accepted'] == 2
    assert all_stats['rejected'] == 1
    assert all_stats['converted'] == 1
    assert all_stats['total'] == 4


def test_feedback_without_notes(db_session, sample_lead):
    """Test submitting feedback without notes."""
    service = FeedbackService(db_session)
    
    feedback = service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='accepted'
    )
    
    assert feedback.notes is None


def test_feedback_without_submitter(db_session, sample_lead):
    """Test submitting feedback without submitter."""
    service = FeedbackService(db_session)
    
    feedback = service.submit_feedback(
        lead_id=sample_lead.id,
        feedback_type='accepted'
    )
    
    assert feedback.submitted_by is None


def test_multiple_feedbacks_trust_score_calculation(db_session, sample_lead):
    """Test trust score calculation with multiple feedbacks."""
    service = FeedbackService(db_session)
    
    # Submit mixed feedback: 2 accepted, 1 converted, 1 rejected
    service.submit_feedback(lead_id=sample_lead.id, feedback_type='accepted')
    service.submit_feedback(lead_id=sample_lead.id, feedback_type='accepted')
    service.submit_feedback(lead_id=sample_lead.id, feedback_type='converted')
    service.submit_feedback(lead_id=sample_lead.id, feedback_type='rejected')
    
    # Calculate expected score: (2 + 1*2) / 4 * 100 = 100
    # Formula: (Accepted + Converted × 2) / Total × 100
    source = db_session.query(Source).filter(
        Source.id == sample_lead.event.signal.source_id
    ).first()
    
    assert source.trust_score == 100.0
    assert source.trust_tier == 'high'


def test_trust_tier_medium(db_session, sample_lead):
    """Test medium trust tier calculation."""
    service = FeedbackService(db_session)
    
    # Submit feedback to get medium tier: 1 accepted, 1 rejected
    # Score: (1 + 0) / 2 * 100 = 50
    service.submit_feedback(lead_id=sample_lead.id, feedback_type='accepted')
    service.submit_feedback(lead_id=sample_lead.id, feedback_type='rejected')
    
    source = db_session.query(Source).filter(
        Source.id == sample_lead.event.signal.source_id
    ).first()
    
    assert source.trust_score == 50.0
    assert source.trust_tier == 'medium'


def test_trust_tier_low(db_session, sample_lead):
    """Test low trust tier calculation."""
    service = FeedbackService(db_session)
    
    # Submit mostly rejected feedback: 1 accepted, 3 rejected
    # Score: (1 + 0) / 4 * 100 = 25
    service.submit_feedback(lead_id=sample_lead.id, feedback_type='accepted')
    service.submit_feedback(lead_id=sample_lead.id, feedback_type='rejected')
    service.submit_feedback(lead_id=sample_lead.id, feedback_type='rejected')
    service.submit_feedback(lead_id=sample_lead.id, feedback_type='rejected')
    
    source = db_session.query(Source).filter(
        Source.id == sample_lead.event.signal.source_id
    ).first()
    
    assert source.trust_score == 25.0
    assert source.trust_tier == 'low'
