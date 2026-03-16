"""Event Classifier for analyzing signals and determining lead-worthiness."""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import google.generativeai as genai
import logging

from app.utils.config import settings
from app.models.signal import Signal
from app.models.event import Event

logger = logging.getLogger(__name__)


class EventClassification(BaseModel):
    """Structured output for event classification."""
    
    is_lead_worthy: bool = Field(
        description="Whether this signal represents a potential business opportunity"
    )
    event_type: Optional[str] = Field(
        default=None,
        description="Type of business event (expansion, tender, procurement, new_project, etc.)"
    )
    event_summary: str = Field(
        description="Brief summary of the business event"
    )
    location: Optional[str] = Field(
        default=None,
        description="Location where the event is taking place"
    )
    capacity: Optional[str] = Field(
        default=None,
        description="Capacity, scale, or size information (e.g., '500 MW', '10,000 sq ft')"
    )
    deadline: Optional[str] = Field(
        default=None,
        description="Deadline or timeline in ISO format (YYYY-MM-DD) if mentioned"
    )
    intent_strength: float = Field(
        ge=0.0,
        le=1.0,
        description="Intent strength score: 1.0 for explicit tenders, 0.7 for expansion plans, 0.3 for vague mentions"
    )
    reasoning: str = Field(
        description="Brief explanation of why this is or isn't lead-worthy"
    )


class EventClassifier:
    """Classifies business events and determines lead-worthiness."""
    
    # Lead-worthy indicators
    LEAD_WORTHY_KEYWORDS = [
        'tender', 'bid', 'procurement', 'expansion', 'new project',
        'construction', 'installation', 'capacity addition', 'modernization',
        'upgrade', 'new plant', 'new facility', 'investment', 'capex',
        'commissioning', 'setting up', 'establishing', 'building'
    ]
    
    # Non-lead indicators
    NON_LEAD_KEYWORDS = [
        'opinion', 'editorial', 'analysis', 'commentary', 'historical',
        'retrospective', 'anniversary', 'celebration', 'award ceremony',
        'conference', 'seminar', 'workshop', 'training'
    ]
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize the event classifier.
        
        Args:
            gemini_api_key: Gemini API key (uses settings if not provided)
        """
        self.api_key = gemini_api_key or settings.gemini_api_key
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.use_llm = True
            logger.info("Event classifier initialized with Gemini LLM")
        else:
            self.model = None
            self.use_llm = False
            logger.warning("No Gemini API key provided, using rule-based classification only")
    
    def classify_event(
        self,
        signal: Signal,
        company_name: Optional[str] = None
    ) -> EventClassification:
        """
        Classify a signal to determine if it represents a business opportunity.
        
        Args:
            signal: Signal object to classify
            company_name: Optional company name for context
        
        Returns:
            EventClassification with lead-worthiness determination
        
        Raises:
            RuntimeError: If classification fails
        """
        try:
            if self.use_llm:
                return self._classify_with_llm(signal, company_name)
            else:
                return self._classify_with_rules(signal, company_name)
        
        except Exception as e:
            logger.error(f"Failed to classify signal {signal.id}: {e}")
            raise RuntimeError(f"Event classification failed: {e}")
    
    def _classify_with_llm(
        self,
        signal: Signal,
        company_name: Optional[str] = None
    ) -> EventClassification:
        """
        Classify event using Gemini LLM with structured output.
        
        Args:
            signal: Signal to classify
            company_name: Optional company name for context
        
        Returns:
            EventClassification object
        """
        # Prepare context
        text = signal.content
        if signal.title:
            text = f"{signal.title}\n\n{text}"
        
        if company_name:
            text = f"Company: {company_name}\n\n{text}"
        
        # Create prompt
        prompt = f"""Analyze the following business signal and determine if it represents a potential business opportunity for HPCL (a fuel and petroleum products company).

Signal:
{text[:2000]}

Classify this signal based on the following criteria:

1. **Lead-worthy indicators**: tenders, bids, procurement announcements, expansion plans, new projects, construction activities, capacity additions, modernization, installations
2. **Non-lead indicators**: general news, opinion pieces, historical articles, conferences, awards, training events

Return a JSON object with:
- is_lead_worthy: true if this represents a business opportunity, false otherwise
- event_type: category like 'expansion', 'tender', 'procurement', 'new_project', etc.
- event_summary: brief 1-2 sentence summary of the business event
- location: where the event is happening (if mentioned)
- capacity: scale or size information (if mentioned)
- deadline: deadline date in YYYY-MM-DD format (if mentioned)
- intent_strength: score from 0.0 to 1.0 where:
  * 1.0 = explicit tender or bid with clear requirements
  * 0.7-0.9 = announced expansion or project with details
  * 0.4-0.6 = planned or proposed project
  * 0.1-0.3 = vague mention or consideration
