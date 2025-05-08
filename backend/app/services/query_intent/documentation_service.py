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

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

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
            self.vector_store = None
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
                vector_store_path = os.path.join(self.docs_dir, 'vector_store.faiss')
                if os.path.exists(vector_store_path):
                    self.vector_store = faiss.read_index(vector_store_path)
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
        
        # Search vector store
        distances, indices = self.vector_store.search(
            np.array([query_vector]).astype('float32'),
            top_k
        )
        
        # Return results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.docs):
                doc = self.docs[idx]
                doc['score'] = float(distances[0][i])
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
            embeddings = self.model.encode(texts)
            
            # Create vector store
            dimension = embeddings.shape[1]
            self.vector_store = faiss.IndexFlatL2(dimension)
            self.vector_store.add(np.array(embeddings).astype('float32'))
            
            # Save vector store and docs
            faiss.write_index(self.vector_store, os.path.join(self.docs_dir, 'vector_store.faiss'))
            with open(os.path.join(self.docs_dir, 'docs.json'), 'w') as f:
                json.dump(docs, f)
            
            self.docs = docs
            logger.info(f"Created vector store with {len(docs)} documents")
            
        except Exception as e:
            logger.error(f"Error creating vector store: {str(e)}")
            raise 