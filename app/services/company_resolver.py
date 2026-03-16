"""Company Resolver for managing company cards and CRUD operations."""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.company import Company
from app.utils.embeddings import get_embedding_generator
from app.db.pinecone_client import pinecone_client
import uuid
import logging

logger = logging.getLogger(__name__)


class CompanyResolver:
    """Manages company cards with CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.embedding_generator = get_embedding_generator()
    
    def generate_embedding(self, company_name: str, name_variants: Optional[List[str]] = None) -> tuple:
        """
        Generate embedding for a company name.
        
        Args:
            company_name: Company name
            name_variants: Optional list of name variants
        
        Returns:
            Tuple of (embedding_array, embedding_id)
        
        Raises:
            RuntimeError: If embedding generation fails
        """
        try:
            # Generate embedding
            embedding = self.embedding_generator.generate_company_embedding(
                company_name,
                name_variants
            )
            
            # Generate unique embedding ID
            embedding_id = f"company_{uuid.uuid4().hex[:16]}"
            
            logger.info(f"Generated embedding for company '{company_name}' with ID: {embedding_id}")
            
            return embedding, embedding_id
        
        except Exception as e:
            logger.error(f"Failed to generate embedding for company '{company_name}': {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")
    
    def create_company(
        self,
        name: str,
        name_variants: Optional[List[str]] = None,
        cin: Optional[str] = None,
        gst: Optional[str] = None,
        website: Optional[str] = None,
        industry: Optional[str] = None,
        address: Optional[str] = None,
        locations: Optional[List[str]] = None,
        key_products: Optional[List[str]] = None,
        embedding_id: Optional[str] = None
    ) -> Company:
        """
        Create a new company card.
        
        Args:
            name: Company name (required)
            name_variants: Alternative spellings/names
            cin: Corporate Identification Number
            gst: GST number
            website: Company website URL
            industry: Industry classification
            address: Registered address
            locations: Plant/office locations
            key_products: Key products manufactured/sold
            embedding_id: Pinecone vector ID for semantic matching
        
        Returns:
            Created Company object
        """
        company = Company(
            name=name,
            name_variants=name_variants or [],
            cin=cin,
            gst=gst,
            website=website,
            industry=industry,
            address=address,
            locations=locations or [],
            key_products=key_products or [],
            embedding_id=embedding_id
        )
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company
    
    def get_company_by_id(self, company_id: uuid.UUID) -> Optional[Company]:
        """Get company by ID."""
        return self.db.query(Company).filter(Company.id == company_id).first()
    
    def get_company_by_name(self, name: str) -> Optional[Company]:
        """Get company by exact name match."""
        return self.db.query(Company).filter(Company.name == name).first()
    
    def get_company_by_cin(self, cin: str) -> Optional[Company]:
        """Get company by CIN."""
        return self.db.query(Company).filter(Company.cin == cin).first()
    
    def get_company_by_gst(self, gst: str) -> Optional[Company]:
        """Get company by GST number."""
        return self.db.query(Company).filter(Company.gst == gst).first()
    
    def get_company_by_embedding_id(self, embedding_id: str) -> Optional[Company]:
        """Get company by Pinecone embedding ID."""
        return self.db.query(Company).filter(
            Company.embedding_id == embedding_id
        ).first()
    
    def search_companies_by_name(self, search_term: str) -> List[Company]:
        """
        Search companies by name or name variants.
        
        Args:
            search_term: Search string
        
        Returns:
            List of matching Company objects
        """
        search_pattern = f"%{search_term}%"
        return self.db.query(Company).filter(
            or_(
                Company.name.ilike(search_pattern),
                Company.name_variants.any(search_term)
            )
        ).all()
    
    def list_companies(
        self,
        industry: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Company]:
        """
        List companies with optional filters.
        
        Args:
            industry: Filter by industry (optional)
            limit: Maximum number of results (optional)
            offset: Number of results to skip (default 0)
        
        Returns:
            List of Company objects
        """
        query = self.db.query(Company)
        
        if industry:
            query = query.filter(Company.industry == industry)
        
        query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def update_company(
        self,
        company_id: uuid.UUID,
        **kwargs
    ) -> Optional[Company]:
        """
        Update company fields.
        
        Args:
            company_id: Company ID
            **kwargs: Fields to update
        
        Returns:
            Updated Company object or None if not found
        """
        company = self.get_company_by_id(company_id)
        if not company:
            return None
        
        # Update allowed fields
        allowed_fields = {
            'name', 'name_variants', 'cin', 'gst', 'website',
            'industry', 'address', 'locations', 'key_products', 'embedding_id'
        }
        
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(company, key, value)
        
        company.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(company)
        return company
    
    def add_name_variant(self, company_id: uuid.UUID, variant: str) -> Optional[Company]:
        """
        Add a name variant to a company.
        
        Args:
            company_id: Company ID
            variant: Name variant to add
        
        Returns:
            Updated Company object or None if not found
        """
        company = self.get_company_by_id(company_id)
        if not company:
            return None
        
        if company.name_variants is None:
            company.name_variants = []
        
        if variant not in company.name_variants:
            company.name_variants = company.name_variants + [variant]
            company.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(company)
        
        return company
    
    def add_location(self, company_id: uuid.UUID, location: str) -> Optional[Company]:
        """
        Add a location to a company.
        
        Args:
            company_id: Company ID
            location: Location to add
        
        Returns:
            Updated Company object or None if not found
        """
        company = self.get_company_by_id(company_id)
        if not company:
            return None
        
        if company.locations is None:
            company.locations = []
        
        if location not in company.locations:
            company.locations = company.locations + [location]
            company.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(company)
        
        return company
    
    def merge_company_info(
        self,
        company_id: uuid.UUID,
        new_info: Dict[str, Any]
    ) -> Optional[Company]:
        """
        Merge new information into existing company card.
        Adds to arrays (name_variants, locations, key_products) without duplicates.
        Updates scalar fields only if currently empty.
        
        Args:
            company_id: Company ID
            new_info: Dictionary with new company information
        
        Returns:
            Updated Company object or None if not found
        """
        company = self.get_company_by_id(company_id)
        if not company:
            return None
        
        # Merge array fields (add unique values)
        if 'name_variants' in new_info and new_info['name_variants']:
            existing = set(company.name_variants or [])
            new_variants = set(new_info['name_variants'])
            company.name_variants = list(existing | new_variants)
        
        if 'locations' in new_info and new_info['locations']:
            existing = set(company.locations or [])
            new_locations = set(new_info['locations'])
            company.locations = list(existing | new_locations)
        
        if 'key_products' in new_info and new_info['key_products']:
            existing = set(company.key_products or [])
            new_products = set(new_info['key_products'])
            company.key_products = list(existing | new_products)
        
        # Update scalar fields only if empty
        scalar_fields = ['cin', 'gst', 'website', 'industry', 'address']
        for field in scalar_fields:
            if field in new_info and new_info[field]:
                current_value = getattr(company, field)
                if not current_value:
                    setattr(company, field, new_info[field])
        
        company.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(company)
        return company
    
    def delete_company(self, company_id: uuid.UUID) -> bool:
        """
        Delete a company from the database.
        
        Args:
            company_id: Company ID
        
        Returns:
            True if deleted, False if not found
        """
        company = self.get_company_by_id(company_id)
        if company:
            self.db.delete(company)
            self.db.commit()
            return True
        return False
    
    def count_companies(self, industry: Optional[str] = None) -> int:
        """
        Count total companies with optional filter.
        
        Args:
            industry: Filter by industry (optional)
        
        Returns:
            Count of companies
        """
        query = self.db.query(Company)
        
        if industry:
            query = query.filter(Company.industry == industry)
        
        return query.count()
    
    def find_similar_companies(
        self,
        company_name: str,
        name_variants: Optional[List[str]] = None,
        threshold: float = 0.85,
        top_k: int = 5
    ) -> List[Tuple[Company, float]]:
        """
        Find similar companies using semantic matching via Pinecone.
        
        Args:
            company_name: Company name to search for
            name_variants: Optional list of name variants
            threshold: Minimum similarity score (default 0.85)
            top_k: Maximum number of results (default 5)
        
        Returns:
            List of tuples (Company, similarity_score) sorted by score descending
        
        Raises:
            RuntimeError: If embedding generation or Pinecone query fails
        """
        try:
            # Generate embedding for the query company name
            embedding = self.embedding_generator.generate_company_embedding(
                company_name,
                name_variants
            )
            
            # Convert numpy array to list for Pinecone
            embedding_list = embedding.tolist()
            
            # Query Pinecone for similar companies
            matches = pinecone_client.search_similar_companies(
                embedding=embedding_list,
                top_k=top_k,
                threshold=threshold,
                namespace="companies"
            )
            
            # Retrieve Company objects from database
            results = []
            for match in matches:
                # Extract company_id from Pinecone ID (format: "company_{uuid}")
                pinecone_id = match.id
                if pinecone_id.startswith("company_"):
                    company_id_str = pinecone_id.replace("company_", "")
                    
                    # Look up company by embedding_id
                    company = self.get_company_by_embedding_id(pinecone_id)
                    
                    if company:
                        results.append((company, float(match.score)))
                    else:
                        logger.warning(
                            f"Company with embedding_id '{pinecone_id}' found in Pinecone "
                            f"but not in PostgreSQL"
                        )
            
            logger.info(
                f"Found {len(results)} similar companies for '{company_name}' "
                f"(threshold={threshold})"
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Failed to find similar companies for '{company_name}': {e}")
            raise RuntimeError(f"Company similarity search failed: {e}")
    
    def resolve_company(
        self,
        company_name: str,
        name_variants: Optional[List[str]] = None,
        cin: Optional[str] = None,
        gst: Optional[str] = None,
        **additional_info
    ) -> Company:
        """
        Resolve company identity using semantic matching.
        
        This method implements the core company resolution logic:
        1. Check for exact CIN/GST match (if provided)
        2. Query Pinecone for semantic matches above threshold (0.85)
        3. If match found, link to existing company and merge info
        4. If no match, create new company card
        
        Args:
            company_name: Company name (required)
            name_variants: Alternative company names
            cin: Corporate Identification Number
            gst: GST number
            **additional_info: Other company fields (website, industry, etc.)
        
        Returns:
            Company object (existing or newly created)
        
        Raises:
            RuntimeError: If resolution process fails
        """
        try:
            # Step 1: Check for exact CIN/GST match
            if cin:
                existing = self.get_company_by_cin(cin)
                if existing:
                    logger.info(f"Found company by CIN: {cin}")
                    # Merge new information
                    merge_data = {
                        'name_variants': name_variants,
                        **additional_info
                    }
                    return self.merge_company_info(existing.id, merge_data)
            
            if gst:
                existing = self.get_company_by_gst(gst)
                if existing:
                    logger.info(f"Found company by GST: {gst}")
                    # Merge new information
                    merge_data = {
                        'name_variants': name_variants,
                        **additional_info
                    }
                    return self.merge_company_info(existing.id, merge_data)
            
            # Step 2: Semantic matching via Pinecone
            similar_companies = self.find_similar_companies(
                company_name=company_name,
                name_variants=name_variants,
                threshold=0.85,
                top_k=1
            )
            
            if similar_companies:
                # Match found - link to existing company
                existing_company, similarity_score = similar_companies[0]
                logger.info(
                    f"Semantic match found: '{company_name}' -> '{existing_company.name}' "
                    f"(score={similarity_score:.3f})"
                )
                
                # Add current name as variant if not already present
                if company_name != existing_company.name:
                    self.add_name_variant(existing_company.id, company_name)
                
                # Merge additional information
                merge_data = {
                    'name_variants': name_variants,
                    'cin': cin,
                    'gst': gst,
                    **additional_info
                }
                return self.merge_company_info(existing_company.id, merge_data)
            
            # Step 3: No match found - create new company card
            logger.info(f"No match found for '{company_name}', creating new company card")
            
            # Generate embedding and store in Pinecone
            embedding, embedding_id = self.generate_embedding(
                company_name,
                name_variants
            )
            
            # Create company in PostgreSQL
            company = self.create_company(
                name=company_name,
                name_variants=name_variants,
                cin=cin,
                gst=gst,
                embedding_id=embedding_id,
                **additional_info
            )
            
            # Store embedding in Pinecone
            metadata = {
                "company_id": str(company.id),
                "company_name": company_name,
                "name_variants": name_variants or [],
                "industry": additional_info.get("industry", "")
            }
            
            pinecone_client.upsert_company_embedding(
                company_id=str(company.id),
                embedding=embedding.tolist(),
                metadata=metadata,
                namespace="companies"
            )
            
            logger.info(
                f"Created new company card for '{company_name}' "
                f"with embedding_id: {embedding_id}"
            )
            
            return company
        
        except Exception as e:
            logger.error(f"Failed to resolve company '{company_name}': {e}")
            raise RuntimeError(f"Company resolution failed: {e}")