- reasoning: brief explanation of your classification

JSON format:
{{
  "is_lead_worthy": true/false,
  "event_type": "type",
  "event_summary": "summary",
  "location": "location or null",
  "capacity": "capacity or null",
  "deadline": "YYYY-MM-DD or null",
  "intent_strength": 0.0-1.0,
  "reasoning": "explanation"
}}"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )
            
            # Parse JSON response
            import json
            result = json.loads(response.text)
            
            classification = EventClassification(**result)
            
            logger.info(
                f"LLM classified signal {signal.id}: "
                f"lead_worthy={classification.is_lead_worthy}, "
                f"intent={classification.intent_strength:.2f}"
            )
            
            return classification
        
        except Exception as e:
            logger.error(f"LLM classification failed for signal {signal.id}: {e}")
            # Fall back to rule-based classification
            logger.info("Falling back to rule-based classification")
            return self._classify_with_rules(signal, company_name)
    
    def _classify_with_rules(
        self,
        signal: Signal,
        company_name: Optional[str] = None
    ) -> EventClassification:
        """
        Classify event using rule-based heuristics.
        
        Args:
            signal: Signal to classify
            company_name: Optional company name for context
        
        Returns:
            EventClassification object
        """
        text = signal.content.lower()
        if signal.title:
            text = f"{signal.title.lower()} {text}"
        
        # Check for lead-worthy keywords
        lead_worthy_score = sum(
            1 for keyword in self.LEAD_WORTHY_KEYWORDS
            if keyword in text
        )
        
        # Check for non-lead keywords
        non_lead_score = sum(
            1 for keyword in self.NON_LEAD_KEYWORDS
            if keyword in text
        )
        
        # Determine lead-worthiness
        is_lead_worthy = lead_worthy_score > non_lead_score
        
        # Calculate intent strength based on keyword matches
        if 'tender' in text or 'bid' in text:
            intent_strength = 0.9
        elif 'expansion' in text or 'new project' in text:
            intent_strength = 0.7
        elif 'planned' in text or 'proposed' in text:
            intent_strength = 0.5
        elif 'considering' in text or 'may' in text:
            intent_strength = 0.3
        else:
            intent_strength = 0.6 if is_lead_worthy else 0.2
        
        # Determine event type
        event_type = None
        if 'tender' in text or 'bid' in text:
            event_type = 'tender'
        elif 'expansion' in text:
            event_type = 'expansion'
        elif 'procurement' in text:
            event_type = 'procurement'
        elif 'new project' in text or 'construction' in text:
            event_type = 'new_project'
        
        # Create summary
        if signal.title:
            event_summary = signal.title[:200]
        else:
            # Extract first sentence or first 200 chars
            sentences = signal.content.split('.')
            event_summary = sentences[0][:200] if sentences else signal.content[:200]
        
        # Reasoning
        if is_lead_worthy:
            reasoning = f"Contains {lead_worthy_score} lead-worthy indicators"
        else:
            reasoning = f"Contains {non_lead_score} non-lead indicators or insufficient business opportunity signals"
        
        classification = EventClassification(
            is_lead_worthy=is_lead_worthy,
            event_type=event_type,
            event_summary=event_summary,
            location=None,  # Rule-based can't extract location reliably
            capacity=None,  # Rule-based can't extract capacity reliably
            deadline=None,  # Rule-based can't extract deadline reliably
            intent_strength=intent_strength,
            reasoning=reasoning
        )
        
        logger.info(
            f"Rule-based classified signal {signal.id}: "
            f"lead_worthy={classification.is_lead_worthy}, "
            f"intent={classification.intent_strength:.2f}"
        )
        
        return classification
    
    def is_lead_worthy(self, signal: Signal) -> bool:
        """
        Quick check if a signal is lead-worthy.
        
        Args:
            signal: Signal to check
        
        Returns:
            True if lead-worthy, False otherwise
        """
        try:
            classification = self.classify_event(signal)
            return classification.is_lead_worthy
        except Exception as e:
            logger.error(f"Failed to determine lead-worthiness for signal {signal.id}: {e}")
            return False
    
    def calculate_intent_strength(self, signal: Signal) -> float:
        """
        Calculate intent strength for a signal.
        
        Args:
            signal: Signal to analyze
        
        Returns:
            Intent strength score (0.0 to 1.0)
        """
        try:
            classification = self.classify_event(signal)
            return classification.intent_strength
        except Exception as e:
            logger.error(f"Failed to calculate intent strength for signal {signal.id}: {e}")
            return 0.0
