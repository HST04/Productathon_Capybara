"""
Integration tests for the complete signal-to-lead pipeline.

Tests the full workflow from signal ingestion through lead generation,
including entity extraction, company resolution, event classification,
product inference, and lead scoring.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, MagicMock

from app.models.signal import Signal
from app.models.source import Source
from app.models.company import Company
from app.models.event import Event
from app.models.lead import Lead
from app.models.lead_product import LeadProduct
from app.models.sales_officer import SalesOfficer
from app.worker import BackgroundWorker
from app.services.ingestion import IngestionService
from app.services.entity_extractor import EntityExtractor, ExtractedEntities, CompanyMention
from app.services.event_classifier import EventClassifier, EventClassification


@pytest.fixture
def db_session():
    """Create a test database session."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        # Clean up test data
        db.query(LeadProduct).delete()
        db.query(Lead).delete()
        db.query(Event).delete()
        db.query(Signal).delete()
        db.query(Company).delete()
        db.query(Source).delete()
        db.query(SalesOfficer).delete()
        db.commit()
        db.close()


@pytest.fixture
def test_source(db_session):
    """Create a test source."""
    source = Source(
        domain="test-news.com",
        category="news",
        access_method="rss",
        trust_score=75.0,
        trust_tier="high"
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


@pytest.fixture
def test_sales_officer(db_session):
    """Create a test sales officer."""
    officer = SalesOfficer(
        name="Test Officer",
        phone_number="+919876543210",
        whatsapp_opt_in=True,
        territories=["Mumbai", "Maharashtra"]
    )
    db_session.add(officer)
    db_session.commit()
    db_session.refresh(officer)
    return officer


@pytest.mark.integration
class TestFullPipeline:
    """Test the complete pipeline from ingestion to lead generation."""
    
    def test_complete_pipeline_expansion_signal(self, db_session, test_source, test_sales_officer):
        """
        Test complete pipeline with an expansion signal.
        
        Validates Requirements: 8.1 (Lead generation timeliness)
        """
        # Create a signal about a company expansion
        signal = Signal(
            source_id=test_source.id,
            url="https://test-news.com/abc-industries-expansion",
            title="ABC Industries announces 500 crore expansion in Mumbai",
            content="""
            ABC Industries Ltd announced a major expansion of their manufacturing facility
            in Mumbai. The company plans to invest 500 crore rupees to install new boilers
            and furnaces for increased production capacity. The expansion is expected to
            be completed by December 2026. ABC Industries (CIN: L12345MH2000PLC123456)
            operates in the chemical manufacturing sector.
            """,
            ingested_at=datetime.utcnow(),
            processed=False
        )
        db_session.add(signal)
        db_session.commit()
        db_session.refresh(signal)
        
        # Mock the LLM calls
        with patch.object(EntityExtractor, 'extract_entities') as mock_extract, \
             patch.object(EventClassifier, 'classify_event') as mock_classify:
            
            # Mock entity extraction
            mock_extract.return_value = ExtractedEntities(
                companies=[
                    CompanyMention(
                        name="ABC Industries Ltd",
                        name_variants=["ABC Industries", "ABC Ltd"],
                        cin="L12345MH2000PLC123456",
                        gst=None,
                        website=None,
                        industry="Chemical Manufacturing",
                        address=None,
                        locations=["Mumbai"]
                    )
                ],
                location=Mock(full_location="Mumbai"),
                capacity=Mock(value="500 crore"),
                product_keywords=["boiler", "furnace"],
                operational_cues=["boilers", "furnaces"]
            )
            
            # Mock event classification
            mock_classify.return_value = EventClassification(
                is_lead_worthy=True,
                event_type="expansion",
                event_summary="Manufacturing facility expansion with new boilers and furnaces",
                location="Mumbai",
                capacity="500 crore",
                deadline=datetime(2026, 12, 31).date(),
                intent_strength=0.85
            )
            
            # Process the signal through the pipeline
            worker = BackgroundWorker()
            start_time = datetime.utcnow()
            success = worker.process_signal(db_session, signal)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Verify processing succeeded
            assert success is True
            
            # Verify processing time (should be < 2 minutes)
            assert processing_time < 120, f"Processing took {processing_time}s, should be < 120s"
            
            # Verify signal marked as processed
            db_session.refresh(signal)
            assert signal.processed is True
            assert signal.processed_at is not None
            
            # Verify company created
            company = db_session.query(Company).filter(
                Company.name == "ABC Industries Ltd"
            ).first()
            assert company is not None
            assert company.cin == "L12345MH2000PLC123456"
            assert company.industry == "Chemical Manufacturing"
            
            # Verify event created
            event = db_session.query(Event).filter(
                Event.signal_id == signal.id
            ).first()
            assert event is not None
            assert event.company_id == company.id
            assert event.event_type == "expansion"
            assert event.is_lead_worthy is True
            assert event.intent_strength == 0.85
            
            # Verify lead created
            lead = db_session.query(Lead).filter(
                Lead.event_id == event.id
            ).first()
            assert lead is not None
            assert lead.company_id == company.id
            assert lead.priority in ["high", "medium", "low"]
            assert 0 <= lead.score <= 100
            
            # Verify lead assigned to correct territory
            assert lead.assigned_to == "Test Officer"
            assert lead.territory == "Mumbai"
            
            # Verify product recommendations created
            products = db_session.query(LeadProduct).filter(
                LeadProduct.lead_id == lead.id
            ).order_by(LeadProduct.rank).all()
            assert len(products) > 0
            assert len(products) <= 3  # Top 3 products
            
            # Verify products are relevant (should include FO or LDO for boilers/furnaces)
            product_names = [p.product_name for p in products]
            assert any(name in ["Furnace Oil (FO)", "Light Diesel Oil (LDO)"] for name in product_names)
            
            # Verify product metadata
            for product in products:
                assert product.confidence_score > 0
                assert product.reasoning is not None
                assert product.reason_code is not None
    
    def test_pipeline_with_non_lead_worthy_signal(self, db_session, test_source):
        """
        Test pipeline correctly filters out non-lead-worthy signals.
        
        Validates Requirements: 3.6 (Lead-worthiness filtering)
        """
        # Create a non-lead-worthy signal (general news)
        signal = Signal(
            source_id=test_source.id,
            url="https://test-news.com/general-article",
            title="Industry trends in 2026",
            content="General article about industry trends without specific opportunities.",
            ingested_at=datetime.utcnow(),
            processed=False
        )
        db_session.add(signal)
        db_session.commit()
        db_session.refresh(signal)
        
        # Mock the LLM calls
        with patch.object(EntityExtractor, 'extract_entities') as mock_extract, \
             patch.object(EventClassifier, 'classify_event') as mock_classify:
            
            mock_extract.return_value = ExtractedEntities(
                companies=[
                    CompanyMention(
                        name="Various Companies",
                        name_variants=[],
                        cin=None,
                        gst=None,
                        website=None,
                        industry=None,
                        address=None,
                        locations=None
                    )
                ],
                location=None,
                capacity=None,
                product_keywords=[],
                operational_cues=[]
            )
            
            mock_classify.return_value = EventClassification(
                is_lead_worthy=False,
                event_type="general_news",
                event_summary="General industry trends article",
                location=None,
                capacity=None,
                deadline=None,
                intent_strength=0.2
            )
            
            # Process the signal
            worker = BackgroundWorker()
            success = worker.process_signal(db_session, signal)
            
            # Verify processing succeeded
            assert success is True
            
            # Verify signal marked as processed
            db_session.refresh(signal)
            assert signal.processed is True
            
            # Verify event created but marked as not lead-worthy
            event = db_session.query(Event).filter(
                Event.signal_id == signal.id
            ).first()
            assert event is not None
            assert event.is_lead_worthy is False
            
            # Verify NO lead was created
            lead = db_session.query(Lead).filter(
                Lead.event_id == event.id
            ).first()
            assert lead is None
    
    def test_pipeline_with_tender_signal(self, db_session, test_source, test_sales_officer):
        """
        Test pipeline with high-intent tender signal.
        
        Should result in high-priority lead.
        """
        # Create a tender signal
        signal = Signal(
            source_id=test_source.id,
            url="https://test-news.com/tender-xyz",
            title="XYZ Corp issues tender for diesel supply",
            content="""
            XYZ Corporation has issued a tender for supply of 10,000 liters of
            High Speed Diesel (HSD) for their warehouse operations in Pune.
            Deadline for submission is March 15, 2026. Contact: procurement@xyzcorp.com
            """,
            ingested_at=datetime.utcnow(),
            processed=False
        )
        db_session.add(signal)
        db_session.commit()
        db_session.refresh(signal)
        
        # Mock the LLM calls
        with patch.object(EntityExtractor, 'extract_entities') as mock_extract, \
             patch.object(EventClassifier, 'classify_event') as mock_classify:
            
            mock_extract.return_value = ExtractedEntities(
                companies=[
                    CompanyMention(
                        name="XYZ Corporation",
                        name_variants=["XYZ Corp"],
                        cin=None,
                        gst=None,
                        website=None,
                        industry=None,
                        address=None,
                        locations=["Pune"]
                    )
                ],
                location=Mock(full_location="Pune"),
                capacity=Mock(value="10,000 liters"),
                product_keywords=["HSD", "diesel"],
                operational_cues=["warehouse"]
            )
            
            mock_classify.return_value = EventClassification(
                is_lead_worthy=True,
                event_type="tender",
                event_summary="Tender for HSD supply for warehouse operations",
                location="Pune",
                capacity="10,000 liters",
                deadline=datetime(2026, 3, 15).date(),
                intent_strength=1.0  # Explicit tender = maximum intent
            )
            
            # Process the signal
            worker = BackgroundWorker()
            success = worker.process_signal(db_session, signal)
            
            assert success is True
            
            # Verify lead created with high priority
            lead = db_session.query(Lead).join(Event).filter(
                Event.signal_id == signal.id
            ).first()
            assert lead is not None
            
            # High intent + fresh signal + explicit product = high score
            assert lead.score >= 70, f"Expected high score, got {lead.score}"
            assert lead.priority == "high"
            
            # Verify HSD product recommended
            products = db_session.query(LeadProduct).filter(
                LeadProduct.lead_id == lead.id
            ).all()
            product_names = [p.product_name for p in products]
            assert "High Speed Diesel (HSD)" in product_names
    
    def test_pipeline_error_handling(self, db_session, test_source):
        """
        Test pipeline handles errors gracefully without crashing.
        
        Validates Requirements: 8.2 (Continuous processing without manual intervention)
        """
        # Create a signal
        signal = Signal(
            source_id=test_source.id,
            url="https://test-news.com/test",
            title="Test signal",
            content="Test content",
            ingested_at=datetime.utcnow(),
            processed=False
        )
        db_session.add(signal)
        db_session.commit()
        db_session.refresh(signal)
        
        # Mock entity extraction to raise an error
        with patch.object(EntityExtractor, 'extract_entities') as mock_extract:
            mock_extract.side_effect = Exception("Simulated extraction error")
            
            # Process the signal
            worker = BackgroundWorker()
            success = worker.process_signal(db_session, signal)
            
            # Verify processing failed gracefully
            assert success is False
            
            # Verify signal NOT marked as processed
            db_session.refresh(signal)
            assert signal.processed is False
            
            # Verify error logged for manual review
            failed_signals = worker.get_failed_signals()
            assert str(signal.id) in failed_signals
    
    def test_multiple_signals_batch_processing(self, db_session, test_source, test_sales_officer):
        """
        Test processing multiple signals in a batch.
        
        Validates Requirements: 8.2 (Continuous processing)
        """
        # Create multiple signals
        signals = []
        for i in range(3):
            signal = Signal(
                source_id=test_source.id,
                url=f"https://test-news.com/signal-{i}",
                title=f"Test Signal {i}",
                content=f"Company {i} announces expansion with boilers in Mumbai",
                ingested_at=datetime.utcnow(),
                processed=False
            )
            db_session.add(signal)
            signals.append(signal)
        
        db_session.commit()
        
        # Mock the LLM calls
        with patch.object(EntityExtractor, 'extract_entities') as mock_extract, \
             patch.object(EventClassifier, 'classify_event') as mock_classify:
            
            def extract_side_effect(text, title):
                return ExtractedEntities(
                    companies=[
                        CompanyMention(
                            name=f"Company {title.split()[-1]}",
                            name_variants=[],
                            cin=None,
                            gst=None,
                            website=None,
                            industry=None,
                            address=None,
                            locations=["Mumbai"]
                        )
                    ],
                    location=Mock(full_location="Mumbai"),
                    capacity=None,
                    product_keywords=["boiler"],
                    operational_cues=["boilers"]
                )
            
            mock_extract.side_effect = extract_side_effect
            
            mock_classify.return_value = EventClassification(
                is_lead_worthy=True,
                event_type="expansion",
                event_summary="Expansion with boilers",
                location="Mumbai",
                capacity=None,
                deadline=None,
                intent_strength=0.7
            )
            
            # Process all signals
            worker = BackgroundWorker()
            worker.process_signals()
            
            # Verify all signals processed
            for signal in signals:
                db_session.refresh(signal)
                assert signal.processed is True
            
            # Verify leads created for all signals
            leads = db_session.query(Lead).all()
            assert len(leads) == 3
