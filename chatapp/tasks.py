from background_task import background
import logging
import time
import os
from django.utils.timezone import now

# Set up logging
logger = logging.getLogger(__name__)

@background(schedule=5)
def process_document_background(document_id):
    """Process a document in the background to prevent request timeouts."""
    # We need to import models here to avoid circular imports
    from .models import Document
    from .colab_client import ColabClient
    
    logger.info(f"Background task: Starting document processing for document {document_id}")
    
    try:
        # Get the document
        document = Document.objects.get(id=document_id)
        document.processing_status = "Processing in background..."
        document.save()
        
        # Get the Colab API URL
        api_url = os.environ.get('COLAB_API_URL', 'http://localhost:5000')
        colab_client = ColabClient(api_url=api_url)
        
        # Check if API is available
        is_healthy = colab_client._check_health_simple()
        if not is_healthy:
            document.processing_error = "API service is unavailable"
            document.processing_status = "Failed - API unavailable"
            document.save()
            logger.error(f"Background task: API unavailable for document {document_id}")
            return
            
        # Get content
        content = document.content
        if not content and document.file:
            # Read file content
            from .file_processor import extract_content_from_file
            try:
                content = extract_content_from_file(document.file)
                document.content = content[:1000000]  # Limit content size if needed
                document.save()
            except Exception as e:
                document.processing_error = f"Could not read file: {str(e)}"
                document.processing_status = "Failed - File read error"
                document.save()
                logger.error(f"Background task: File read error for document {document_id}: {str(e)}")
                return
        
        if not content:
            document.processing_error = "No content found in document"
            document.processing_status = "Failed - Empty content"
            document.save()
            logger.error(f"Background task: No content for document {document_id}")
            return
            
        # Process document with Colab API
        try:
            logger.info(f"Processing document {document_id} with {len(content)} characters")
            document.processing_status = "Processing with API..."
            document.save()
            
            # Process the document in chunks if needed
            chunks_created = colab_client.process_document(
                document_id=str(document.id),
                content=content,
                user_id=str(document.uploaded_by.id)
            )
            
            # Update document status
            document.is_processed = True
            document.chunks = chunks_created
            document.processing_status = "Complete"
            document.last_processed = now()
            document.save()
            
            logger.info(f"Document {document_id} processed successfully with {chunks_created} chunks")
            
        except Exception as e:
            document.processing_error = str(e)
            document.processing_status = f"Failed - API error: {str(e)[:100]}"
            document.is_processed = False
            document.save()
            logger.error(f"Error processing document {document_id}: {str(e)}")
            
    except Document.DoesNotExist:
        logger.error(f"Background task: Document {document_id} not found")
    
    except Exception as e:
        logger.error(f"Background task: Unexpected error: {str(e)}")
        try:
            document = Document.objects.get(id=document_id)
            document.processing_status = f"Failed - Unexpected error: {str(e)[:100]}"
            document.save()
        except:
            pass

@background(schedule=30)
def check_document_completion(document_id):
    """Final check for document processing status after giving API time to finish."""
    from .models import Document
    from .colab_client import ColabClient
    import os
    
    try:
        document = Document.objects.get(id=document_id)
        
        # Only check documents that don't have chunks yet
        if document.chunks == 0 and document.processing_status != "Failed":
            logger.info(f"Final check for document {document_id}")
            
            # Get the Colab API URL
            api_url = os.environ.get('COLAB_API_URL', 'http://localhost:5000')
            colab_client = ColabClient(api_url=api_url)
            
            # Check status
            status_info = colab_client.check_document_status(
                document_id=str(document.id),
                user_id=str(document.uploaded_by.id)
            )
            
            if status_info.get("status") in ["complete", "ready"]:
                chunks = status_info.get("chunks", 0)
                document.chunks = chunks
                document.is_processed = True
                document.processing_status = "Complete"
                document.save()
                logger.info(f"Final check: Document {document_id} has {chunks} chunks")
            
    except Exception as e:
        logger.error(f"Error in final document check: {str(e)}")