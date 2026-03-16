"""Pinecone client setup for vector database operations."""

from pinecone import Pinecone, ServerlessSpec
from app.utils.config import settings


class PineconeClient:
    """Wrapper for Pinecone operations."""
    
    def __init__(self):
        """Initialize Pinecone client."""
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        self._index = None
    
    def get_index(self):
        """Get or create Pinecone index."""
        if self._index is None:
            # Check if index exists
            if self.index_name not in self.pc.list_indexes().names():
                # Create index with 384 dimensions (all-MiniLM-L6-v2)
                self.pc.create_index(
                    name=self.index_name,
                    dimension=384,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-west-2"
                    )
                )
            
            self._index = self.pc.Index(self.index_name)
        
        return self._index
    
    def upsert_company_embedding(
        self,
        company_id: str,
        embedding: list,
        metadata: dict,
        namespace: str = "companies"
    ):
        """
        Store company name embedding in Pinecone.
        
        Args:
            company_id: Company UUID
            embedding: 384-dim embedding vector
            metadata: Company metadata (name, name_variants, industry, etc.)
            namespace: Pinecone namespace (default "companies")
        """
        index = self.get_index()
        index.upsert(
            vectors=[{
                "id": f"company_{company_id}",
                "values": embedding,
                "metadata": metadata
            }],
            namespace=namespace
        )
    
    def search_similar_companies(
        self,
        embedding: list,
        top_k: int = 5,
        threshold: float = None,
        namespace: str = "companies",
        metadata_filter: dict = None
    ):
        """
        Search for similar company embeddings.
        
        Args:
            embedding: Query embedding vector (384-dim for all-MiniLM-L6-v2)
            top_k: Number of results to return (default 5)
            threshold: Minimum similarity score (default from settings, typically 0.85)
            namespace: Pinecone namespace (default "companies")
            metadata_filter: Optional metadata filter dict
        
        Returns:
            List of matches above threshold with id, score, and metadata
        """
        index = self.get_index()
        threshold = threshold or settings.company_similarity_threshold
        
        # Build query parameters
        query_params = {
            "vector": embedding,
            "top_k": top_k,
            "include_metadata": True,
            "namespace": namespace
        }
        
        # Add metadata filter if provided
        if metadata_filter:
            query_params["filter"] = metadata_filter
        
        # Execute query
        results = index.query(**query_params)
        
        # Filter by threshold
        filtered_matches = [
            match for match in results.matches
            if match.score >= threshold
        ]
        
        return filtered_matches
    
    def delete_company_embedding(self, company_id: str, namespace: str = "companies"):
        """
        Delete company embedding from Pinecone.
        
        Args:
            company_id: Company UUID
            namespace: Pinecone namespace (default "companies")
        """
        index = self.get_index()
        index.delete(
            ids=[f"company_{company_id}"],
            namespace=namespace
        )
    
    def get_index_stats(self):
        """Get Pinecone index statistics."""
        index = self.get_index()
        return index.describe_index_stats()


# Global Pinecone client instance
pinecone_client = PineconeClient()
