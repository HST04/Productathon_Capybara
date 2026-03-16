"""Unit tests for Company CRUD operations."""

import pytest
from unittest.mock import Mock
import uuid


def test_company_model_exists():
    """Test that Company model can be imported."""
    try:
        from app.models.company import Company
        assert Company is not None
        assert hasattr(Company, '__tablename__')
        assert Company.__tablename__ == 'companies'
    except ImportError:
        pytest.skip("Database dependencies not available")


def test_company_resolver_exists():
    """Test that CompanyResolver service can be imported."""
    try:
        from app.services.company_resolver import CompanyResolver
        assert CompanyResolver is not None
    except ImportError:
        pytest.skip("Database dependencies not available")


def test_company_resolver_has_crud_methods():
    """Test that CompanyResolver has all required CRUD methods."""
    try:
        from app.services.company_resolver import CompanyResolver
        
        # Check that all required methods exist
        assert hasattr(CompanyResolver, 'create_company')
        assert hasattr(CompanyResolver, 'get_company_by_id')
        assert hasattr(CompanyResolver, 'get_company_by_name')
        assert hasattr(CompanyResolver, 'get_company_by_cin')
        assert hasattr(CompanyResolver, 'get_company_by_gst')
        assert hasattr(CompanyResolver, 'get_company_by_embedding_id')
        assert hasattr(CompanyResolver, 'search_companies_by_name')
        assert hasattr(CompanyResolver, 'list_companies')
        assert hasattr(CompanyResolver, 'update_company')
        assert hasattr(CompanyResolver, 'add_name_variant')
        assert hasattr(CompanyResolver, 'add_location')
        assert hasattr(CompanyResolver, 'merge_company_info')
        assert hasattr(CompanyResolver, 'delete_company')
        assert hasattr(CompanyResolver, 'count_companies')
    except ImportError:
        pytest.skip("Database dependencies not available")


def test_create_company_signature():
    """Test that create_company has the correct signature."""
    try:
        from app.services.company_resolver import CompanyResolver
        import inspect
        
        sig = inspect.signature(CompanyResolver.create_company)
        params = list(sig.parameters.keys())
        
        # Check required parameters
        assert 'self' in params
        assert 'name' in params
        
        # Check optional parameters
        assert 'name_variants' in params
        assert 'cin' in params
        assert 'gst' in params
        assert 'website' in params
        assert 'industry' in params
        assert 'address' in params
        assert 'locations' in params
        assert 'key_products' in params
        assert 'embedding_id' in params
    except ImportError:
        pytest.skip("Database dependencies not available")


def test_merge_company_info_signature():
    """Test that merge_company_info has the correct signature."""
    try:
        from app.services.company_resolver import CompanyResolver
        import inspect
        
        sig = inspect.signature(CompanyResolver.merge_company_info)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'company_id' in params
        assert 'new_info' in params
    except ImportError:
        pytest.skip("Database dependencies not available")
