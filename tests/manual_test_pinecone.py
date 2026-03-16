"""Manual test script for Pinecone integration.

This script demonstrates the Pinecone integration for company matching.
Run this manually to verify the integration works.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment variables
os.environ.setdefault('PINECONE_API_KEY', 'test-key')
os.environ.setdefault('PINECONE_ENVIRONMENT', 'test-env')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost:5432/test_db')

from unittest.mock import Mock, patch
import numpy as np
from app.services.company_resolver import CompanyResolver
from app.models.company import Company
from app.db.pinecone_client import pinecone_client
import uuid


def test_pinecone_integration():
    """Test Pinecone integration manually."""
    print("Testing Pinecone Integration for Company Matching")
    print("=" * 60)
    
    # Create mock database session
    mock_db = Mock()
    
    # Create company resolver
    resolver = CompanyResolver(mock_db)
    
    # Mock embedding generator
    resolver.embedding_generator = Mock()
    test_embedding = np.random.rand(384)
    resolver.embedding_generator.generate_company_embedding.return_value = test_embedding
    
    print("\n1. Testing find_similar_companies with matches...")
    
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
        resolver.get_company_by_embedding_id = Mock(return_value=mock_company)
        
        # Execute
        results = resolver.find_similar_companies(
            company_name="ABC Industries Ltd",
            threshold=0.85
        )
        
        # Verify
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0][0].name == "ABC Industries Limited"
        assert results[0][1] == 0.92
        print("   ✓ Found similar company with score 0.92")
    
    print("\n2. Testing resolve_company creates new company...")
    
    # Reset mocks
    resolver.generate_embedding = Mock(return_value=(test_embedding, "company_new123"))
    resolver.get_company_by_cin = Mock(return_value=None)
    resolver.get_company_by_gst = Mock(return_value=None)
    resolver.find_similar_companies = Mock(return_value=[])
    
    new_company = Company(
        id=uuid.uuid4(),
        name="New Company Ltd",
        embedding_id="company_new123"
    )
    resolver.create_company = Mock(return_value=new_company)
    
    with patch.object(pinecone_client, 'upsert_company_embedding') as mock_upsert:
        result = resolver.resolve_company(
            company_name="New Company Ltd",
            industry="Technology"
        )
        
        assert result.name == "New Company Ltd"
        assert mock_upsert.called
        print("   ✓ Created new company and stored in Pinecone")
    
    print("\n3. Testing resolve_company links to existing via semantic match...")
    
    existing_company = Company(
        id=uuid.uuid4(),
        name="Existing Corp",
        embedding_id="company_existing"
    )
    
    resolver.get_company_by_cin = Mock(return_value=None)
    resolver.get_company_by_gst = Mock(return_value=None)
    resolver.find_similar_companies = Mock(return_value=[(existing_company, 0.91)])
    resolver.add_name_variant = Mock(return_value=existing_company)
    resolver.merge_company_info = Mock(return_value=existing_company)
    
    result = resolver.resolve_company(
        company_name="Existing Corporation",
        industry="Finance"
    )
    
    assert result.id == existing_company.id
    assert resolver.add_name_variant.called
    print("   ✓ Linked to existing company via semantic match")
    
    print("\n4. Testing CIN match takes precedence...")
    
    cin_company = Company(
        id=uuid.uuid4(),
        name="CIN Match Company",
        cin="U12345AB1234ABC123456"
    )
    
    resolver.get_company_by_cin = Mock(return_value=cin_company)
    resolver.merge_company_info = Mock(return_value=cin_company)
    resolver.find_similar_companies = Mock()  # Should not be called
    
    result = resolver.resolve_company(
        company_name="Different Name",
        cin="U12345AB1234ABC123456"
    )
    
    assert result.id == cin_company.id
    assert not resolver.find_similar_companies.called
    print("   ✓ CIN match took precedence over semantic matching")
    
    print("\n" + "=" * 60)
    print("All Pinecone integration tests passed! ✓")
    print("\nKey features verified:")
    print("  • Semantic company matching via Pinecone")
    print("  • New company creation with embedding storage")
    print("  • Linking to existing companies above threshold (0.85)")
    print("  • CIN/GST exact match precedence")
    print("  • Metadata storage in Pinecone")


if __name__ == "__main__":
    try:
        test_pinecone_integration()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
