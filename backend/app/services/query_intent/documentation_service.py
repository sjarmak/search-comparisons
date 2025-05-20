"""
Documentation Service module for query intent service.

This module provides functionality to manage and search through documentation
for query transformation rules and examples.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import numpy as np
from sentence_transformers import SentenceTransformer

# Configure logger for this module
logger = logging.getLogger(__name__)

class DocumentationService:
    """
    Service for managing and searching documentation.
    
    This service handles loading, indexing, and searching through documentation
    for query transformation rules and examples.
    """
    
    _instance = None
    _model_loaded = False
    _vector_store_loaded = False
    
    def __new__(cls, *args, **kwargs):
        """
        Create a new instance of DocumentationService or return the existing one.
        
        Returns:
            DocumentationService: The singleton instance
        """
        if cls._instance is None:
            cls._instance = super(DocumentationService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, docs_dir: Optional[str] = None) -> None:
        """
        Initialize the documentation service.
        
        Args:
            docs_dir: Optional directory containing documentation files
        """
        if not hasattr(self, 'initialized'):
            self.docs_dir = docs_dir or os.path.join(
                os.path.dirname(__file__),
                'docs'
            )
            self.model = None
            self.embeddings = None
            self.docs = []
            self.initialized = True
            logger.info(f"Using docs directory: {self.docs_dir}")
    
    async def _ensure_model_loaded(self) -> None:
        """
        Ensure the sentence transformer model is loaded.
        This implements lazy loading to reduce memory usage.
        """
        if not self._model_loaded:
            try:
                logger.info("Loading sentence transformer model...")
                self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
                self._model_loaded = True
                logger.info("Sentence transformer model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading sentence transformer model: {str(e)}")
                raise
    
    async def _ensure_vector_store_loaded(self) -> None:
        """
        Ensure the vector store is loaded.
        This implements lazy loading to reduce memory usage.
        """
        if not self._vector_store_loaded:
            try:
                await self._ensure_model_loaded()
                logger.info("Loading existing vector store")
                vector_store_path = os.path.join(self.docs_dir, 'embeddings.npy')
                if os.path.exists(vector_store_path):
                    self.embeddings = np.load(vector_store_path)
                    with open(os.path.join(self.docs_dir, 'docs.json'), 'r') as f:
                        self.docs = json.load(f)
                else:
                    await self._create_vector_store()
                self._vector_store_loaded = True
                logger.info("Vector store loaded successfully")
            except Exception as e:
                logger.error(f"Error loading vector store: {str(e)}")
                raise
    
    async def search_docs(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search documentation for relevant examples and rules.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of relevant documentation entries
        """
        await self._ensure_vector_store_loaded()
        
        # Encode query
        query_vector = self.model.encode([query])[0]
        
        # Calculate cosine similarity
        similarities = np.dot(self.embeddings, query_vector) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_vector)
        )
        
        # Get top k results
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Return results
        results = []
        for idx in top_indices:
            if idx < len(self.docs):
                doc = self.docs[idx]
                doc['score'] = float(similarities[idx])
                results.append(doc)
        
        return results
    
    async def _create_vector_store(self) -> None:
        """
        Create a new vector store from documentation files.
        """
        try:
            # Load and process documentation files
            docs = []
            for file in Path(self.docs_dir).glob('*.md'):
                with open(file, 'r') as f:
                    content = f.read()
                    docs.append({
                        'content': content,
                        'source': file.name
                    })
            
            # Encode documents
            texts = [doc['content'] for doc in docs]
            self.embeddings = self.model.encode(texts)
            
            # Save embeddings and docs
            np.save(os.path.join(self.docs_dir, 'embeddings.npy'), self.embeddings)
            with open(os.path.join(self.docs_dir, 'docs.json'), 'w') as f:
                json.dump(docs, f)
            
            self.docs = docs
            logger.info(f"Created vector store with {len(docs)} documents")
            
        except Exception as e:
            logger.error(f"Error creating vector store: {str(e)}")
            raise 