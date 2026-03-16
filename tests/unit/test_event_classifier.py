"""Unit tests for Event Classifier."""

import pytest
from unittest.mock import Mock, MagicMock, patch
import uuid
from datetime import datetime

# Mock OpenAI before importing
import sys
sys.modules['openai'] = Mock()

from app.services.event_classifier import EventClassifier, EventClassification
from app.models.signal import Signal


@pytest.fixture
def classifier_no_llm():
    """Create classifier without LLM (rule-based only)."""
    return EventClassifier(openai_api_key=None)


@pytest.fixture
def mock_signal_tender():
    """Create a mock signal about a tender."""
    signal = Mock(spec=Signal)
    signal.id = uuid.uuid4()
    signal.title = "ABC Industries Issues Tender for Fuel Supply"
    signal.content = """ABC Industries Ltd has issued a tender for supply of 
    furnace oil and diesel for their new manufacturing plant in Gujarat. 
    The tender deadline is March 31, 2024. Capacity requirement is 500 MT per month."""
    signal.url = "https://example.com/tender"
    signal.ingested_at = datetime.now()
    return signal


@pytest.fixture
def mock_signal_expansion():
    """Create a mock signal about an expansion."""
    signal = Mock(spec=Signal)
    signal.id = uuid.uuid4()
    signal.title = "XYZ Corp Plans Major Expansion"
    signal.content = """XYZ Corporation announced plans to expand their 
    manufacturing facility in Maharashtra with a new 1000 MW power plant. 
    The expansion is expected to be completed by Q4 2024."""
    signal.url = "https://example.com/expansion"
    signal.ingested_at = datetime.now()
    return signal


@pytest.fixture
def mock_signal_non_lead():
    """Create a mock signal that is not lead-worthy."""
    signal = Mock(spec=Signal)
    signal.id = uuid.uuid4()
    signal.title = "Industry Conference Scheduled for Next Month"
    signal.content = """The annual petroleum industry conference will be held 
    next month in Mumbai. Industry leaders will discuss market trends and 
    future outlook. Registration is now open."""
    signal.url = "https://example.com/conference"
    signal.ingested_at = datetime.now()
    return signal


@pytest.fixture
def mock_signal_vague():
    """Create a mock signal with vague business mention."""
    signal = Mock(spec=Signal)
    signal.id = uuid.uuid4()
    signal.title = "Company Considering Future Growth"
    signal.content = """The company may consider expanding operations in the 
    future if market conditions improve. No specific plans have been announced."""
    signal.url = "https://example.com/vague"
    signal.ingested_at = datetime.now()
    return signal


class TestEventClassifierRuleBased:
    """Test rule-based event classification."""
    
    def test_classify_tender_as_lead_worthy(self, classifier_no_llm, mock_signal_tender):
        """Test that tender signals are classified as lead-worthy."""
        classification = classifier_no_llm.classify_event(mock_signal_tender)
        
        assert classification.is_lead_worthy is True
        assert classification.intent_strength >= 0.8
        assert classification.event_type == 'tender'
        assert len(classification.event_summary) > 0
        assert len(classification.reasoning) > 0
    
    def test_classify_expansion_as_lead_worthy(self, classifier_no_llm, mock_signal_expansion):
        """Test that expansion signals are classified as lead-worthy."""
        classification = classifier_no_llm.classify_event(mock_signal_expansion)
        
        assert classification.is_lead_worthy is True
        assert classification.intent_strength >= 0.6
        assert classification.event_type == 'expansion'
    
    def test_classify_conference_as_non_lead(self, classifier_no_llm, mock_signal_non_lead):
        """Test that conference signals are not lead-worthy."""
        classification = classifier_no_llm.classify_event(mock_signal_non_lead)
        
        assert classification.is_lead_worthy is False
        assert classification.intent_strength < 0.5
    
    def test_classify_vague_mention_low_intent(self, classifier_no_llm, mock_signal_vague):
        """Test that vague mentions have low intent strength."""
        classification = classifier_no_llm.classify_event(mock_signal_vague)
        
        assert classification.intent_strength <= 0.5
    
    def test_is_lead_worthy_quick_check(self, classifier_no_llm, mock_signal_tender):
        """Test quick lead-worthiness check."""
        is_worthy = classifier_no_llm.is_lead_worthy(mock_signal_tender)
        
        assert is_worthy is True
    
    def test_calculate_intent_strength(self, classifier_no_llm, mock_signal_tender):
        """Test intent strength calculation."""
        intent = classifier_no_llm.calculate_intent_strength(mock_signal_tender)
        
        assert 0.0 <= intent <= 1.0
        assert intent >= 0.8  # Tender should have high intent
    
    def test_classification_structure(self, classifier_no_llm, mock_signal_tender):
        """Test that classification returns all required fields."""
        classification = classifier_no_llm.classify_event(mock_signal_tender)
        
        assert hasattr(classification, 'is_lead_worthy')
        assert hasattr(classification, 'event_type')
        assert hasattr(classification, 'event_summary')
        assert hasattr(classification, 'location')
        assert hasattr(classification, 'capacity')
        assert hasattr(classification, 'deadline')
        assert hasattr(classification, 'intent_strength')
        assert hasattr(classification, 'reasoning')
    
    def test_intent_strength_range(self, classifier_no_llm, mock_signal_tender):
        """Test that intent strength is within valid range."""
        classification = classifier_no_llm.classify_event(mock_signal_tender)
        
        assert 0.0 <= classification.intent_strength <= 1.0
    
    def test_event_summary_not_empty(self, classifier_no_llm, mock_signal_tender):
        """Test that event summary is always generated."""
        classification = classifier_no_llm.classify_event(mock_signal_tender)
        
        assert classification.event_summary is not None
        assert len(classification.event_summary) > 0
    
    def test_reasoning_provided(self, classifier_no_llm, mock_signal_tender):
        """Test that reasoning is always provided."""
        classification = classifier_no_llm.classify_event(mock_signal_tender)
        
        assert classification.reasoning is not None
        assert len(classification.reasoning) > 0


