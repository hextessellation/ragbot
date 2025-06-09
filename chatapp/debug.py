def evaluate_chunk_quality(document_id, user_id):
    """Evaluate the quality of document chunking"""
    from .vector_store import get_vectorstore
    
    vectorstore = get_vectorstore(document_id, user_id)
    
    # Basic stats
    stats = {
        "total_chunks": 0,
        "avg_chunk_length": 0,
        "empty_chunks": 0,
        "short_chunks": 0  # Less than 100 chars
    }
    
    if not vectorstore:
        return {"error": "Vector store not found", "stats": stats}
    
    # Get all document chunks
    all_chunks = vectorstore.get()
    
    if not all_chunks["documents"]:
        return {"error": "No chunks found", "stats": stats}
    
    # Calculate stats
    total_length = 0
    chunk_count = len(all_chunks["documents"])
    empty_count = 0
    short_count = 0
    
    for chunk in all_chunks["documents"]:
        length = len(chunk)
        total_length += length
        
        if length == 0:
            empty_count += 1
        elif length < 100:
            short_count += 1
    
    stats["total_chunks"] = chunk_count
    stats["avg_chunk_length"] = total_length / chunk_count if chunk_count > 0 else 0
    stats["empty_chunks"] = empty_count
    stats["short_chunks"] = short_count
    
    return {
        "status": "success",
        "stats": stats,
        "sample_chunks": all_chunks["documents"][:3]  # Return first 3 chunks as samples
    }