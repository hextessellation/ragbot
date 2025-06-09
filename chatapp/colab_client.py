import requests
import logging
import time
import random
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

class ColabClient:
    def __init__(self, api_url: str):
        """
        Initialize the Colab client.
        
        Args:
            api_url: The public URL of your Colab notebook Flask API.
        """
        self.api_url = api_url.rstrip('/')
        self.max_retries = 3
        self.base_retry_delay = 2  # seconds
        logger.info(f"ColabClient initialized with API URL: {self.api_url}")
    
    def check_health(self) -> tuple:
        """
        Check if the API is healthy.
        
        Returns:
            Tuple of (is_healthy, model_info)
        """
        try:
            result = self._make_api_request(
                endpoint="healthcheck",
                payload={},
                method='get',
                timeout=5
            )
            
            is_healthy = result.get("status") == "ok"
            model_info = result.get("model", "unknown")
            
            return is_healthy, model_info
        
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False, str(e)
    
    def _make_api_request(self, endpoint: str, payload: dict, timeout: int = 30, method: str = 'post', params: dict = None) -> dict:
        """
        Make an API request with retry logic.
        
        Args:
            endpoint: API endpoint to call (without leading slash)
            payload: Request payload
            timeout: Request timeout in seconds
            method: HTTP method (get or post)
            params: URL parameters for GET requests
        
        Returns:
            API response as dictionary
        """
        url = f"{self.api_url}/{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                # Make the request
                if method.lower() == 'post':
                    response = requests.post(url, json=payload, timeout=timeout)
                else:
                    # Use params for GET requests if provided, otherwise use payload as params
                    response = requests.get(url, params=params if params else payload, timeout=timeout)
                
                # Log the request for debugging
                logger.debug(f"{method.upper()} {url} - Status: {response.status_code}")
                
                if response.status_code == 200:
                    return response.json()
                
                # Non-200 responses
                logger.warning(f"API returned non-200 status: {response.status_code} - {response.text}")
                response.raise_for_status()
            
            except requests.exceptions.Timeout:
                logger.warning(f"Request timed out (attempt {attempt+1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    retry_delay = self.base_retry_delay * (attempt + 1) + random.uniform(0, 1)
                    logger.info(f"Retrying in {retry_delay:.1f} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Maximum retries reached for timeout")
                    raise
            
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error: {str(e)} (attempt {attempt+1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    retry_delay = self.base_retry_delay * (attempt + 1) + random.uniform(0, 1)
                    logger.info(f"Retrying in {retry_delay:.1f} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Maximum retries reached for connection error")
                    raise
            
            except Exception as e:
                logger.error(f"Unexpected error making API request: {str(e)}")
                raise
        
        # If we get here, all retries failed (this should not be reachable with current logic)
        raise Exception(f"Failed to get successful response from {url} after {self.max_retries} attempts")
    
    def process_document(self, document_id: str, content: str, user_id: str) -> int:
        """
        Process a document through the Colab API.
        
        Args:
            document_id: The document ID
            content: The document content
            user_id: The user ID
            
        Returns:
            The number of chunks created (will be positive if successful)
        """
        try:
            # For large documents, process in chunks to avoid timeout
            max_chunk_size = 20000  # Process 20K characters at once
            chunks_created = 0
            
            logger.info(f"Processing document {document_id} for user {user_id}")
            
            # If content is small enough, process in one request
            if len(content) <= max_chunk_size:
                logger.debug(f"Processing small document: {len(content)} characters")
                
                payload = {
                    "text": content,
                    "document_id": document_id,
                    "user_id": user_id
                }
                
                # Use a longer timeout for document processing
                result = self._make_api_request(
                    endpoint="process_document",
                    payload=payload,
                    timeout=120  # 2 minutes timeout for processing
                )
                
                # Handle the response
                if result.get("status") == "processing_started":
                    # If async processing started, check status after a delay
                    logger.info(f"Document processing started in background. Will check status.")
                    time.sleep(10)  # Wait for processing
                    
                    # Check document status
                    status_result = self._make_api_request(
                        endpoint="document_status",
                        payload={},
                        method="get",
                        params={
                            "document_id": document_id,
                            "user_id": user_id
                        },
                        timeout=10
                    )
                    
                    if status_result.get("status") == "ready":
                        # Get chunk count from status
                        chunks_created = status_result.get("chunks", 0)
                    else:
                        # If not ready yet, estimate 1 chunk per 1000 characters
                        chunks_created = max(1, len(content) // 1000)
                        
                else:
                    # If chunks were returned directly
                    chunks_created = result.get("chunks", 0)
                    
            else:
                # For large content, process in chunks
                logger.info(f"Processing large document of {len(content)} characters in chunks")
                
                # Process multiple chunks
                for i in range(0, len(content), max_chunk_size):
                    chunk = content[i:i + max_chunk_size]
                    
                    payload = {
                        "text": chunk,
                        "document_id": document_id,
                        "user_id": user_id,
                        "chunk_number": i // max_chunk_size,
                        "is_partial": True
                    }
                    
                    # Process this chunk
                    result = self._make_api_request(
                        endpoint="process_document",
                        payload=payload,
                        timeout=120
                    )
                    
                    # Track chunks created
                    chunk_count = result.get("chunks", 0)
                    chunks_created += chunk_count
                    
                    logger.info(f"Processed chunk {i // max_chunk_size + 1}, created {chunk_count} chunks")
                    
                    # Small delay between chunks
                    if i + max_chunk_size < len(content):
                        time.sleep(2)
                
                # Finalize the document
                payload = {
                    "document_id": document_id,
                    "user_id": user_id,
                    "finalize": True
                }
                
                self._make_api_request(
                    endpoint="finalize_document",
                    payload=payload,
                    timeout=30
                )
            
            logger.info(f"Document {document_id} processed with {chunks_created} chunks")
            return chunks_created
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            raise Exception(f"Failed to process document: {str(e)}")

    def generate_response(self, query: str, document_id: str, user_id: str, conversation_history=None) -> str:
        """Generate a response using the Colab-hosted LLM."""
        try:
            # Check API availability first
            if not self._check_health_simple():
                return "The Colab service is currently unavailable. Please try again later."
            
            payload = {
                "query": query,
                "document_id": document_id,
                "user_id": user_id
            }
            
            if conversation_history:
                payload["conversation_history"] = conversation_history
            
            logger.info(f"Generating response for query on document {document_id}")
            
            result = self._make_api_request(
                endpoint="generate",
                payload=payload,
                timeout=45
            )
            
            response_text = result.get("response", "Sorry, I couldn't generate a proper response.")
            return response_text
            
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            logger.error(f"Request error: {error_message}")
            
            if "404" in error_message:
                if "Document not processed yet" in error_message or "vectorstore not found" in error_message:
                    return "This document hasn't been processed yet in the current session. Please go back to the Documents page and click 'Reprocess' on this document, then try again."
                else:
                    return "The API endpoint was not found. The Colab notebook might need to be restarted."
            elif "Connection" in error_message:
                return "Could not connect to the API server. Please check that your Colab notebook is running."
            else:
                return f"Sorry, an error occurred while contacting the API: {error_message}"
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Sorry, an error occurred: {str(e)}"
    
    def _check_health_simple(self) -> bool:
        """Simple health check that just returns True/False"""
        try:
            response = requests.get(f"{self.api_url}/healthcheck", timeout=5)
            return response.status_code == 200
        except:
            return False


def detect_query_type(query):
    """Detect query type to customize retrieval and prompting"""
    query = query.lower()
    
    if any(term in query for term in ["summarize", "summary", "summarization", "overview", 
                                       "key points", "main ideas", "brief me"]):
        return "summarization"
    
    if any(term in query for term in ["compare", "difference", "versus", "similarities"]):
        return "comparison"
        
    if any(term in query for term in ["list", "enumerate", "what are"]):
        return "listing"
    
    return "default"


def enhance_query(original_query, query_type):
    """Enhance the original query for better retrieval results"""
    if query_type == "summarization":
        return "document summary main points key concepts important sections " + original_query
    
    if len(original_query.split()) < 4:
        # Expand short queries to improve retrieval
        return f"information about {original_query} context details explanation"
    
    return original_query


def format_context_for_llm(retrieved_docs, query_type):
    """Format retrieved documents for optimal LLM comprehension"""
    if not retrieved_docs:
        return "No relevant information found in the document."
    
    if query_type == "summarization":
        # For summarization, organize by document position
        beginning_chunks = [doc for doc in retrieved_docs if doc.metadata.get("position") == "beginning"]
        middle_chunks = [doc for doc in retrieved_docs if doc.metadata.get("position") == "middle"]
        end_chunks = [doc for doc in retrieved_docs if doc.metadata.get("position") == "end"]
        
        formatted_context = "DOCUMENT SECTIONS:\n\n"
        
        if beginning_chunks:
            formatted_context += "--- BEGINNING SECTIONS ---\n\n"
            for doc in beginning_chunks:
                formatted_context += f"{doc.page_content}\n\n"
        
        if middle_chunks:
            formatted_context += "--- MIDDLE SECTIONS ---\n\n"
            for doc in middle_chunks:
                formatted_context += f"{doc.page_content}\n\n"
                
        if end_chunks:
            formatted_context += "--- END SECTIONS ---\n\n"
            for doc in end_chunks:
                formatted_context += f"{doc.page_content}\n\n"
                
        return formatted_context
    
    else:
        # For specific questions, order by relevance but with clear separators
        formatted_context = ""
        
        for i, doc in enumerate(retrieved_docs):
            chunk_id = doc.metadata.get("chunk_id", i)
            header = doc.metadata.get("potential_header", "")
            
            formatted_context += f"\n\n--- DOCUMENT SECTION {i+1} "
            if header:
                formatted_context += f"({header}) "
            formatted_context += f"---\n\n{doc.page_content}"
            
        return formatted_context


def get_enhanced_prompt(query, context, query_type, conversation_history=None):
    """Create specialized prompts for different query types"""
    history_context = ""
    if conversation_history and len(conversation_history) > 0:
        history_context = "\n\nRecent conversation history:\n"
        for msg in conversation_history[-6:]:  # Include last 3 exchanges (6 messages)
            role = "User" if msg["role"] == "user" else "Assistant"
            history_context += f"{role}: {msg['content']}\n"
        
    if query_type == "summarization":
        return f"""You are an expert document analyst. Please provide a comprehensive summary of the following document sections.
Be thorough and make sure to include key points from all sections shown below.

{context}

{history_context}

Create a well-structured summary that covers the main topics and important details from the document.
If information appears incomplete or missing from certain sections, acknowledge that in your summary.
Organize your summary by main topics and include specific details from the text.

USER QUERY: {query}"""
    
    elif query_type == "comparison":
        return f"""You are a helpful assistant. Based ONLY on the information provided in these document excerpts, 
compare the elements requested in the user's question.

{context}

{history_context}

If the answer isn't contained in the excerpts, say "I don't have enough information to make this comparison."
Be specific and cite details from the document sections where possible.

USER QUERY: {query}"""
    
    else:
        return f"""You are a helpful assistant. Answer the following question based ONLY on the information provided in these document excerpts.
If the answer isn't contained in the excerpts, say "I don't have enough information to answer that question."

{context}

{history_context}

Focus on being accurate and providing specific details from the text rather than general knowledge.

USER QUERY: {query}"""