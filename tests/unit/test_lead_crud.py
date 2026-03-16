"""Unit tests for Lead CRUD operations."""

import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.lead import Lead
from app.models.event import Event
from app.models.signal import Signal
from app.models.company import Company
from app.models.source import Source
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
def sample_event(db_session):
    """Create a sample event for testing."""
    # Create dependencies
    source = Source(
        id=uuid.uuid4(),
        domain='test.com',
        category='news',
        access_method='rss'
    )
    db_session.add(source)
    
    company = Company(
        id=uuid.uuid4(),
        name='Test Company'
    )
    db_session.add(company)
    
    signal = Signal(
        id=uuid.uuid4(),
        source_id=source.id,
        url='https://test.com/article',
        content='Test content'
    )
    db_session.add(signal)
    
    event = Event(
        id=uuid.uuid4(),
        signal_id=signal.id,
        company_id=company.id,
        event_summary='Test event',
        is_lead_worthy=True
    )
    db_session.add(event)
    db_session.commit()
    
    return event


def test_create_lead(db_session, sample_event):
    """Test creating a lead."""
    lead = Lead.create(
        db=db_session,
        event_id=sample_event.id,
        company_id=sample_event.company_id,
        score=85,
        priority='high',
        assigned_to='John Doe',
        territory='Mumbai',
        status='new'
    )
    
    assert lead.id is not None
    assert lead.event_id == sample_event.id
    assert lead.company_id == sample_event.company_id
    assert lead.score == 85
    assert lead.priority == 'high'
    assert lead.assigned_to == 'John Doe'
    assert lead.territory == 'Mumbai'
    assert lead.status == 'new'
    assert lead.created_at is not None


def test_get_by_id(db_session, sample_event):
    """Test retrieving a lead by ID."""
    lead = Lead.create(
        db=db_session,
        event_id=sample_event.id,
        company_id=sample_event.company_id,
        score=75,
        priority='high'
    )
    
    retrieved = Lead.get_by_id(db=db_session, lead_id=lead.id)
    
    assert retrieved is not None
    assert retrieved.id == lead.id
    assert retrieved.score == 75


def test_get_by_id_not_found(db_session):
    """Test retrieving a non-existent lead."""
    result = Lead.get_by_id(db=db_session, lead_id=uuid.uuid4())
    assert result is None


def test_get_by_event_id(db_session, sample_event):
    """Test retrieving a lead by event ID."""
    lead = Lead.create(
        db=db_session,
        event_id=sample_event.id,
        company_id=sample_event.company_id,
        score=80,
        priority='high'
    )
    
    retrieved = Lead.get_by_event_id(db=db_session, event_id=sample_event.id)
    
    assert retrieved is not None
    assert retrieved.id == lead.id
    assert retrieved.event_id == sample_event.id


def test_list_leads_no_filters(db_session, sample_event):
    """Test listing all leads without filters."""
    # Create multiple leads
    lead1 = Lead.create(
        db=db_session,
        event_id=sample_event.id,
        company_id=sample_event.company_id,
        score=85,
        priority='high'
    )
    
    # Create another event for second lead
    signal2 = Signal(
        id=uuid.uuid4(),
        source_id=sample_event.signal.source_id,
        url='https://test.com/article2',
        content='Test content 2'
    )
    db_session.add(signal2)
    
    event2 = Event(
        id=uuid.uuid4(),
        signal_id=signal2.id,
        company_id=sample_event.company_id,
        event_summary='Test event 2',
        is_lead_worthy=True
    )
    db_session.add(event2)
    db_session.commit()
    
    lead2 = Lead.create(
        db=db_session,
        event_id=event2.id,
        company_id=sample_event.company_id,
        score=55,
        priority='medium'
    )
    
    leads = Lead.list_leads(db=db_session)
    
    assert len(leads) == 2


def test_list_leads_filter_by_priority(db_session, sample_event):
    """Test listing leads filtered by priority."""
    # Create high priority lead
    lead1 = Lead.create(
        db=db_session,
        event_id=sample_event.id,
        company_id=sample_event.company_id,
        score=85,
        priority='high'
    )
    
    # Create another event for medium priority lead
    signal2 = Signal(
        id=uuid.uuid4(),
        source_id=sample_event.signal.source_id,
        url='https://test.com/article2',
        content='Test content 2'
    )
    db_session.add(signal2)
    
    event2 = Event(
        id=uuid.uuid4(),
        signal_id=signal2.id,
        company_id=sample_event.company_id,
        event_summary='Test event 2',
        is_lead_worthy=True
    )
    db_session.add(event2)
    db_session.commit()
    
    lead2 = Lead.create(
        db=db_session,
        event_id=event2.id,
        company_id=sample_event.company_id,
        score=55,
        priority='medium'
    )
    
    # Filter by high priority
    high_priority_leads = Lead.list_leads(db=db_session, priority='high')
    assert len(high_priority_leads) == 1
    assert high_priority_leads[0].priority == 'high'
    
    # Filter by medium priority
    medium_priority_leads = Lead.list_leads(db=db_session, priority='medium')
    assert len(medium_priority_leads) == 1
    assert medium_priority_leads[0].priority == 'medium'


