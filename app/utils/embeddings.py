"""Embedding generation utilities using sentence-transformers."""

from typing import List, Union, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generate embeddings for text using sentence-transformers.
    
    Uses the all-MiniLM-L6-v2 model which produces 384-dimensional embeddings
    optimized for semantic similarity tasks.
    """
    
    # Model configuration
    MODEL_NAME = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION = 384
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Name of the sentence-transformers model to use.
                       Defaults to all-MiniLM-L6-v2.
        """
        self.model_name = model_name or self.MODEL_NAME
        self._model = None
        logger.info(f"EmbeddingGenerator initialized with model: {self.model_name}")
    
    @property
    def model(self) -> SentenceTransformer:
        """
        Lazy-load the sentence transformer model.
        
        Returns:
            Loaded SentenceTransformer model
        """
        if self._model is None:
            try:
                logger.info(f"Loading sentence-transformers model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load model {self.model_name}: {e}")
                raise RuntimeError(f"Failed to load embedding model: {e}")
        return self._model
    
    def generate_embedding(
        self,
        text: str,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Generate embedding for a single text string.
        
        Args:
            text: Input text to encode
            normalize: Whether to normalize the embedding (default True)
        
        Returns:
            Numpy array of shape (384,) containing the embedding
        
        Raises:
            ValueError: If text is empty
            RuntimeError: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            # Encode the text
            embedding = self.model.encode(
                text,
                normalize_embeddings=normalize,
                show_progress_bar=False
            )
            
            # Ensure correct shape
            if embedding.shape != (self.EMBEDDING_DIMENSION,):
                logger.warning(
                    f"Unexpected embedding shape: {embedding.shape}, "
                    f"expected ({self.EMBEDDING_DIMENSION},)"
                )
            
            return embedding
        
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")
    
    def generate_embeddings(
        self,
        texts: List[str],
        normalize: bool = True,
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Generate embeddings for multiple text strings.
        
        Args:
            texts: List of input texts to encode
            normalize: Whether to normalize the embeddings (default True)
            batch_size: Batch size for encoding (default 32)
        
        Returns:
            Numpy array of shape (len(texts), 384) containing the embeddings
        
        Raises:
            ValueError: If texts list is empty
            RuntimeError: If embedding generation fails
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")
        
        # Filter out empty strings
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise ValueError("All texts are empty")
        
        try:
            # Encode all texts
            embeddings = self.model.encode(
                valid_texts,
                normalize_embeddings=normalize,
                batch_size=batch_size,
                show_progress_bar=False
            )
            
            # Ensure correct shape
            expected_shape = (len(valid_texts), self.EMBEDDING_DIMENSION)
            if embeddings.shape != expected_shape:
                logger.warning(
                    f"Unexpected embeddings shape: {embeddings.shape}, "
                    f"expected {expected_shape}"
                )
            
            return embeddings
        
        except Exception as e:
            logger.error(f"Failed to generate embeddings for {len(texts)} texts: {e}")
            raise RuntimeError(f"Batch embedding generation failed: {e}")
    
    def generate_company_embedding(
        self,
        company_name: str,
        name_variants: Optional[List[str]] = None
    ) -> np.ndarray:
        """
        Generate embedding for a company name, optionally incorporating variants.
        
        If name variants are provided, generates embeddings for all variants
        and returns the mean embedding.
        
        Args:
            company_name: Primary company name
            name_variants: Optional list of alternative company names
        
        Returns:
            Numpy array of shape (384,) containing the company embedding
        
        Raises:
            ValueError: If company_name is empty
            RuntimeError: If embedding generation fails
        """
        if not company_name or not company_name.strip():
            raise ValueError("Company name cannot be empty")
        
        try:
            # If no variants, just encode the primary name
            if not name_variants:
                return self.generate_embedding(company_name)
            
            # Combine primary name with variants
            all_names = [company_name] + [v for v in name_variants if v and v.strip()]
            
            # Generate embeddings for all names
            embeddings = self.generate_embeddings(all_names)
            
            # Return mean embedding
            mean_embedding = np.mean(embeddings, axis=0)
            
            # Normalize the mean embedding
            norm = np.linalg.norm(mean_embedding)
            if norm > 0:
                mean_embedding = mean_embedding / norm
            
            return mean_embedding
        
        except Exception as e:
            logger.error(f"Failed to generate company embedding for '{company_name}': {e}")
            raise RuntimeError(f"Company embedding generation failed: {e}")
    
    def calculate_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
        
        Returns:
            Cosine similarity score between -1 and 1
        
        Raises:
            ValueError: If embeddings have different shapes
        """
        if embedding1.shape != embedding2.shape:
            raise ValueError(
                f"Embedding shapes must match: {embedding1.shape} vs {embedding2.shape}"
            )
        
        # Calculate cosine similarity
        # If embeddings are normalized, this is just the dot product
        similarity = np.dot(embedding1, embedding2)
        
        return float(similarity)


# Global singleton instance
_embedding_generator = None


def get_embedding_generator(model_name: Optional[str] = None) -> EmbeddingGenerator:
    """
    Get or create the global embedding generator instance.
    
    Args:
        model_name: Optional model name (only used on first call)
    
    Returns:
        EmbeddingGenerator instance
    """
    global _embedding_generator
    
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator(model_name)
    
    return _embedding_generator
