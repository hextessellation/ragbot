import chromadb
from chromadb.config import Settings
import os
import uuid
import logging
from nltk.tokenize import sent_tokenize
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_directory="vectordb"):
        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with persistent storage
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(allow_reset=True)
        )
        
        # Get or create collection with proper configuration
        self.collection = self.client.get_or_create_collection(
            name="document_chunks",
            metadata={"hnsw:space": "cosine"}
        )

    def process_document(self, document_id: str, content: str, user_id: str, chunk_size: int = 5):
        """Process document into chunks and store in vector DB"""
        try:
            # Split document into sentences
            sentences = sent_tokenize(content)
            
            # Create chunks of sentences
            chunks = [' '.join(sentences[i:i+chunk_size]) 
                     for i in range(0, len(sentences), chunk_size)]
            
            # Generate metadata for each chunk
            metadatas = [{
                "document_id": document_id,
                "user_id": user_id,
                "chunk_index": i,
                "total_chunks": len(chunks)
            } for i in range(len(chunks))]
            
            # Create unique IDs for chunks
            ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
            
            # Add to collection
            self.collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            raise

    def query_chunks(self, query: str, user_id: str, n_results: int = 3):
        """Query similar chunks with user-specific filtering"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"user_id": user_id}
            )
            
            return {
                "documents": results["documents"][0],
                "metadatas": results["metadatas"][0],
                "distances": results["distances"][0]
            }
            
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            return None

def get_retriever(vectorstore, query_type="default"):
    """Get an enhanced retriever with better context selection strategies"""
    
    if query_type == "summarization":
        # For summarization, we want broader coverage of the document
        retriever = vectorstore.as_retriever(
            search_type="mmr",  # Maximum Marginal Relevance for diversity
            search_kwargs={
                "k": 8,  # More chunks for summarization
                "fetch_k": 12,  # Consider more candidates
                "lambda_mult": 0.6  # Favor diversity more
            }
        )
    else:
        # For specific questions, we want more focused but still diverse results
        retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 5,  # Retrieve enough context but not too much
                "fetch_k": 8,  # Consider several candidates
                "lambda_mult": 0.7  # Balance between relevance and diversity
            }
        )
    
    return retriever

def create_vectorstore(chunks, embedding_function, document_id, user_id):
    """Create vector store with improved configurations"""
    
    from langchain_community.vectorstores import Chroma
    
    # Create a vector store with more metadata and better search configuration
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_function,
        collection_name=f"user_{user_id}_doc_{document_id}",
        persist_directory="./chroma_db",
        collection_metadata={
            "document_id": str(document_id),
            "user_id": str(user_id),
            "chunk_count": len(chunks),
            "created_at": str(datetime.now())
        }
    )
    
    return vectorstore