def test_list_leads_filter_by_status(db_session, sample_event):
    """Test listing leads filtered by status."""
    lead = Lead.create(
        db=db_session,
        event_id=sample_event.id,
        company_id=sample_event.company_id,
        score=75,
        priority='high',
        status='contacted'
    )
    
    leads = Lead.list_leads(db=db_session, status='contacted')
    
    assert len(leads) == 1
    assert leads[0].status == 'contacted'


def test_list_leads_filter_by_assigned_to(db_session, sample_event):
    """Test listing leads filtered by assigned officer."""
    lead = Lead.create(
        db=db_session,
        event_id=sample_event.id,
        company_id=sample_event.company_id,
        score=75,
        priority='high',
        assigned_to='John Doe'
    )
    
    leads = Lead.list_leads(db=db_session, assigned_to='John Doe')
    
    assert len(leads) == 1
    assert leads[0].assigned_to == 'John Doe'


def test_list_leads_pagination(db_session, sample_event):
    """Test lead listing with pagination."""
    # Create multiple leads
    for i in range(5):
        signal = Signal(
            id=uuid.uuid4(),
            source_id=sample_event.signal.source_id,
            url=f'https://test.com/article{i}',
            content=f'Test content {i}'
        )
        db_session.add(signal)
        
        event = Event(
            id=uuid.uuid4(),
            signal_id=signal.id,
            company_id=sample_event.company_id,
            event_summary=f'Test event {i}',
            is_lead_worthy=True
        )
        db_session.add(event)
        db_session.commit()
        
        Lead.create(
            db=db_session,
            event_id=event.id,
            company_id=sample_event.company_id,
            score=70 + i,
            priority='high'
        )
    
    # Get first page (2 items)
    page1 = Lead.list_leads(db=db_session, limit=2, offset=0)
    assert len(page1) == 2
    
    # Get second page (2 items)
    page2 = Lead.list_leads(db=db_session, limit=2, offset=2)
    assert len(page2) == 2
    
    # Ensure different leads
    assert page1[0].id != page2[0].id


def test_update_lead(db_session, sample_event):
    """Test updating a lead."""
    lead = Lead.create(
        db=db_session,
        event_id=sample_event.id,
        company_id=sample_event.company_id,
        score=75,
        priority='high',
        status='new'
    )
    
    updated = Lead.update(
        db=db_session,
        lead_id=lead.id,
        status='contacted',
        assigned_to='Jane Smith'
    )
    
    assert updated is not None
    assert updated.status == 'contacted'
    assert updated.assigned_to == 'Jane Smith'
    assert updated.score == 75  # Unchanged


def test_update_lead_not_found(db_session):
    """Test updating a non-existent lead."""
    result = Lead.update(
        db=db_session,
        lead_id=uuid.uuid4(),
        status='contacted'
    )
    assert result is None


def test_delete_lead(db_session, sample_event):
    """Test deleting a lead."""
    lead = Lead.create(
        db=db_session,
        event_id=sample_event.id,
        company_id=sample_event.company_id,
        score=75,
        priority='high'
    )
    
    result = Lead.delete(db=db_session, lead_id=lead.id)
    
    assert result is True
    
    # Verify deletion
    retrieved = Lead.get_by_id(db=db_session, lead_id=lead.id)
    assert retrieved is None


def test_delete_lead_not_found(db_session):
    """Test deleting a non-existent lead."""
    result = Lead.delete(db=db_session, lead_id=uuid.uuid4())
    assert result is False


def test_count_leads_no_filters(db_session, sample_event):
    """Test counting all leads."""
    Lead.create(
        db=db_session,
        event_id=sample_event.id,
        company_id=sample_event.company_id,
        score=85,
        priority='high'
    )
    
    count = Lead.count_leads(db=db_session)
    assert count == 1


def test_count_leads_with_filters(db_session, sample_event):
    """Test counting leads with filters."""
    # Create high priority lead
    Lead.create(
        db=db_session,
        event_id=sample_event.id,
        company_id=sample_event.company_id,
        score=85,
        priority='high',
        status='new'
    )
    
    # Create another event for medium priority lead
    signal2 = Signal(
        id=uuid.uuid4(),
        source_id=sample_event.signal.source_id,
        url='https://test.com/article2',
        content='Test content 2'
    )
    db_session.add(signal2)
    
    event2 = Event(
        id=uuid.uuid4(),
        signal_id=signal2.id,
        company_id=sample_event.company_id,
        event_summary='Test event 2',
        is_lead_worthy=True
    )
    db_session.add(event2)
    db_session.commit()
    
    Lead.create(
        db=db_session,
        event_id=event2.id,
        company_id=sample_event.company_id,
        score=55,
        priority='medium',
        status='contacted'
    )
    
    # Count by priority
    high_count = Lead.count_leads(db=db_session, priority='high')
    assert high_count == 1
    
    medium_count = Lead.count_leads(db=db_session, priority='medium')
    assert medium_count == 1
    
    # Count by status
    new_count = Lead.count_leads(db=db_session, status='new')
    assert new_count == 1


def test_lead_relationships(db_session, sample_event):
    """Test lead relationships with event and company."""
    lead = Lead.create(
        db=db_session,
        event_id=sample_event.id,
        company_id=sample_event.company_id,
        score=75,
        priority='high'
    )
    
    # Test event relationship
    assert lead.event is not None
    assert lead.event.id == sample_event.id
    assert lead.event.event_summary == 'Test event'
    
    # Test company relationship
    assert lead.company is not None
    assert lead.company.id == sample_event.company_id
    assert lead.company.name == 'Test Company'
