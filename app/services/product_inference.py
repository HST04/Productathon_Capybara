"""Product Inference Engine for mapping business events to HPCL products."""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProductMatch:
    """Represents a product match with confidence and reasoning."""
    product_name: str
    confidence: float  # 0.0 to 1.0
    reason_code: str  # 'keyword_match', 'operational_cue', 'inference'
    reasoning: str
    keywords_found: List[str]
    cues_found: List[str]
    uncertainty_flag: bool = False  # True when confidence < 60%


class ProductInferenceEngine:
    """
    Engine for inferring HPCL product recommendations from business events.
    
    Maps direct product keywords and operational cues to specific HPCL products
    with confidence scoring and reasoning.
    """
    
    # HPCL Product Catalog
    PRODUCTS = {
        'FO': 'Furnace Oil',
        'LDO': 'Light Diesel Oil',
        'HSD': 'High Speed Diesel',
        'LSHS': 'Low Sulphur Heavy Stock',
        'BITUMEN': 'Bitumen',
        'BUNKER': 'Bunker Fuel',
        'MARINE_DIESEL': 'Marine Diesel Oil',
        'HEXANE': 'Hexane',
        'SOLVENT': 'Industrial Solvents',
        'JUTE_OIL': 'Jute Batching Oil',
        'WASH_OIL': 'Steel Wash Oil',
        'LPG': 'Liquefied Petroleum Gas'
    }
    
    # Direct keyword to product mappings
    # Format: keyword -> (product_code, confidence)
    KEYWORD_MAPPINGS = {
        # Furnace Oil
        'furnace oil': ('FO', 0.95),
        'fo': ('FO', 0.90),
        'fuel oil': ('FO', 0.85),
        
        # Light Diesel Oil
        'light diesel oil': ('LDO', 0.95),
        'ldo': ('LDO', 0.90),
        'light diesel': ('LDO', 0.85),
        
        # High Speed Diesel
        'high speed diesel': ('HSD', 0.95),
        'hsd': ('HSD', 0.90),
        'diesel': ('HSD', 0.75),
        'automotive diesel': ('HSD', 0.90),
        
        # Low Sulphur Heavy Stock
        'low sulphur heavy stock': ('LSHS', 0.95),
        'lshs': ('LSHS', 0.90),
        'low sulfur heavy stock': ('LSHS', 0.95),
        
        # Bitumen
        'bitumen': ('BITUMEN', 0.95),
        'asphalt': ('BITUMEN', 0.90),
        'road tar': ('BITUMEN', 0.85),
        
        # Bunker Fuel
        'bunker': ('BUNKER', 0.90),
        'bunker fuel': ('BUNKER', 0.95),
        'marine fuel': ('BUNKER', 0.85),
        'ship fuel': ('BUNKER', 0.85),
        
        # Marine Diesel
        'marine diesel': ('MARINE_DIESEL', 0.95),
        'marine gas oil': ('MARINE_DIESEL', 0.90),
        'mgo': ('MARINE_DIESEL', 0.85),
        
        # Hexane
        'hexane': ('HEXANE', 0.95),
        'n-hexane': ('HEXANE', 0.95),
        
        # Solvents
        'solvent': ('SOLVENT', 0.85),
        'industrial solvent': ('SOLVENT', 0.90),
        
        # Jute Batching Oil
        'jute batching oil': ('JUTE_OIL', 0.95),
        'jute oil': ('JUTE_OIL', 0.90),
        'batching oil': ('JUTE_OIL', 0.85),
        
        # Wash Oil
        'wash oil': ('WASH_OIL', 0.95),
        'steel wash oil': ('WASH_OIL', 0.95),
        
        # LPG
        'lpg': ('LPG', 0.90),
        'liquefied petroleum gas': ('LPG', 0.95),
        'cooking gas': ('LPG', 0.80)
    }
    
    # Operational cue to product inference rules
    # Format: cue -> [(product_code, confidence, reasoning)]
    OPERATIONAL_CUE_RULES = {
        # Heating and Power Generation
        'boiler': [
            ('FO', 0.85, 'Boilers commonly use Furnace Oil for industrial heating'),
            ('LDO', 0.75, 'Light Diesel Oil is an alternative fuel for boilers')
        ],
        'furnace': [
            ('FO', 0.85, 'Furnaces typically require Furnace Oil for high-temperature operations'),
            ('LDO', 0.70, 'Light Diesel Oil can be used in smaller furnaces')
        ],
        'genset': [
            ('HSD', 0.90, 'Diesel generators (gensets) run on High Speed Diesel'),
            ('LDO', 0.70, 'Light Diesel Oil is an alternative for some gensets')
        ],
        'generator': [
            ('HSD', 0.85, 'Generators typically use High Speed Diesel'),
            ('LDO', 0.65, 'Light Diesel Oil can power some generators')
        ],
        'captive power': [
            ('HSD', 0.85, 'Captive power plants often use High Speed Diesel'),
            ('FO', 0.80, 'Furnace Oil is used in larger captive power installations')
        ],
        'power plant': [
            ('FO', 0.80, 'Power plants may use Furnace Oil for generation'),
            ('HSD', 0.75, 'Diesel-based power plants use High Speed Diesel')
        ],
        
        # Marine and Shipping
        'shipping': [
            ('BUNKER', 0.85, 'Shipping operations require Bunker Fuel for vessels'),
            ('MARINE_DIESEL', 0.80, 'Marine Diesel Oil is used for ship engines')
        ],
        'port': [
            ('BUNKER', 0.80, 'Port operations involve Bunker Fuel for ships'),
            ('HSD', 0.70, 'High Speed Diesel for port equipment and vehicles')
        ],
        'marine': [
            ('BUNKER', 0.85, 'Marine operations use Bunker Fuel'),
            ('MARINE_DIESEL', 0.85, 'Marine Diesel Oil for ship propulsion')
        ],
        'vessel': [
            ('BUNKER', 0.85, 'Vessels require Bunker Fuel for operation'),
            ('MARINE_DIESEL', 0.80, 'Marine Diesel Oil for vessel engines')
        ],
        'ship': [
            ('BUNKER', 0.85, 'Ships use Bunker Fuel for propulsion'),
            ('MARINE_DIESEL', 0.80, 'Marine Diesel Oil for ship engines')
        ],
        
        # Construction and Infrastructure
        'road project': [
            ('BITUMEN', 0.90, 'Road construction requires Bitumen for asphalt'),
            ('HSD', 0.80, 'High Speed Diesel for construction equipment')
        ],
        'highway': [
            ('BITUMEN', 0.90, 'Highway construction uses Bitumen for road surfacing'),
            ('HSD', 0.75, 'High Speed Diesel for highway construction machinery')
        ],
        'township': [
            ('BITUMEN', 0.75, 'Township development includes road construction with Bitumen'),
            ('HSD', 0.70, 'High Speed Diesel for construction vehicles'),
            ('LPG', 0.65, 'LPG for residential cooking in townships')
        ],
        'housing project': [
            ('BITUMEN', 0.70, 'Housing projects include road infrastructure with Bitumen'),
            ('HSD', 0.65, 'High Speed Diesel for construction equipment'),
            ('LPG', 0.70, 'LPG for residential cooking')
        ],
        
        # Logistics and Transportation
        'warehouse': [
            ('HSD', 0.85, 'Warehouse operations require High Speed Diesel for fleet vehicles'),
            ('LDO', 0.60, 'Light Diesel Oil for backup generators')
        ],
        'logistics': [
            ('HSD', 0.90, 'Logistics operations need High Speed Diesel for transportation fleet'),
        ],
        'fleet': [
            ('HSD', 0.90, 'Fleet operations require High Speed Diesel for vehicles'),
        ],
        'transport': [
            ('HSD', 0.85, 'Transportation requires High Speed Diesel for vehicles'),
        ],
        
        # Industrial Processes
        'jute mill': [
            ('JUTE_OIL', 0.95, 'Jute mills require Jute Batching Oil for processing'),
            ('HSD', 0.70, 'High Speed Diesel for mill equipment')
        ],
        'steel plant': [
            ('WASH_OIL', 0.90, 'Steel plants use Wash Oil for steel processing'),
            ('FO', 0.80, 'Furnace Oil for steel plant heating operations')
        ],
        'steel wash': [
            ('WASH_OIL', 0.95, 'Steel washing operations require specialized Wash Oil'),
        ],
        'solvent extraction': [
            ('HEXANE', 0.95, 'Solvent extraction processes use Hexane'),
            ('SOLVENT', 0.85, 'Industrial solvents for extraction')
        ],
        'refinery': [
            ('FO', 0.75, 'Refineries may use Furnace Oil for heating'),
            ('HSD', 0.70, 'High Speed Diesel for refinery operations')
        ],
        
        # Manufacturing
        'manufacturing': [
            ('HSD', 0.70, 'Manufacturing facilities need High Speed Diesel for equipment'),
            ('FO', 0.65, 'Furnace Oil for industrial heating in manufacturing')
        ],
        'factory': [
            ('HSD', 0.70, 'Factories require High Speed Diesel for operations'),
            ('FO', 0.65, 'Furnace Oil for factory heating systems')
        ],
        'plant': [
            ('HSD', 0.65, 'Industrial plants need High Speed Diesel'),
            ('FO', 0.60, 'Furnace Oil for plant heating')
        ]
    }
    
    def __init__(self):
        """Initialize the product inference engine."""
        logger.info("Product inference engine initialized")
    
    def infer_products(
        self,
        text: str,
        product_keywords: List[str],
        operational_cues: List[str],
        top_n: int = 3
    ) -> List[ProductMatch]:
        """
        Infer product recommendations from text, keywords, and operational cues.
        
        Args:
            text: Event text for context
            product_keywords: Direct product keywords found
            operational_cues: Operational cues found
            top_n: Number of top recommendations to return
        
        Returns:
            List of ProductMatch objects, ranked by confidence
        """
        matches: Dict[str, ProductMatch] = {}
        
        # Process direct keyword matches
        for keyword in product_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in self.KEYWORD_MAPPINGS:
                product_code, confidence = self.KEYWORD_MAPPINGS[keyword_lower]
                
                if product_code not in matches:
                    matches[product_code] = ProductMatch(
                        product_name=self.PRODUCTS[product_code],
                        confidence=confidence,
                        reason_code='keyword_match',
                        reasoning=f'Direct mention of "{keyword}" indicates need for {self.PRODUCTS[product_code]}',
                        keywords_found=[keyword],
                        cues_found=[],
                        uncertainty_flag=False
                    )
                else:
                    # Update confidence if higher
                    if confidence > matches[product_code].confidence:
                        matches[product_code].confidence = confidence
                    matches[product_code].keywords_found.append(keyword)
        
        # Process operational cue inferences
        for cue in operational_cues:
            cue_lower = cue.lower()
            if cue_lower in self.OPERATIONAL_CUE_RULES:
                rules = self.OPERATIONAL_CUE_RULES[cue_lower]
                
                for product_code, confidence, reasoning in rules:
                    if product_code not in matches:
                        matches[product_code] = ProductMatch(
                            product_name=self.PRODUCTS[product_code],
                            confidence=confidence,
                            reason_code='operational_cue',
                            reasoning=reasoning,
                            keywords_found=[],
                            cues_found=[cue],
                            uncertainty_flag=False
                        )
                    else:
                        # Boost confidence if cue supports existing match
                        boost = 0.05
                        matches[product_code].confidence = min(
                            1.0,
                            matches[product_code].confidence + boost
                        )
                        matches[product_code].cues_found.append(cue)
                        
                        # Update reasoning if this is a cue-based match
                        if matches[product_code].reason_code == 'operational_cue':
                            matches[product_code].reasoning += f'; {reasoning}'
        
        # Sort by confidence and return top N
        sorted_matches = sorted(
            matches.values(),
            key=lambda m: m.confidence,
            reverse=True
        )
        
        top_matches = sorted_matches[:top_n]
        
        # Flag uncertainty for low confidence matches (< 60%)
        for match in top_matches:
            if match.confidence < 0.60:
                match.uncertainty_flag = True
        
        logger.info(
            f"Inferred {len(top_matches)} product recommendations "
            f"from {len(product_keywords)} keywords and {len(operational_cues)} cues"
        )
        
        return top_matches
    
    def apply_keyword_rules(self, text: str) -> List[ProductMatch]:
        """
        Apply keyword matching rules to text.
        
        Args:
            text: Text to analyze
        
        Returns:
            List of ProductMatch objects from keyword matches
        """
        text_lower = text.lower()
        matches = []
        
        for keyword, (product_code, confidence) in self.KEYWORD_MAPPINGS.items():
            if keyword in text_lower:
                matches.append(ProductMatch(
                    product_name=self.PRODUCTS[product_code],
                    confidence=confidence,
                    reason_code='keyword_match',
                    reasoning=f'Direct mention of "{keyword}" indicates need for {self.PRODUCTS[product_code]}',
                    keywords_found=[keyword],
                    cues_found=[],
                    uncertainty_flag=(confidence < 0.60)
                ))
        
        return matches
    
    def apply_operational_rules(self, cues: List[str]) -> List[ProductMatch]:
        """
        Apply operational cue inference rules.
        
        Args:
            cues: List of operational cues found
        
        Returns:
            List of ProductMatch objects from operational inferences
        """
        matches: Dict[str, ProductMatch] = {}
        
        for cue in cues:
            cue_lower = cue.lower()
            if cue_lower in self.OPERATIONAL_CUE_RULES:
                rules = self.OPERATIONAL_CUE_RULES[cue_lower]
                
                for product_code, confidence, reasoning in rules:
                    if product_code not in matches:
                        matches[product_code] = ProductMatch(
                            product_name=self.PRODUCTS[product_code],
                            confidence=confidence,
                            reason_code='operational_cue',
                            reasoning=reasoning,
                            keywords_found=[],
                            cues_found=[cue],
                            uncertainty_flag=(confidence < 0.60)
                        )
                    else:
                        # Add cue to existing match
                        matches[product_code].cues_found.append(cue)
        
        return list(matches.values())
    
    def calculate_confidence(
        self,
        match: ProductMatch,
        context: Optional[str] = None
    ) -> float:
        """
        Calculate or adjust confidence score for a product match.
        
        Args:
            match: ProductMatch object
            context: Optional context text for adjustment
        
        Returns:
            Adjusted confidence score (0.0 to 1.0)
        """
        confidence = match.confidence
        
        # Boost confidence if multiple evidence sources
        if match.keywords_found and match.cues_found:
            confidence = min(1.0, confidence + 0.1)
        
        # Boost if multiple keywords or cues
        if len(match.keywords_found) > 1:
            confidence = min(1.0, confidence + 0.05)
        if len(match.cues_found) > 1:
            confidence = min(1.0, confidence + 0.05)
        
        return confidence
    
    def generate_reasoning(self, match: ProductMatch) -> str:
        """
        Generate human-readable reasoning for a product recommendation.
        
        Args:
            match: ProductMatch object
        
        Returns:
            Reasoning text
        """
        reasoning_parts = []
        
        if match.keywords_found:
            keywords_str = ', '.join(f'"{k}"' for k in match.keywords_found)
            reasoning_parts.append(f'Direct mention of {keywords_str}')
        
        if match.cues_found:
            cues_str = ', '.join(f'"{c}"' for c in match.cues_found)
            reasoning_parts.append(f'Operational indicators: {cues_str}')
        
        if reasoning_parts:
            base_reasoning = ' and '.join(reasoning_parts)
            return f'{base_reasoning} suggests need for {match.product_name}'
        
        return match.reasoning
    
    def get_product_name(self, product_code: str) -> str:
        """
        Get full product name from code.
        
        Args:
            product_code: Product code (e.g., 'FO', 'HSD')
        
        Returns:
            Full product name
        """
        return self.PRODUCTS.get(product_code, product_code)
    
    def get_all_products(self) -> Dict[str, str]:
        """
        Get all available products.
        
        Returns:
            Dictionary of product codes to names
        """
        return self.PRODUCTS.copy()
