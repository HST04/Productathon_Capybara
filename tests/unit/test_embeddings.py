"""Unit tests for embedding generation utilities."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np


class TestEmbeddingGenerator:
    """Test embedding generation functionality."""
    
    @pytest.fixture
    def mock_sentence_transformer(self):
        """Create a mock SentenceTransformer."""
        mock_model = Mock()
        # Mock encode to return a 384-dim array
        mock_model.encode.return_value = np.random.rand(384)
        return mock_model
    
    @pytest.fixture
    def embedding_generator(self, mock_sentence_transformer):
        """Create an EmbeddingGenerator with mocked model."""
        with patch('app.utils.embeddings.SentenceTransformer', return_value=mock_sentence_transformer):
            from app.utils.embeddings import EmbeddingGenerator
            return EmbeddingGenerator()
    
    def test_embedding_generator_initialization(self):
        """Test that EmbeddingGenerator initializes with correct model name."""
        try:
            from app.utils.embeddings import EmbeddingGenerator
            
            generator = EmbeddingGenerator()
            assert generator.model_name == "all-MiniLM-L6-v2"
            assert generator.EMBEDDING_DIMENSION == 384
        except ImportError:
            pytest.skip("sentence-transformers not available")
    
    def test_generate_embedding_single_text(self, embedding_generator, mock_sentence_transformer):
        """Test generating embedding for a single text."""
        text = "ABC Industries Ltd"
        
        result = embedding_generator.generate_embedding(text)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (384,)
        mock_sentence_transformer.encode.assert_called_once()
    
    def test_generate_embedding_empty_text_raises_error(self, embedding_generator):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            embedding_generator.generate_embedding("")
    
    def test_generate_embeddings_multiple_texts(self, embedding_generator, mock_sentence_transformer):
        """Test generating embeddings for multiple texts."""
        texts = ["ABC Industries", "XYZ Corporation", "DEF Ltd"]
        
        # Mock to return array with correct shape
        mock_sentence_transformer.encode.return_value = np.random.rand(3, 384)
        
        result = embedding_generator.generate_embeddings(texts)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 384)
        mock_sentence_transformer.encode.assert_called_once()
    
    def test_generate_embeddings_empty_list_raises_error(self, embedding_generator):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            embedding_generator.generate_embeddings([])
    
    def test_generate_company_embedding_without_variants(self, embedding_generator, mock_sentence_transformer):
        """Test generating company embedding without variants."""
        company_name = "ABC Industries Ltd"
        
        result = embedding_generator.generate_company_embedding(company_name)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (384,)
        mock_sentence_transformer.encode.assert_called_once()
    
    def test_generate_company_embedding_with_variants(self, embedding_generator, mock_sentence_transformer):
        """Test generating company embedding with name variants."""
        company_name = "ABC Industries Ltd"
        variants = ["ABC Ltd", "ABC Corp"]
        
        # Mock to return array for multiple names
        mock_sentence_transformer.encode.return_value = np.random.rand(3, 384)
        
        result = embedding_generator.generate_company_embedding(company_name, variants)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (384,)
        # Should encode all names together
        mock_sentence_transformer.encode.assert_called_once()
    
    def test_calculate_similarity(self, embedding_generator):
        """Test calculating cosine similarity between embeddings."""
        # Create two normalized random embeddings
        emb1 = np.random.rand(384)
        emb1 = emb1 / np.linalg.norm(emb1)
        
        emb2 = np.random.rand(384)
        emb2 = emb2 / np.linalg.norm(emb2)
        
        similarity = embedding_generator.calculate_similarity(emb1, emb2)
        
        assert isinstance(similarity, float)
        assert -1.0 <= similarity <= 1.0
    
    def test_calculate_similarity_identical_embeddings(self, embedding_generator):
        """Test that identical embeddings have similarity of 1.0."""
        emb = np.random.rand(384)
        emb = emb / np.linalg.norm(emb)
        
        similarity = embedding_generator.calculate_similarity(emb, emb)
        
        assert abs(similarity - 1.0) < 1e-6
    
    def test_calculate_similarity_different_shapes_raises_error(self, embedding_generator):
        """Test that different embedding shapes raise ValueError."""
        emb1 = np.random.rand(384)
        emb2 = np.random.rand(256)
        
        with pytest.raises(ValueError, match="Embedding shapes must match"):
            embedding_generator.calculate_similarity(emb1, emb2)
    
    def test_get_embedding_generator_singleton(self):
        """Test that get_embedding_generator returns singleton instance."""
        try:
            from app.utils.embeddings import get_embedding_generator
            
            with patch('app.utils.embeddings.SentenceTransformer'):
                gen1 = get_embedding_generator()
                gen2 = get_embedding_generator()
                
                assert gen1 is gen2
        except ImportError:
            pytest.skip("sentence-transformers not available")
    
    def test_lazy_model_loading(self):
        """Test that model is loaded lazily on first use."""
        try:
            from app.utils.embeddings import EmbeddingGenerator
            
            with patch('app.utils.embeddings.SentenceTransformer') as mock_st:
                generator = EmbeddingGenerator()
                
                # Model should not be loaded yet
                mock_st.assert_not_called()
                
                # Access model property
                _ = generator.model
                
                # Now model should be loaded
                mock_st.assert_called_once_with("all-MiniLM-L6-v2")
        except ImportError:
            pytest.skip("sentence-transformers not available")
    
    def test_model_loading_error_handling(self):
        """Test that model loading errors are handled gracefully."""
        try:
            from app.utils.embeddings import EmbeddingGenerator
            
            with patch('app.utils.embeddings.SentenceTransformer', side_effect=Exception("Model not found")):
                generator = EmbeddingGenerator()
                
                with pytest.raises(RuntimeError, match="Failed to load embedding model"):
                    _ = generator.model
        except ImportError:
            pytest.skip("sentence-transformers not available")


class TestCompanyResolverEmbeddings:
    """Test embedding integration in CompanyResolver."""
    
    def test_company_resolver_has_generate_embedding_method(self):
        """Test that CompanyResolver has generate_embedding method."""
        try:
            from app.services.company_resolver import CompanyResolver
            
            assert hasattr(CompanyResolver, 'generate_embedding')
        except ImportError:
            pytest.skip("Database dependencies not available")
    
    def test_generate_embedding_returns_tuple(self):
        """Test that generate_embedding returns (embedding, embedding_id) tuple."""
        try:
            from app.services.company_resolver import CompanyResolver
            from unittest.mock import Mock
            
            mock_db = Mock()
            
            with patch('app.services.company_resolver.get_embedding_generator') as mock_gen:
                mock_generator = Mock()
                mock_generator.generate_company_embedding.return_value = np.random.rand(384)
                mock_gen.return_value = mock_generator
                
                resolver = CompanyResolver(mock_db)
                result = resolver.generate_embedding("ABC Industries")
                
                assert isinstance(result, tuple)
                assert len(result) == 2
                embedding, embedding_id = result
                assert isinstance(embedding, np.ndarray)
                assert isinstance(embedding_id, str)
                assert embedding_id.startswith("company_")
        except ImportError:
            pytest.skip("Dependencies not available")
