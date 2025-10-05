#!/usr/bin/env python3
"""
RAG (Retrieval-Augmented Generation) System for Pittsburgh Events Data
基于匹兹堡活动数据的检索增强生成系统

This system processes data from two main folders:
1. Event_Pittsburgh_CMU_data - Contains event calendars and campus events
2. Food_related_events_data - Contains food festival and restaurant information

The system supports both Markdown (.md) and CSV (.csv) files.
"""

import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import json
import re
from pathlib import Path
import logging

# Core RAG components
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.document_loaders import TextLoader, CSVLoader
from langchain.schema import Document

# Alternative: Use local models for privacy
try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    LOCAL_MODELS_AVAILABLE = True
except ImportError:
    LOCAL_MODELS_AVAILABLE = False
    print("Warning: Transformers not available. Will use OpenAI API.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PittsburghEventsRAG:
    """
    RAG system for Pittsburgh events data
    """
    
    def __init__(self, 
                 data_path: str = ".",
                 use_local_models: bool = False,
                 openai_api_key: Optional[str] = None):
        """
        Initialize the RAG system
        
        Args:
            data_path: Path to the data directory
            use_local_models: Whether to use local models instead of OpenAI
            openai_api_key: OpenAI API key (required if not using local models)
        """
        self.data_path = Path(data_path)
        self.use_local_models = use_local_models
        self.documents = []
        self.vectorstore = None
        self.retrieval_chain = None
        
        # Initialize components
        self._setup_embeddings()
        self._setup_llm(openai_api_key)
        self._setup_text_splitter()
        
    def _setup_embeddings(self):
        """Setup embedding model"""
        if self.use_local_models and LOCAL_MODELS_AVAILABLE:
            # Use local embedding model
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': 'cpu'}
            )
            logger.info(f"Using local embedding model: {model_name}")
        else:
            # Use OpenAI embeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            logger.info("Using OpenAI-compatible embeddings")
    
    def _setup_llm(self, openai_api_key: Optional[str]):
        """Setup language model"""
        if self.use_local_models and LOCAL_MODELS_AVAILABLE:
            # Use local model (simplified - in practice you'd use a proper local LLM)
            self.llm = None  # Will implement local LLM integration
            logger.info("Using local language model")
        else:
            if not openai_api_key:
                raise ValueError("OpenAI API key required when not using local models")
            os.environ["OPENAI_API_KEY"] = openai_api_key
            self.llm = OpenAI(temperature=0.7)
            logger.info("Using OpenAI language model")
    
    def _setup_text_splitter(self):
        """Setup text splitter for chunking documents"""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def load_data(self):
        """Load all data from the two main directories"""
        logger.info("Loading data from directories...")
        
        # Load from Event_Pittsburgh_CMU_data
        event_data_path = self.data_path / "Event_Pittsburgh_CMU_data"
        if event_data_path.exists():
            self._load_directory(event_data_path, "Event_Data")
        
        # Load from Food_related_events_data
        food_data_path = self.data_path / "Food_related_events_data"
        if food_data_path.exists():
            self._load_directory(food_data_path, "Food_Events")
        
        logger.info(f"Loaded {len(self.documents)} documents")
    
    def _load_directory(self, directory_path: Path, category: str):
        """Load all files from a directory"""
        for file_path in directory_path.rglob("*"):
            if file_path.is_file():
                try:
                    if file_path.suffix == '.md':
                        self._load_markdown_file(file_path, category)
                    elif file_path.suffix == '.csv':
                        self._load_csv_file(file_path, category)
                except Exception as e:
                    logger.warning(f"Failed to load {file_path}: {e}")
    
    def _load_markdown_file(self, file_path: Path, category: str):
        """Load a markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create document with metadata
            doc = Document(
                page_content=content,
                metadata={
                    "source": str(file_path),
                    "category": category,
                    "file_type": "markdown",
                    "filename": file_path.name,
                    "subdirectory": file_path.parent.name
                }
            )
            self.documents.append(doc)
            logger.info(f"Loaded markdown file: {file_path}")
            
        except Exception as e:
            logger.error(f"Error loading markdown file {file_path}: {e}")
    
    def _load_csv_file(self, file_path: Path, category: str):
        """Load a CSV file"""
        try:
            df = pd.read_csv(file_path)
            
            # Convert CSV to text format
            for index, row in df.iterrows():
                # Create a text representation of the row
                text_parts = []
                for col, value in row.items():
                    if pd.notna(value):
                        text_parts.append(f"{col}: {value}")
                
                content = "\n".join(text_parts)
                
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": str(file_path),
                        "category": category,
                        "file_type": "csv",
                        "filename": file_path.name,
                        "subdirectory": file_path.parent.name,
                        "row_index": index
                    }
                )
                self.documents.append(doc)
            
            logger.info(f"Loaded CSV file: {file_path} ({len(df)} rows)")
            
        except Exception as e:
            logger.error(f"Error loading CSV file {file_path}: {e}")
    
    def build_vectorstore(self):
        """Build the vector store from loaded documents"""
        if not self.documents:
            raise ValueError("No documents loaded. Call load_data() first.")
        
        logger.info("Building vector store...")
        
        # Split documents into chunks
        texts = self.text_splitter.split_documents(self.documents)
        logger.info(f"Split into {len(texts)} text chunks")
        
        # Create vector store
        self.vectorstore = FAISS.from_documents(texts, self.embeddings)
        logger.info("Vector store built successfully")
    
    def setup_retrieval_chain(self):
        """Setup the retrieval chain"""
        if not self.vectorstore:
            raise ValueError("Vector store not built. Call build_vectorstore() first.")
        
        if self.llm:
            self.retrieval_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 5}),
                return_source_documents=True
            )
            logger.info("Retrieval chain setup complete")
        else:
            logger.warning("No LLM available. Only retrieval will work.")
    
    def query(self, question: str, return_sources: bool = True) -> Dict[str, Any]:
        """
        Query the RAG system
        
        Args:
            question: The question to ask
            return_sources: Whether to return source documents
            
        Returns:
            Dictionary containing answer and optionally sources
        """
        if not self.vectorstore:
            raise ValueError("Vector store not built. Call build_vectorstore() first.")
        
        # Get relevant documents
        relevant_docs = self.vectorstore.similarity_search(question, k=5)
        
        result = {
            "question": question,
            "relevant_documents": relevant_docs if return_sources else None
        }
        
        # Generate answer if LLM is available
        if self.retrieval_chain:
            try:
                response = self.retrieval_chain({"query": question})
                result["answer"] = response["result"]
                if return_sources:
                    result["source_documents"] = response["source_documents"]
            except Exception as e:
                logger.error(f"Error generating answer: {e}")
                result["answer"] = "Sorry, I couldn't generate an answer. Please check the relevant documents."
        else:
            # Return context from relevant documents
            context = "\n\n".join([doc.page_content for doc in relevant_docs])
            print(context)
            result["answer"] = f"Based on the available documents, here's what I found:\n\n{context}"
        
        return result
    
    def get_event_summary(self) -> Dict[str, Any]:
        """Get a summary of all events in the system"""
        if not self.documents:
            return {"error": "No documents loaded"}
        
        summary = {
            "total_documents": len(self.documents),
            "categories": {},
            "file_types": {},
            "events_by_category": {}
        }
        
        for doc in self.documents:
            category = doc.metadata.get("category", "Unknown")
            file_type = doc.metadata.get("file_type", "Unknown")
            subdir = doc.metadata.get("subdirectory", "Unknown")
            
            # Count by category
            summary["categories"][category] = summary["categories"].get(category, 0) + 1
            
            # Count by file type
            summary["file_types"][file_type] = summary["file_types"].get(file_type, 0) + 1
            
            # Count events by subdirectory
            if category not in summary["events_by_category"]:
                summary["events_by_category"][category] = {}
            summary["events_by_category"][category][subdir] = summary["events_by_category"][category].get(subdir, 0) + 1
        
        return summary
    
    def save_vectorstore(self, path: str):
        """Save the vector store to disk"""
        if self.vectorstore:
            self.vectorstore.save_local(path)
            logger.info(f"Vector store saved to {path}")
        else:
            raise ValueError("No vector store to save")
    
    def load_vectorstore(self, path: str):
        """Load a vector store from disk"""
        self.vectorstore = FAISS.load_local(path, self.embeddings)
        logger.info(f"Vector store loaded from {path}")


def main():
    """Main function to demonstrate the RAG system"""
    
    # Initialize the RAG system
    rag = PittsburghEventsRAG(
        data_path=".",
        use_local_models=True  # Set to False if you want to use OpenAI
    )
    
    # Load data
    print("Loading data...")
    rag.load_data()
    
    # Build vector store
    print("Building vector store...")
    rag.build_vectorstore()
    
    # Setup retrieval chain (if using OpenAI)
    # rag.setup_retrieval_chain()
    
    # Get summary
    summary = rag.get_event_summary()
    print("\n=== Data Summary ===")
    print(f"Total documents: {summary['total_documents']}")
    print(f"Categories: {summary['categories']}")
    print(f"File types: {summary['file_types']}")
    
    # Example queries
    example_questions = [
        "What food festivals are available in Pittsburgh?",
        "Tell me about CMU campus events",
        "What activities are available at the Banana Split Festival?",
        "When is Pittsburgh Restaurant Week?",
        "What entertainment is available at Little Italy Days?"
    ]
    
    print("\n=== Example Queries ===")
    for question in example_questions:
        print(f"\nQ: {question}")
        result = rag.query(question)
        print(f"A: {result['answer'][:200]}...")
        if result['relevant_documents']:
            print(f"Sources: {len(result['relevant_documents'])} documents")
    
    # Save vector store for future use
    rag.save_vectorstore("pittsburgh_events_vectorstore")


if __name__ == "__main__":
    main()
