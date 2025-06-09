from langchain_community.embeddings import HuggingFaceEmbeddings

def get_embedding_model(model_name=None):
    """Get improved embedding model for better semantic understanding"""
    
    # Default to a more powerful model if none specified
    if not model_name:
        model_name = "sentence-transformers/all-mpnet-base-v2"  # Better than all-MiniLM-L6-v2
    
    # Initialize embeddings with better parameters
    embedding_model = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}  # Normalize for better similarity comparison
    )
    
    return embedding_model

def create_hybrid_retriever(retriever):
    """Create a hybrid retrieval approach (future enhancement)"""
    # This is a placeholder for future implementation
    # Could combine vector search with keyword-based approaches
    return retriever