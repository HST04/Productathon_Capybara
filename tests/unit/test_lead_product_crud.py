"""Unit tests for LeadProduct CRUD operations."""

import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.lead_product import LeadProduct
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
def sample_lead(db_session):
    """Create a sample lead for testing."""
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
    
    lead = Lead(
        id=uuid.uuid4(),
        event_id=event.id,
        company_id=company.id,
        score=75,
        priority='high'
    )
    db_session.add(lead)
    db_session.commit()
    
    return lead


def test_create_lead_product(db_session, sample_lead):
    """Test creating a single product recommendation."""
    product = LeadProduct.create(
        db=db_session,
        lead_id=sample_lead.id,
        product_name='High Speed Diesel',
        confidence_score=0.85,
        reasoning='Direct mention of diesel indicates need for HSD',
        reason_code='keyword_match',
        rank=1,
        uncertainty_flag=False
    )
    
    assert product.id is not None
    assert product.lead_id == sample_lead.id
    assert product.product_name == 'High Speed Diesel'
    assert product.confidence_score == 0.85
    assert product.reasoning == 'Direct mention of diesel indicates need for HSD'
    assert product.reason_code == 'keyword_match'
    assert product.rank == 1
    assert product.uncertainty_flag is False


def test_create_batch_lead_products(db_session, sample_lead):
    """Test creating multiple product recommendations in batch."""
    products_data = [
        {
            'product_name': 'High Speed Diesel',
            'confidence_score': 0.90,
            'reasoning': 'Direct keyword match',
            'reason_code': 'keyword_match',
            'rank': 1,
            'uncertainty_flag': False
        },
        {
            'product_name': 'Furnace Oil',
            'confidence_score': 0.75,
            'reasoning': 'Boiler operations suggest FO',
            'reason_code': 'operational_cue',
            'rank': 2,
            'uncertainty_flag': False
        },
        {
            'product_name': 'Light Diesel Oil',
            'confidence_score': 0.55,
            'reasoning': 'Alternative fuel option',
            'reason_code': 'inference',
            'rank': 3,
            'uncertainty_flag': True
        }
    ]
    
    products = LeadProduct.create_batch(
        db=db_session,
        lead_id=sample_lead.id,
        products=products_data
    )
    
    assert len(products) == 3
    assert products[0].product_name == 'High Speed Diesel'
    assert products[1].product_name == 'Furnace Oil'
    assert products[2].product_name == 'Light Diesel Oil'
    assert products[2].uncertainty_flag is True


def test_get_by_lead_id(db_session, sample_lead):
    """Test retrieving all products for a lead."""
    # Create multiple products
    products_data = [
        {
            'product_name': 'Product 1',
            'confidence_score': 0.90,
            'reasoning': 'Reason 1',
            'rank': 1
        },
        {
            'product_name': 'Product 2',
            'confidence_score': 0.80,
            'reasoning': 'Reason 2',
            'rank': 2
        }
    ]
    
    LeadProduct.create_batch(db=db_session, lead_id=sample_lead.id, products=products_data)
    
    # Retrieve products
    products = LeadProduct.get_by_lead_id(db=db_session, lead_id=sample_lead.id)
    
    assert len(products) == 2
    assert products[0].rank == 1
    assert products[1].rank == 2


def test_get_by_id(db_session, sample_lead):
    """Test retrieving a product by ID."""
    product = LeadProduct.create(
        db=db_session,
        lead_id=sample_lead.id,
        product_name='Test Product',
        confidence_score=0.85,
        reasoning='Test reasoning'
    )
    
    retrieved = LeadProduct.get_by_id(db=db_session, product_id=product.id)
    
    assert retrieved is not None
    assert retrieved.id == product.id
    assert retrieved.product_name == 'Test Product'


def test_update_lead_product(db_session, sample_lead):
    """Test updating a product recommendation."""
    product = LeadProduct.create(
        db=db_session,
        lead_id=sample_lead.id,
        product_name='Original Product',
        confidence_score=0.70,
        reasoning='Original reasoning'
    )
    
    updated = LeadProduct.update(
        db=db_session,
        product_id=product.id,
        confidence_score=0.85,
        reasoning='Updated reasoning'
    )
    
    assert updated is not None
    assert updated.confidence_score == 0.85
    assert updated.reasoning == 'Updated reasoning'
    assert updated.product_name == 'Original Product'  # Unchanged


def test_delete_lead_product(db_session, sample_lead):
    """Test deleting a product recommendation."""
    product = LeadProduct.create(
        db=db_session,
        lead_id=sample_lead.id,
        product_name='Test Product',
        confidence_score=0.85,
        reasoning='Test reasoning'
    )
    
    result = LeadProduct.delete(db=db_session, product_id=product.id)
    
    assert result is True
    
    # Verify deletion
    retrieved = LeadProduct.get_by_id(db=db_session, product_id=product.id)
    assert retrieved is None


def test_delete_by_lead_id(db_session, sample_lead):
    """Test deleting all products for a lead."""
    products_data = [
        {
            'product_name': 'Product 1',
            'confidence_score': 0.90,
            'reasoning': 'Reason 1',
            'rank': 1
        },
        {
            'product_name': 'Product 2',
            'confidence_score': 0.80,
            'reasoning': 'Reason 2',
            'rank': 2
        }
    ]
    
    LeadProduct.create_batch(db=db_session, lead_id=sample_lead.id, products=products_data)
    
    count = LeadProduct.delete_by_lead_id(db=db_session, lead_id=sample_lead.id)
    
    assert count == 2
    
    # Verify deletion
    products = LeadProduct.get_by_lead_id(db=db_session, lead_id=sample_lead.id)
    assert len(products) == 0


def test_uncertainty_flag_for_low_confidence(db_session, sample_lead):
    """Test that uncertainty flag is set for low confidence scores."""
    product = LeadProduct.create(
        db=db_session,
        lead_id=sample_lead.id,
        product_name='Low Confidence Product',
        confidence_score=0.45,
        reasoning='Weak inference',
        uncertainty_flag=True
    )
    
    assert product.uncertainty_flag is True
    assert product.confidence_score < 0.60
