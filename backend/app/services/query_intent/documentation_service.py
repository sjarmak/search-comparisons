"""Service for handling ADS documentation retrieval and embedding."""

from typing import List, Dict, Any
import os
import json
from pathlib import Path
import logging
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

logger = logging.getLogger(__name__)

class DocumentationService:
    """Service for managing and retrieving ADS documentation."""
    
    def __init__(
        self,
        docs_dir: str = None,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize the documentation service.
        
        Args:
            docs_dir: Directory containing documentation files
            embedding_model: Name of the embedding model to use
        """
        # Set default docs directory if not provided
        if docs_dir is None:
            self.docs_dir = Path(__file__).parent / "docs"
        else:
            self.docs_dir = Path(docs_dir)
            
        logger.info(f"Using docs directory: {self.docs_dir}")
        
        # Ensure docs directory exists
        if not self.docs_dir.exists():
            logger.error(f"Docs directory does not exist: {self.docs_dir}")
            raise FileNotFoundError(f"Docs directory not found: {self.docs_dir}")
            
        self.embedding_model = embedding_model
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        self.vector_store = None
        self._initialize_vector_store()
    
    def _initialize_vector_store(self) -> None:
        """Initialize the vector store with documentation."""
        try:
            # Check if vector store exists
            if (self.docs_dir / "faiss_index").exists():
                logger.info("Loading existing vector store")
                self.vector_store = FAISS.load_local(
                    str(self.docs_dir / "faiss_index"),
                    self.embeddings,
                    allow_dangerous_deserialization=True  # We trust our own saved index
                )
            else:
                logger.info("Creating new vector store")
                self._create_vector_store()
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise
    
    def _create_vector_store(self) -> None:
        """Create a new vector store from documentation files."""
        try:
            # Load and split documentation
            docs = []
            for doc_file in self.docs_dir.glob("*.txt"):
                logger.info(f"Loading document: {doc_file}")
                loader = TextLoader(str(doc_file))
                docs.extend(loader.load())
            
            if not docs:
                raise ValueError("No documentation files found or loaded")
                
            logger.info(f"Loaded {len(docs)} documents")
            
            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            chunks = text_splitter.split_documents(docs)
            
            if not chunks:
                raise ValueError("No chunks were created from the documents")
                
            logger.info(f"Created {len(chunks)} chunks from documents")
            
            # Create vector store
            self.vector_store = FAISS.from_documents(chunks, self.embeddings)
            
            # Save vector store
            self.vector_store.save_local(str(self.docs_dir / "faiss_index"))
            logger.info("Vector store created and saved")
            
        except Exception as e:
            logger.error(f"Error creating vector store: {str(e)}")
            raise
    
    def retrieve_relevant_docs(self, query: str, k: int = 3) -> List[str]:
        """
        Retrieve relevant documentation chunks for a query.
        
        Args:
            query: The search query
            k: Number of chunks to retrieve
            
        Returns:
            List[str]: Retrieved documentation chunks
        """
        try:
            if not self.vector_store:
                raise ValueError("Vector store not initialized")
            
            # Retrieve relevant chunks
            docs = self.vector_store.similarity_search(query, k=k)
            return [doc.page_content for doc in docs]
            
        except Exception as e:
            logger.error(f"Error retrieving documentation: {str(e)}")
            raise
    
    def update_documentation(self) -> None:
        """Update the documentation and rebuild the vector store."""
        try:
            # Remove existing vector store
            if (self.docs_dir / "faiss_index").exists():
                import shutil
                shutil.rmtree(str(self.docs_dir / "faiss_index"))
            
            # Recreate vector store
            self._create_vector_store()
            logger.info("Documentation updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating documentation: {str(e)}")
            raise 