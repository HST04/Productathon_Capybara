"""Unit tests for Company Resolver Pinecone integration."""

import pytest
from unittest.mock import Mock, MagicMock, patch
import uuid
import numpy as np

# Try to import dependencies, skip tests if not available
try:
    from app.services.company_resolver import CompanyResolver
    from app.models.company import Company
    from app.db.pinecone_client import pinecone_client
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not DEPENDENCIES_AVAILABLE,
    reason="Database dependencies not available"
)


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_embedding_generator():
    """Mock embedding generator."""
    generator = Mock()
    # Return a 384-dim embedding
    generator.generate_company_embedding.return_value = np.random.rand(384)
    return generator


@pytest.fixture
def company_resolver(mock_db_session, mock_embedding_generator):
    """Create CompanyResolver with mocked dependencies."""
    resolver = CompanyResolver(mock_db_session)
    resolver.embedding_generator = mock_embedding_generator
    return resolver


class TestPineconeIntegration:
    """Test Pinecone integration for company matching."""
    
    def test_find_similar_companies_with_matches(self, company_resolver, mock_embedding_generator):
        """Test finding similar companies when matches exist."""
        # Setup
        company_name = "ABC Industries Ltd"
        embedding = np.random.rand(384)
        mock_embedding_generator.generate_company_embedding.return_value = embedding
        
        # Mock Pinecone response
        mock_match = Mock()
        mock_match.id = "company_123e4567-e89b-12d3-a456-426614174000"
        mock_match.score = 0.92
        mock_match.metadata = {
            "company_name": "ABC Industries Limited",
            "industry": "Manufacturing"
        }
        
        with patch.object(pinecone_client, 'search_similar_companies', return_value=[mock_match]):
            # Mock database lookup
            mock_company = Company(
                id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
                name="ABC Industries Limited",
                embedding_id="company_123e4567-e89b-12d3-a456-426614174000"
            )
            company_resolver.get_company_by_embedding_id = Mock(return_value=mock_company)
            
            # Execute
            results = company_resolver.find_similar_companies(
                company_name=company_name,
                threshold=0.85
            )
            
            # Assert
            assert len(results) == 1
            assert results[0][0].name == "ABC Industries Limited"
            assert results[0][1] == 0.92
            
            # Verify Pinecone was called correctly
            pinecone_client.search_similar_companies.assert_called_once()
            call_args = pinecone_client.search_similar_companies.call_args
            assert call_args[1]['threshold'] == 0.85
            assert call_args[1]['namespace'] == "companies"
    
    def test_find_similar_companies_no_matches(self, company_resolver, mock_embedding_generator):
        """Test finding similar companies when no matches exist."""
        # Setup
        company_name = "XYZ Corp"
        embedding = np.random.rand(384)
        mock_embedding_generator.generate_company_embedding.return_value = embedding
        
        # Mock Pinecone response with no matches
        with patch.object(pinecone_client, 'search_similar_companies', return_value=[]):
            # Execute
            results = company_resolver.find_similar_companies(
                company_name=company_name,
                threshold=0.85
            )
            
            # Assert
            assert len(results) == 0
    
    def test_find_similar_companies_below_threshold(self, company_resolver, mock_embedding_generator):
        """Test that matches below threshold are filtered out."""
        # Setup
        company_name = "Test Company"
        embedding = np.random.rand(384)
        mock_embedding_generator.generate_company_embedding.return_value = embedding
        
        # Mock Pinecone response with low score (already filtered by Pinecone client)
        with patch.object(pinecone_client, 'search_similar_companies', return_value=[]):
            # Execute
            results = company_resolver.find_similar_companies(
                company_name=company_name,
                threshold=0.85
            )
            
            # Assert
            assert len(results) == 0
    
    def test_resolve_company_creates_new_with_pinecone(self, company_resolver, mock_embedding_generator):
        """Test resolving a new company creates entry in both PostgreSQL and Pinecone."""
        # Setup
        company_name = "New Company Ltd"
        embedding = np.random.rand(384)
        embedding_id = "company_abc123"
        
        mock_embedding_generator.generate_company_embedding.return_value = embedding
        company_resolver.generate_embedding = Mock(return_value=(embedding, embedding_id))
        
        # Mock no existing matches
        company_resolver.get_company_by_cin = Mock(return_value=None)
        company_resolver.get_company_by_gst = Mock(return_value=None)
        company_resolver.find_similar_companies = Mock(return_value=[])
        
        # Mock company creation
        new_company = Company(
            id=uuid.uuid4(),
            name=company_name,
            embedding_id=embedding_id
        )
        company_resolver.create_company = Mock(return_value=new_company)
        
        # Mock Pinecone upsert
        with patch.object(pinecone_client, 'upsert_company_embedding') as mock_upsert:
            # Execute
            result = company_resolver.resolve_company(
                company_name=company_name,
                industry="Technology"
            )
            
            # Assert
            assert result.name == company_name
            assert result.embedding_id == embedding_id
            
            # Verify Pinecone upsert was called
            mock_upsert.assert_called_once()
            call_args = mock_upsert.call_args
            assert call_args[1]['company_id'] == str(new_company.id)
            assert call_args[1]['namespace'] == "companies"
            assert 'company_name' in call_args[1]['metadata']
    
    def test_resolve_company_links_to_existing_via_semantic_match(
        self,
        company_resolver,
        mock_embedding_generator
    ):
        """Test resolving company links to existing via Pinecone semantic match."""
        # Setup
        company_name = "ABC Ltd"
        existing_company = Company(
            id=uuid.uuid4(),
            name="ABC Industries Limited",
            embedding_id="company_existing123"
        )
        
        # Mock semantic match found
        company_resolver.get_company_by_cin = Mock(return_value=None)
        company_resolver.get_company_by_gst = Mock(return_value=None)
        company_resolver.find_similar_companies = Mock(
            return_value=[(existing_company, 0.92)]
        )
        company_resolver.add_name_variant = Mock(return_value=existing_company)
        company_resolver.merge_company_info = Mock(return_value=existing_company)
        
        # Execute
        result = company_resolver.resolve_company(
            company_name=company_name,
            industry="Manufacturing"
        )
        
        # Assert
        assert result.id == existing_company.id
        
        # Verify name variant was added
        company_resolver.add_name_variant.assert_called_once_with(
            existing_company.id,
            company_name
        )
        
        # Verify info was merged
        company_resolver.merge_company_info.assert_called_once()
    
    def test_resolve_company_prefers_cin_over_semantic_match(self, company_resolver):
        """Test that CIN match takes precedence over semantic matching."""
        # Setup
        cin = "U12345AB1234ABC123456"
        existing_company = Company(
            id=uuid.uuid4(),
            name="Exact Match Company",
            cin=cin
        )
        
        # Mock CIN match
        company_resolver.get_company_by_cin = Mock(return_value=existing_company)
        company_resolver.merge_company_info = Mock(return_value=existing_company)
        
        # Mock semantic match (should not be called)
        company_resolver.find_similar_companies = Mock()
        
        # Execute
        result = company_resolver.resolve_company(
            company_name="Different Name",
            cin=cin
        )
        
        # Assert
        assert result.id == existing_company.id
        
        # Verify semantic search was NOT called
        company_resolver.find_similar_companies.assert_not_called()
    
    def test_resolve_company_handles_embedding_generation_failure(
        self,
        company_resolver,
        mock_embedding_generator
    ):
        """Test that embedding generation failure is handled gracefully."""
        # Setup
        mock_embedding_generator.generate_company_embedding.side_effect = RuntimeError(
            "Embedding generation failed"
        )
        
        # Mock no CIN/GST matches
        company_resolver.get_company_by_cin = Mock(return_value=None)
        company_resolver.get_company_by_gst = Mock(return_value=None)
        
        # Execute and assert
        with pytest.raises(RuntimeError, match="Company resolution failed"):
            company_resolver.resolve_company(company_name="Test Company")
    
    def test_find_similar_companies_with_name_variants(
        self,
        company_resolver,
        mock_embedding_generator
    ):
        """Test finding similar companies using name variants."""
        # Setup
        company_name = "ABC Industries"
        name_variants = ["ABC Ltd", "ABC Corp"]
        embedding = np.random.rand(384)
        mock_embedding_generator.generate_company_embedding.return_value = embedding
        
        with patch.object(pinecone_client, 'search_similar_companies', return_value=[]):
            # Execute
            company_resolver.find_similar_companies(
                company_name=company_name,
                name_variants=name_variants,
                threshold=0.85
            )
            
            # Assert embedding was generated with variants
            mock_embedding_generator.generate_company_embedding.assert_called_once_with(
                company_name,
                name_variants
            )
    
    def test_resolve_company_metadata_in_pinecone(self, company_resolver, mock_embedding_generator):
        """Test that company metadata is correctly stored in Pinecone."""
        # Setup
        company_name = "Tech Corp"
        industry = "Technology"
        name_variants = ["TechCorp", "Tech Corporation"]
        embedding = np.random.rand(384)
        embedding_id = "company_tech123"
        
        mock_embedding_generator.generate_company_embedding.return_value = embedding
        company_resolver.generate_embedding = Mock(return_value=(embedding, embedding_id))
        
        # Mock no existing matches
        company_resolver.get_company_by_cin = Mock(return_value=None)
        company_resolver.get_company_by_gst = Mock(return_value=None)
        company_resolver.find_similar_companies = Mock(return_value=[])
        
        # Mock company creation
        new_company = Company(
            id=uuid.uuid4(),
            name=company_name,
            embedding_id=embedding_id,
            industry=industry
        )
        company_resolver.create_company = Mock(return_value=new_company)
        
        # Mock Pinecone upsert
        with patch.object(pinecone_client, 'upsert_company_embedding') as mock_upsert:
            # Execute
            company_resolver.resolve_company(
                company_name=company_name,
                name_variants=name_variants,
                industry=industry
            )
            
            # Assert metadata is correct
            call_args = mock_upsert.call_args
            metadata = call_args[1]['metadata']
            assert metadata['company_name'] == company_name
            assert metadata['name_variants'] == name_variants
            assert metadata['industry'] == industry
            assert 'company_id' in metadata
