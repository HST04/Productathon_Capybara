"""Entity Extractor service for extracting structured information from signals."""

import logging
import re
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import google.generativeai as genai

from app.utils.config import settings

logger = logging.getLogger(__name__)


# Pydantic models for structured extraction
class CompanyMention(BaseModel):
    """Extracted company information."""
    name: str = Field(description="Company name as mentioned in text")
    cin: Optional[str] = Field(None, description="Corporate Identification Number (CIN) if mentioned")
    gst: Optional[str] = Field(None, description="GST number if mentioned")
    website: Optional[str] = Field(None, description="Company website URL if mentioned")
    industry: Optional[str] = Field(None, description="Industry or sector")
    address: Optional[str] = Field(None, description="Company address if mentioned")
    locations: List[str] = Field(default_factory=list, description="Plant or office locations mentioned")


class Location(BaseModel):
    """Extracted location information."""
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State or province")
    country: Optional[str] = Field(None, description="Country name")
    full_location: str = Field(description="Complete location string as mentioned")


class DateMention(BaseModel):
    """Extracted date or deadline information."""
    date_string: str = Field(description="Date as mentioned in text")
    date_type: str = Field(description="Type of date: deadline, start_date, completion_date, announcement_date")
    parsed_date: Optional[str] = Field(None, description="ISO format date if parseable (YYYY-MM-DD)")


class Capacity(BaseModel):
    """Extracted capacity or scale information."""
    value: str = Field(description="Capacity value with units")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    capacity_type: str = Field(description="Type: production_capacity, investment_amount, project_size, employee_count")


class ExtractedEntities(BaseModel):
    """Complete entity extraction result."""
    companies: List[CompanyMention] = Field(default_factory=list, description="All companies mentioned")
    location: Optional[Location] = Field(None, description="Primary location mentioned")
    dates: List[DateMention] = Field(default_factory=list, description="All dates and deadlines")
    capacity: Optional[Capacity] = Field(None, description="Capacity or scale information")
    product_keywords: List[str] = Field(default_factory=list, description="Direct product keywords found")
    operational_cues: List[str] = Field(default_factory=list, description="Operational cues indicating product needs")


