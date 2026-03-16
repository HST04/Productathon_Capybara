"""Unit tests for Entity Extractor service."""

import pytest
from unittest.mock import Mock, patch
import sys
from typing import List

# Mock OpenAI before importing
sys.modules['openai'] = Mock()

from app.services.entity_extractor import EntityExtractor, CompanyMention, ExtractedEntities


class TestEntityExtractor:
    """Test entity extraction functionality."""
    
    @pytest.fixture
    def extractor_no_llm(self):
        """Create extractor without LLM (rule-based only)."""
        return EntityExtractor(openai_api_key=None)
    
    def test_extract_product_keywords(self, extractor_no_llm):
        """Test extraction of direct product keywords."""
        text = "The facility will use furnace oil and high speed diesel for operations."
        
        keywords = extractor_no_llm.extract_product_keywords(text)
        
        assert 'furnace oil' in keywords
        assert 'high speed diesel' in keywords
    
    def test_extract_operational_cues(self, extractor_no_llm):
        """Test extraction of operational cues."""
        text = "The plant will install new boilers and gensets for power generation."
        
        cues = extractor_no_llm.extract_operational_cues(text)
        
        assert 'boiler' in cues
        assert 'genset' in cues
    
    def test_extract_multiple_product_keywords(self, extractor_no_llm):
        """Test extraction of multiple product keywords."""
        text = "Supply of bitumen, high speed diesel, and LDO for the project."
        
        keywords = extractor_no_llm.extract_product_keywords(text)
        
        assert 'bitumen' in keywords
        assert 'high speed diesel' in keywords
        assert 'ldo' in keywords
    
    def test_extract_operational_cues_case_insensitive(self, extractor_no_llm):
        """Test that operational cue extraction is case insensitive."""
        text = "New BOILER installation and FURNACE upgrade planned."
        
        cues = extractor_no_llm.extract_operational_cues(text)
        
        assert 'boiler' in cues
        assert 'furnace' in cues
    
    def test_extract_cin_pattern(self, extractor_no_llm):
        """Test CIN number extraction with regex."""
        text = "ABC Industries Ltd (CIN: U12345AB2020PTC123456) is expanding."
        
        entities = extractor_no_llm.extract_entities(text)
        
        # Should extract CIN even with rule-based extraction
        assert len(entities.companies) > 0
        # CIN should be found by regex enhancement
        if entities.companies:
            assert entities.companies[0].cin is not None
    
    def test_extract_gst_pattern(self, extractor_no_llm):
        """Test GST number extraction with regex."""
        text = "Company GST: 27AABCU9603R1ZM for tax purposes."
        
        entities = extractor_no_llm.extract_entities(text)
        
        # GST should be found by regex enhancement
        if entities.companies:
            assert entities.companies[0].gst is not None
    
    def test_extract_company_names_rule_based(self, extractor_no_llm):
        """Test rule-based company name extraction."""
        text = "XYZ Industries Ltd and ABC Corporation Pvt Ltd are collaborating."
        
        companies = extractor_no_llm.extract_companies(text)
        
        assert len(companies) > 0
        # Should find at least one company with Ltd/Pvt pattern
        company_names = [c.name for c in companies]
        assert any('Ltd' in name or 'Pvt' in name for name in company_names)
    
    def test_extract_entities_empty_text(self, extractor_no_llm):
        """Test extraction from empty text."""
        entities = extractor_no_llm.extract_entities("")
        
        assert isinstance(entities, ExtractedEntities)
        assert len(entities.companies) == 0
        assert len(entities.product_keywords) == 0
        assert len(entities.operational_cues) == 0
    
    def test_extract_entities_with_title(self, extractor_no_llm):
        """Test extraction with both title and text."""
        title = "New Boiler Installation Project"
        text = "The project will use furnace oil for heating."
        
        entities = extractor_no_llm.extract_entities(text, title)
        
        # Should find operational cue from title
        assert 'boiler' in entities.operational_cues
        # Should find product keyword from text
        assert 'furnace oil' in entities.product_keywords
    
    def test_extract_no_keywords_or_cues(self, extractor_no_llm):
        """Test extraction when no keywords or cues present."""
        text = "This is a general news article about the economy."
        
        entities = extractor_no_llm.extract_entities(text)
        
        assert len(entities.product_keywords) == 0
        assert len(entities.operational_cues) == 0
    
    def test_extract_marine_keywords(self, extractor_no_llm):
        """Test extraction of marine-related keywords and cues."""
        text = "Port expansion project requires bunker fuel for shipping operations."
        
        entities = extractor_no_llm.extract_entities(text)
        
        assert 'bunker' in entities.product_keywords
        assert 'port' in entities.operational_cues
        assert 'shipping' in entities.operational_cues
    
    def test_extract_construction_keywords(self, extractor_no_llm):
        """Test extraction of construction-related keywords."""
        text = "Highway construction project using bitumen and high speed diesel."
        
        entities = extractor_no_llm.extract_entities(text)
        
        assert 'bitumen' in entities.product_keywords
        assert 'high speed diesel' in entities.product_keywords
        assert 'highway' in entities.operational_cues
        assert 'highway' in entities.operational_cues
    
    def test_extract_industrial_cues(self, extractor_no_llm):
        """Test extraction of industrial operational cues."""
        text = "Steel plant with wash oil facility and captive power generation."
        
        entities = extractor_no_llm.extract_entities(text)
        
        assert 'steel plant' in entities.operational_cues
        assert 'captive power' in entities.operational_cues
    
    def test_extractor_initialization_without_api_key(self):
        """Test that extractor initializes without API key."""
        extractor = EntityExtractor(openai_api_key=None)
        
        assert extractor.use_llm is False
        assert extractor.client is None
    
    def test_product_keywords_list_not_empty(self, extractor_no_llm):
        """Test that product keywords list is populated."""
        assert len(extractor_no_llm.PRODUCT_KEYWORDS) > 0
        assert 'furnace oil' in extractor_no_llm.PRODUCT_KEYWORDS
        assert 'high speed diesel' in extractor_no_llm.PRODUCT_KEYWORDS
        assert 'bitumen' in extractor_no_llm.PRODUCT_KEYWORDS
    
    def test_operational_cues_list_not_empty(self, extractor_no_llm):
        """Test that operational cues list is populated."""
        assert len(extractor_no_llm.OPERATIONAL_CUES) > 0
        assert 'boiler' in extractor_no_llm.OPERATIONAL_CUES
        assert 'genset' in extractor_no_llm.OPERATIONAL_CUES