class TestEventClassifierWithCompanyContext:
    """Test event classification with company context."""
    
    def test_classify_with_company_name(self, classifier_no_llm, mock_signal_tender):
        """Test classification with company name context."""
        classification = classifier_no_llm.classify_event(
            mock_signal_tender,
            company_name="ABC Industries Ltd"
        )
        
        assert classification.is_lead_worthy is True
        assert classification.event_summary is not None


class TestEventClassifierInitialization:
    """Test event classifier initialization."""
    
    def test_initialization_without_api_key(self):
        """Test that classifier initializes without API key."""
        classifier = EventClassifier(openai_api_key=None)
        
        assert classifier.use_llm is False
        assert classifier.client is None
    
    def test_initialization_with_api_key(self):
        """Test that classifier initializes with API key."""
        with patch('app.services.event_classifier.OpenAI') as mock_openai:
            classifier = EventClassifier(openai_api_key="test-key")
            
            assert classifier.use_llm is True
            mock_openai.assert_called_once_with(api_key="test-key")


class TestEventClassifierErrorHandling:
    """Test error handling in event classifier."""
    
    def test_classify_handles_missing_title(self, classifier_no_llm):
        """Test classification works without title."""
        signal = Mock(spec=Signal)
        signal.id = uuid.uuid4()
        signal.title = None
        signal.content = "Tender for fuel supply issued by ABC Industries"
        signal.url = "https://example.com/test"
        signal.ingested_at = datetime.now()
        
        classification = classifier_no_llm.classify_event(signal)
        
        assert classification is not None
        assert classification.event_summary is not None
    
    def test_classify_handles_short_content(self, classifier_no_llm):
        """Test classification works with short content."""
        signal = Mock(spec=Signal)
        signal.id = uuid.uuid4()
        signal.title = "Tender"
        signal.content = "Tender issued"
        signal.url = "https://example.com/test"
        signal.ingested_at = datetime.now()
        
        classification = classifier_no_llm.classify_event(signal)
        
        assert classification is not None


class TestEventClassifierKeywordDetection:
    """Test keyword detection logic."""
    
    def test_detects_procurement_keyword(self, classifier_no_llm):
        """Test detection of procurement keyword."""
        signal = Mock(spec=Signal)
        signal.id = uuid.uuid4()
        signal.title = "Procurement Notice"
        signal.content = "Company issues procurement notice for industrial fuel"
        signal.url = "https://example.com/test"
        signal.ingested_at = datetime.now()
        
        classification = classifier_no_llm.classify_event(signal)
        
        assert classification.is_lead_worthy is True
        assert classification.event_type == 'procurement'
    
    def test_detects_new_project_keyword(self, classifier_no_llm):
        """Test detection of new project keyword."""
        signal = Mock(spec=Signal)
        signal.id = uuid.uuid4()
        signal.title = "New Project Announcement"
        signal.content = "Company announces new project for manufacturing facility"
        signal.url = "https://example.com/test"
        signal.ingested_at = datetime.now()
        
        classification = classifier_no_llm.classify_event(signal)
        
        assert classification.is_lead_worthy is True
        assert classification.event_type == 'new_project'
    
    def test_detects_opinion_piece(self, classifier_no_llm):
        """Test detection of opinion piece (non-lead)."""
        signal = Mock(spec=Signal)
        signal.id = uuid.uuid4()
        signal.title = "Opinion: Future of Energy"
        signal.content = "This is an editorial opinion about the energy sector"
        signal.url = "https://example.com/test"
        signal.ingested_at = datetime.now()
        
        classification = classifier_no_llm.classify_event(signal)
        
        assert classification.is_lead_worthy is False