class EntityExtractor:
    """
    Service for extracting structured entities from signal text using LLM.
    
    Extracts:
    - Company names with CIN/GST identifiers
    - Locations (city, state, country)
    - Dates and deadlines
    - Capacity and scale information
    - Product keywords (FO, LDO, HSD, bitumen, etc.)
    - Operational cues (boiler, furnace, genset, etc.)
    """
    
    # Product keywords to look for
    PRODUCT_KEYWORDS = [
        'furnace oil', 'fo', 'light diesel oil', 'ldo', 'high speed diesel', 'hsd',
        'bitumen', 'bunker', 'bunker fuel', 'marine diesel', 'solvent', 'hexane',
        'jute batching oil', 'wash oil', 'lshs', 'low sulphur heavy stock'
    ]
    
    # Operational cues that indicate product needs
    OPERATIONAL_CUES = [
        'boiler', 'furnace', 'genset', 'generator', 'captive power', 'power plant',
        'shipping', 'port', 'marine', 'vessel', 'road project', 'highway', 'township',
        'housing project', 'warehouse', 'logistics', 'jute mill', 'steel plant',
        'steel wash', 'solvent extraction', 'refinery'
    ]
    
    # Regex patterns for identifiers
    CIN_PATTERN = re.compile(r'\b[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b', re.IGNORECASE)
    GST_PATTERN = re.compile(r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b', re.IGNORECASE)
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize the entity extractor.
        
        Args:
            gemini_api_key: Gemini API key (uses settings if not provided)
        """
        self.api_key = gemini_api_key or settings.gemini_api_key
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.use_llm = True
            logger.info("Entity extractor initialized with Gemini LLM")
        else:
            self.model = None
            self.use_llm = False
            logger.warning("No Gemini API key provided, using rule-based extraction only")
    
    def extract_entities(self, text: str, title: Optional[str] = None) -> ExtractedEntities:
        """
        Extract all entities from signal text.
        
        Args:
            text: Signal content text
            title: Optional signal title
        
        Returns:
            ExtractedEntities object with all extracted information
        """
        try:
            # Combine title and text for better context
            full_text = f"{title}\n\n{text}" if title else text
            
            if self.use_llm:
                # Use LLM for comprehensive extraction
                entities = self._extract_with_llm(full_text)
            else:
                # Fall back to rule-based extraction
                entities = self._extract_with_rules(full_text)
            
            # Always enhance with regex-based identifier extraction
            entities = self._enhance_with_regex(entities, full_text)
            
            # Extract product keywords and operational cues
            entities.product_keywords = self.extract_product_keywords(full_text)
            entities.operational_cues = self.extract_operational_cues(full_text)
            
            logger.info(
                f"Extracted entities: {len(entities.companies)} companies, "
                f"{len(entities.product_keywords)} product keywords, "
                f"{len(entities.operational_cues)} operational cues"
            )
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}", exc_info=True)
            # Return empty entities on error
            return ExtractedEntities()
    
    def _extract_with_llm(self, text: str) -> ExtractedEntities:
        """
        Extract entities using Gemini LLM with structured output.
        
        Args:
            text: Text to extract from
        
        Returns:
            ExtractedEntities object
        """
        try:
            prompt = f"""You are an expert at extracting business information from text.
Extract all relevant entities including:
- Company names with any identifiers (CIN, GST, website, address, locations)
- Location information (city, state, country)
- Dates and deadlines
- Capacity, scale, or investment amounts
- Product keywords related to petroleum products
- Operational cues indicating industrial equipment or processes

Extract structured business entities from this text:

{text}

Focus on:
1. All company names mentioned
2. Geographic locations
3. Dates, deadlines, or timelines
4. Capacity, scale, investment amounts
5. Product keywords (fuel oil, diesel, bitumen, etc.)
6. Operational cues (boilers, furnaces, generators, etc.)

Return the result as a JSON object with this structure:
{{
  "companies": [
    {{
      "name": "company name",
      "cin": "CIN if found",
      "gst": "GST if found",
      "website": "website if found",
      "industry": "industry if found",
      "address": "address if found",
      "locations": ["location1", "location2"]
    }}
  ],
  "location": {{
    "city": "city name",
    "state": "state name",
    "country": "country name",
    "full_location": "complete location string"
  }},
  "dates": [
    {{
      "date_string": "date as mentioned",
      "date_type": "deadline/start_date/completion_date/announcement_date",
      "parsed_date": "YYYY-MM-DD format if parseable"
    }}
  ],
  "capacity": {{
    "value": "capacity value with units",
    "unit": "unit of measurement",
    "capacity_type": "production_capacity/investment_amount/project_size/employee_count"
  }},
  "product_keywords": ["keyword1", "keyword2"],
  "operational_cues": ["cue1", "cue2"]
}}

If information is not present, use null or empty arrays."""

            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            
            # Parse JSON response into ExtractedEntities
            import json
            result = json.loads(response.text)
            
            # Convert to ExtractedEntities object
            entities = ExtractedEntities(
                companies=[CompanyMention(**c) for c in result.get('companies', [])],
                location=Location(**result['location']) if result.get('location') else None,
                dates=[DateMention(**d) for d in result.get('dates', [])],
                capacity=Capacity(**result['capacity']) if result.get('capacity') else None,
                product_keywords=result.get('product_keywords', []),
                operational_cues=result.get('operational_cues', [])
            )
            
            return entities
                
        except Exception as e:
            logger.error(f"Error in LLM extraction: {e}", exc_info=True)
            # Fall back to rule-based extraction
            return self._extract_with_rules(text)
    
    def _extract_with_rules(self, text: str) -> ExtractedEntities:
        """
        Extract entities using rule-based methods (fallback).
        
        Args:
            text: Text to extract from
        
        Returns:
            ExtractedEntities object
        """
        entities = ExtractedEntities()
        
        # Basic company name extraction (look for "Ltd", "Limited", "Pvt", etc.)
        company_pattern = re.compile(
            r'\b([A-Z][A-Za-z\s&]+(?:Ltd|Limited|Pvt|Private|Corporation|Corp|Inc|Industries|Company|Co)\b\.?)',
            re.IGNORECASE
        )
        company_matches = company_pattern.findall(text)
        
        for match in company_matches[:5]:  # Limit to first 5 to avoid noise
            entities.companies.append(CompanyMention(name=match.strip()))
        
        logger.info(f"Rule-based extraction found {len(entities.companies)} companies")
        
        return entities
    
    def _enhance_with_regex(self, entities: ExtractedEntities, text: str) -> ExtractedEntities:
        """
        Enhance extracted entities with regex-based identifier extraction.
        
        Args:
            entities: Existing extracted entities
            text: Original text
        
        Returns:
            Enhanced entities
        """
        # Extract CIN numbers
        cin_matches = self.CIN_PATTERN.findall(text)
        
        # Extract GST numbers
        gst_matches = self.GST_PATTERN.findall(text)
        
        # If we found identifiers but no companies, create placeholder companies
        if (cin_matches or gst_matches) and not entities.companies:
            entities.companies.append(CompanyMention(
                name="Company (identifier found)",
                cin=cin_matches[0] if cin_matches else None,
                gst=gst_matches[0] if gst_matches else None
            ))
        # If we have companies, add identifiers to the first company
        elif entities.companies:
            if cin_matches and not entities.companies[0].cin:
                entities.companies[0].cin = cin_matches[0]
            if gst_matches and not entities.companies[0].gst:
                entities.companies[0].gst = gst_matches[0]
        
        return entities
    
    def extract_companies(self, text: str) -> List[CompanyMention]:
        """
        Extract company mentions from text.
        
        Args:
            text: Text to extract from
        
        Returns:
            List of CompanyMention objects
        """
        entities = self.extract_entities(text)
        return entities.companies
    
    def extract_location(self, text: str) -> Optional[Location]:
        """
        Extract primary location from text.
        
        Args:
            text: Text to extract from
        
        Returns:
            Location object or None
        """
        entities = self.extract_entities(text)
        return entities.location
    
    def extract_dates(self, text: str) -> List[DateMention]:
        """
        Extract dates and deadlines from text.
        
        Args:
            text: Text to extract from
        
        Returns:
            List of DateMention objects
        """
        entities = self.extract_entities(text)
        return entities.dates
    
    def extract_capacity(self, text: str) -> Optional[Capacity]:
        """
        Extract capacity or scale information from text.
        
        Args:
            text: Text to extract from
        
        Returns:
            Capacity object or None
        """
        entities = self.extract_entities(text)
        return entities.capacity
    
    def extract_product_keywords(self, text: str) -> List[str]:
        """
        Extract direct product keywords from text.
        
        Args:
            text: Text to search
        
        Returns:
            List of found product keywords
        """
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.PRODUCT_KEYWORDS:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def extract_operational_cues(self, text: str) -> List[str]:
        """
        Extract operational cues indicating product needs.
        
        Args:
            text: Text to search
        
        Returns:
            List of found operational cues
        """
        text_lower = text.lower()
        found_cues = []
        
        for cue in self.OPERATIONAL_CUES:
            if cue.lower() in text_lower:
                found_cues.append(cue)
        
        return found_cues
