"""Unit tests for Product Inference Engine."""

import pytest
from app.services.product_inference import ProductInferenceEngine, ProductMatch


class TestProductInferenceEngine:
    """Test product inference functionality."""
    
    @pytest.fixture
    def engine(self):
        """Create product inference engine."""
        return ProductInferenceEngine()
    
    def test_infer_products_from_keywords(self, engine):
        """Test product inference from direct keywords."""
        keywords = ['furnace oil', 'diesel']
        cues = []
        
        recommendations = engine.infer_products(
            text="Test text",
            product_keywords=keywords,
            operational_cues=cues,
            top_n=3
        )
        
        assert len(recommendations) > 0
        product_names = [r.product_name for r in recommendations]
        assert 'Furnace Oil' in product_names
        assert 'High Speed Diesel' in product_names
    
    def test_infer_products_from_operational_cues(self, engine):
        """Test product inference from operational cues."""
        keywords = []
        cues = ['boiler', 'genset']
        
        recommendations = engine.infer_products(
            text="Test text",
            product_keywords=keywords,
            operational_cues=cues,
            top_n=3
        )
        
        assert len(recommendations) > 0
        # Boiler should suggest FO, genset should suggest HSD
        product_names = [r.product_name for r in recommendations]
        assert 'Furnace Oil' in product_names or 'High Speed Diesel' in product_names
    
    def test_infer_products_top_n_limit(self, engine):
        """Test that top_n parameter limits results."""
        keywords = ['furnace oil', 'diesel', 'bitumen', 'lpg']
        cues = ['boiler', 'genset', 'road project']
        
        recommendations = engine.infer_products(
            text="Test text",
            product_keywords=keywords,
            operational_cues=cues,
            top_n=2
        )
        
        assert len(recommendations) <= 2
    
    def test_infer_products_sorted_by_confidence(self, engine):
        """Test that recommendations are sorted by confidence."""
        keywords = ['furnace oil', 'diesel']
        cues = []
        
        recommendations = engine.infer_products(
            text="Test text",
            product_keywords=keywords,
            operational_cues=cues,
            top_n=3
        )
        
        # Check that confidence scores are in descending order
        for i in range(len(recommendations) - 1):
            assert recommendations[i].confidence >= recommendations[i + 1].confidence
    
    def test_apply_keyword_rules(self, engine):
        """Test keyword rule application."""
        text = "The facility will use furnace oil and high speed diesel."
        
        matches = engine.apply_keyword_rules(text)
        
        assert len(matches) > 0
        product_names = [m.product_name for m in matches]
        assert 'Furnace Oil' in product_names
        assert 'High Speed Diesel' in product_names
    
    def test_apply_operational_rules(self, engine):
        """Test operational cue rule application."""
        cues = ['boiler', 'road project']
        
        matches = engine.apply_operational_rules(cues)
        
        assert len(matches) > 0
        # Boiler should suggest FO/LDO, road project should suggest bitumen
        product_names = [m.product_name for m in matches]
        assert any(name in product_names for name in ['Furnace Oil', 'Bitumen'])
    
    def test_boiler_cue_inference(self, engine):
        """Test that boiler cue infers FO and LDO."""
        cues = ['boiler']
        
        matches = engine.apply_operational_rules(cues)
        
        product_names = [m.product_name for m in matches]
        assert 'Furnace Oil' in product_names
        assert 'Light Diesel Oil' in product_names
    
    def test_genset_cue_inference(self, engine):
        """Test that genset cue infers HSD."""
        cues = ['genset']
        
        matches = engine.apply_operational_rules(cues)
        
        product_names = [m.product_name for m in matches]
        assert 'High Speed Diesel' in product_names
    
    def test_road_project_cue_inference(self, engine):
        """Test that road project cue infers bitumen."""
        cues = ['road project']
        
        matches = engine.apply_operational_rules(cues)
        
        product_names = [m.product_name for m in matches]
        assert 'Bitumen' in product_names
    
    def test_shipping_cue_inference(self, engine):
        """Test that shipping cue infers bunker fuel."""
        cues = ['shipping']
        
        matches = engine.apply_operational_rules(cues)
        
        product_names = [m.product_name for m in matches]
        assert 'Bunker Fuel' in product_names
    
    def test_jute_mill_cue_inference(self, engine):
        """Test that jute mill cue infers jute batching oil."""
        cues = ['jute mill']
        
        matches = engine.apply_operational_rules(cues)
        
        product_names = [m.product_name for m in matches]
        assert 'Jute Batching Oil' in product_names
    
    def test_steel_plant_cue_inference(self, engine):
        """Test that steel plant cue infers wash oil."""
        cues = ['steel plant']
        
        matches = engine.apply_operational_rules(cues)
        
        product_names = [m.product_name for m in matches]
        assert 'Steel Wash Oil' in product_names
    
    def test_warehouse_cue_inference(self, engine):
        """Test that warehouse cue infers HSD."""
        cues = ['warehouse']
        
        matches = engine.apply_operational_rules(cues)
        
        product_names = [m.product_name for m in matches]
        assert 'High Speed Diesel' in product_names
    
    def test_confidence_score_range(self, engine):
        """Test that confidence scores are in valid range."""
        keywords = ['furnace oil']
        cues = ['boiler']
        
        recommendations = engine.infer_products(
            text="Test text",
            product_keywords=keywords,
            operational_cues=cues,
            top_n=3
        )
        
        for rec in recommendations:
            assert 0.0 <= rec.confidence <= 1.0
    
    def test_keyword_match_reason_code(self, engine):
        """Test that keyword matches have correct reason code."""
        text = "Supply of furnace oil required."
        
        matches = engine.apply_keyword_rules(text)
        
        for match in matches:
            assert match.reason_code == 'keyword_match'
    
    def test_operational_cue_reason_code(self, engine):
        """Test that operational cue matches have correct reason code."""
        cues = ['boiler']
        
        matches = engine.apply_operational_rules(cues)
        
        for match in matches:
            assert match.reason_code == 'operational_cue'
    
    def test_generate_reasoning(self, engine):
        """Test reasoning generation."""
        match = ProductMatch(
            product_name='Furnace Oil',
            confidence=0.85,
            reason_code='keyword_match',
            reasoning='Original reasoning',
            keywords_found=['furnace oil'],
            cues_found=['boiler']
        )
        
        reasoning = engine.generate_reasoning(match)
        
        assert 'furnace oil' in reasoning.lower()
        assert 'boiler' in reasoning.lower()
    
    def test_calculate_confidence_boost(self, engine):
        """Test confidence boost for multiple evidence sources."""
        match = ProductMatch(
            product_name='Furnace Oil',
            confidence=0.80,
            reason_code='keyword_match',
            reasoning='Test',
            keywords_found=['furnace oil', 'fo'],
            cues_found=['boiler', 'furnace']
        )
        
        adjusted_confidence = engine.calculate_confidence(match)
        
        # Should be boosted for multiple keywords and cues
        assert adjusted_confidence > match.confidence
    
    def test_get_product_name(self, engine):
        """Test product name retrieval."""
        assert engine.get_product_name('FO') == 'Furnace Oil'
        assert engine.get_product_name('HSD') == 'High Speed Diesel'
        assert engine.get_product_name('BITUMEN') == 'Bitumen'
    
    def test_get_all_products(self, engine):
        """Test getting all products."""
        products = engine.get_all_products()
        
        assert len(products) > 0
        assert 'FO' in products
        assert 'HSD' in products
        assert 'BITUMEN' in products
        assert products['FO'] == 'Furnace Oil'
    
    def test_multiple_cues_same_product(self, engine):
        """Test that multiple cues for same product boost confidence."""
        keywords = []
        cues = ['boiler', 'furnace']  # Both suggest FO
        
        recommendations = engine.infer_products(
            text="Test text",
            product_keywords=keywords,
            operational_cues=cues,
            top_n=3
        )
        
        # Find FO recommendation
        fo_rec = next((r for r in recommendations if 'Furnace Oil' in r.product_name), None)
        assert fo_rec is not None
        assert len(fo_rec.cues_found) > 1
    
    def test_empty_input(self, engine):
        """Test inference with empty inputs."""
        recommendations = engine.infer_products(
            text="",
            product_keywords=[],
            operational_cues=[],
            top_n=3
        )
        
        assert len(recommendations) == 0
    
    def test_case_insensitive_keyword_matching(self, engine):
        """Test that keyword matching is case insensitive."""
        text = "Supply of FURNACE OIL and HIGH SPEED DIESEL required."
        
        matches = engine.apply_keyword_rules(text)
        
        product_names = [m.product_name for m in matches]
        assert 'Furnace Oil' in product_names
        assert 'High Speed Diesel' in product_names
    
    def test_product_match_has_required_fields(self, engine):
        """Test that ProductMatch has all required fields."""
        keywords = ['diesel']
        cues = []
        
        recommendations = engine.infer_products(
            text="Test",
            product_keywords=keywords,
            operational_cues=cues,
            top_n=1
        )
        
        assert len(recommendations) > 0
        match = recommendations[0]
        assert hasattr(match, 'product_name')
        assert hasattr(match, 'confidence')
        assert hasattr(match, 'reason_code')
        assert hasattr(match, 'reasoning')
        assert hasattr(match, 'keywords_found')
        assert hasattr(match, 'cues_found')
