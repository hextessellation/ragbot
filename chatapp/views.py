from django.contrib import messages  # Replace 'from pyexpat.errors import messages'
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .forms import CustomUserCreationForm, DocumentUploadForm
from django.contrib.auth.forms import AuthenticationForm
from .models import Document, ChatSession, ChatMessage
from .colab_client import ColabClient
import logging
import os
from django.http import JsonResponse
from django.utils.timezone import now
from django.conf import settings
from django.utils import timezone
import pytz

# Set up logging
logger = logging.getLogger(__name__)

# Initialize the Colab client with the URL from settings
COLAB_API_URL = settings.COLAB_API_URL
colab_client = ColabClient(api_url=COLAB_API_URL)

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Get the 'next' parameter or default to documents page
                next_url = request.POST.get('next', '/documents/')
                return redirect(next_url)
    else:
        form = AuthenticationForm()
    
    # Pass the 'next' parameter to the template
    return render(request, 'login.html', {
        'form': form,
        'next': request.GET.get('next', '/documents/')
    })


def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def chat_view(request, document_id):
    document = get_object_or_404(Document, id=document_id, uploaded_by=request.user)
    
    # Get the latest session or create a new one if none exists
    try:
        session = ChatSession.objects.filter(
            user=request.user, 
            document=document
        ).latest('created_at')  # Get the most recent session
        created = False
    except ChatSession.DoesNotExist:
        session = ChatSession.objects.create(
            user=request.user, 
            document=document
        )
        created = True
    
    # Fetch chat messages for this session
    chat_messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
    
    # Check if API is active
    api_active, _ = colab_client.check_health()
    
    # When generating response, include previous messages for context
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        if not message_text:
            return JsonResponse({'status': 'error', 'error': 'Message cannot be empty'})
        
        # Get or create session
        session_id = request.POST.get('session_id')
        if session_id:
            session = get_object_or_404(ChatSession, id=session_id, document=document)
        else:
            session = ChatSession.objects.create(document=document, user=request.user)
        
        # Save user message
        user_msg = ChatMessage.objects.create(
            session=session,
            is_user=True,
            message=message_text
        )
        
        # Get recent message history (last 3 exchanges = 6 messages)
        recent_messages = ChatMessage.objects.filter(session=session).order_by('-timestamp')[:6]
        conversation_history = []
        
        # Format the conversation history
        for msg in reversed(recent_messages):
            role = "user" if msg.is_user else "assistant"
            conversation_history.append({"role": role, "content": msg.message})
        
        try:
            # Generate AI response
            ai_response = colab_client.generate_response(
                query=message_text,
                document_id=str(document.id),
                user_id=str(request.user.id),
                conversation_history=conversation_history
            )
            
            # Save AI message
            ai_msg = ChatMessage.objects.create(
                session=session, 
                is_user=False, 
                message=ai_response
            )
            
            # Convert timestamps to IST for consistent display
            ist = pytz.timezone('Asia/Kolkata')
            user_timestamp = user_msg.timestamp.astimezone(ist)
            ai_timestamp = ai_msg.timestamp.astimezone(ist)
            
            # Return both messages for AJAX update
            return JsonResponse({
                'status': 'success',
                'user_message': {
                    'id': user_msg.id,
                    'content': user_msg.message,
                    'timestamp': user_timestamp.strftime('%b %d, %Y, %I:%M %p')
                },
                'ai_message': {
                    'id': ai_msg.id,
                    'content': ai_msg.message,
                    'timestamp': ai_timestamp.strftime('%b %d, %Y, %I:%M %p')
                }
            })
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            
            # Check if this is likely a retrieval error (empty context or vector store issue)
            error_message = str(e).lower()
            if "no document chunks" in error_message or "failed to load vector store" in error_message or "empty" in error_message:
                try:
                    # Auto-reprocess the document
                    logger.info(f"Attempting to auto-reprocess document {document.id}")
                    
                    # Get document content
                    content = document.content
                    if not content and document.file:
                        with open(document.file.path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    
                    # Process document using Colab API
                    chunks_created = colab_client.process_document(
                        document_id=str(document.id),
                        content=content,
                        user_id=str(request.user.id)
                    )
                    
                    # Update document metadata
                    document.is_processed = True
                    document.chunks = chunks_created
                    document.last_processed = now()
                    document.processing_error = None
                    document.save()
                    
                    # Try generating response again
                    ai_response = colab_client.generate_response(
                        query=message_text,
                        document_id=str(document.id),
                        user_id=str(request.user.id)
                    )
                    
                    # Save AI message with success note
                    ai_msg = ChatMessage.objects.create(
                        session=session, 
                        is_user=False, 
                        message=f"{ai_response}\n\n_Note: Document was automatically reprocessed to generate this response._"
                    )
                    
                    return JsonResponse({
                        'status': 'success',
                        'user_message': {
                            'id': user_msg.id,
                            'content': user_msg.message,
                            'timestamp': user_msg.timestamp.strftime('%b %d, %Y, %I:%M %p')
                        },
                        'ai_message': {
                            'id': ai_msg.id,
                            'content': ai_msg.message,
                            'timestamp': ai_msg.timestamp.strftime('%b %d, %Y, %I:%M %p')
                        },
                        'reprocessed': True
                    })
                    
                except Exception as reprocess_error:
                    logger.error(f"Auto-reprocessing failed: {str(reprocess_error)}")
                    ai_msg = ChatMessage.objects.create(
                        session=session, 
                        is_user=False, 
                        message=f"I'm sorry, but I couldn't answer your question. The document needed reprocessing, but the reprocessing failed. Error: {str(reprocess_error)}"
                    )
            else:
                # Create error message
                ai_msg = ChatMessage.objects.create(
                    session=session, 
                    is_user=False, 
                    message=f"I'm sorry, but I encountered an error trying to answer your question. Error: {str(e)}"
                )
            
            # Return error response
            return JsonResponse({
                'status': 'error',
                'user_message': {
                    'id': user_msg.id,
                    'content': user_msg.message,
                    'timestamp': user_msg.timestamp.strftime('%b %d, %Y, %I:%M %p')
                },
                'ai_message': {
                    'id': ai_msg.id,
                    'content': ai_msg.message,
                    'timestamp': ai_msg.timestamp.strftime('%b %d, %Y, %I:%M %p')
                }
            })
    
    # Rest of your view code for GET requests...
    # Handle regular form submission
    elif request.method == 'POST':
        user_message = request.POST.get('message', '')
        if user_message:
            # Save user's message
            user_msg = ChatMessage.objects.create(session=session, is_user=True, message=user_message)
            
            try:
                # Generate AI response using Colab-hosted model
                ai_response = colab_client.generate_response(
                    query=user_message,
                    document_id=str(document.id),
                    user_id=str(request.user.id)
                )
                
                # Save AI's response
                ai_msg = ChatMessage.objects.create(session=session, is_user=False, message=ai_response)
                
            except Exception as e:
                error_message = f"Error processing your request: {str(e)}"
                ChatMessage.objects.create(session=session, is_user=False, message=error_message)
                messages.error(request, "An error occurred while generating a response.")
                logger.error(f"Error in chat_view: {str(e)}")
            
            return redirect('chat', document_id=document_id)
    
    # Check API status
    try:
        api_active, _ = colab_client.check_health()
    except:
        api_active = False
    
    return render(request, 'chat.html', {
        'document': document,
        'chat_messages': chat_messages,  # Now this variable is defined
        'api_active': api_active
    })

@login_required
def document_list(request):
    """View function that displays all documents uploaded by the current user."""
    documents = Document.objects.filter(uploaded_by=request.user)
    return render(request, 'document_list.html', {'documents': documents})

@login_required
def upload_document(request):
    """View function for uploading a new document."""
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploaded_by = request.user
            document.save()
            
            try:
                # Extract content as before
                if document.file:
                    from .file_processor import extract_content_from_file
                    content = extract_content_from_file(document.file)
                    document.content = content
                    document.save()
                else:
                    content = document.content
                    
                # Start background processing and continue
                from .tasks import process_document_background
                process_document_background.delay(document.id)
                
                # Mark document as processing
                document.is_processed = False
                document.processing_status = "processing"
                document.save()
                
                messages.success(request, "Document uploaded and processing started. You can use it once processing completes.")
                return redirect('documents')
                
            except Exception as e:
                document.processing_error = str(e)
                document.is_processed = False
                document.save()
                messages.error(request, f"Error preparing document: {str(e)}")
                
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DocumentUploadForm()
        
    return render(request, 'upload_document.html', {'form': form})

@login_required
def api_status(request):
    """Check and display the status of the Colab API."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('documents')
    
    # Get the Colab API URL from settings
    from django.conf import settings
    api_url = settings.COLAB_API_URL
    
    # Initialize the client
    client = ColabClient(api_url)
    
    # Check health and get status
    is_healthy, model_info = client.check_health()
    
    # Check if a new URL was submitted
    if request.method == 'POST' and 'api_url' in request.POST:
        new_url = request.POST.get('api_url').strip()
        if new_url:
            # Update the URL in settings
            os.environ['COLAB_API_URL'] = new_url
            setattr(settings, 'COLAB_API_URL', new_url)
            messages.success(request, f"API URL updated to: {new_url}")
            
            # Initialize ColabClient globally with new URL
            global colab_client
            colab_client = ColabClient(api_url=new_url)
            
            # Test the new URL
            test_client = ColabClient(new_url)
            is_healthy, model_info = test_client.check_health()
            
            if is_healthy:
                messages.success(request, "Successfully connected to the new API URL.")
            else:
                messages.warning(request, f"Could not connect to the new API URL: {model_info}")
            
            # Redirect to refresh the page
            return redirect('api_status')
    
    context = {
        'is_healthy': is_healthy,
        'model_info': model_info,
        'api_url': api_url,
    }
    
    return render(request, 'api_status.html', context)

@login_required
def reprocess_document(request, document_id):
    """Reprocess an existing document."""
    document = get_object_or_404(Document, id=document_id, uploaded_by=request.user)
    
    try:
        # Get content
        if document.file:
            from .file_processor import extract_content_from_file
            try:
                content = extract_content_from_file(document.file)
                document.content = content
                document.save()
            except Exception as e:
                messages.error(request, f"Could not read file: {str(e)}")
                return redirect('documents')
        else:
            content = document.content
        
        if not content:
            messages.error(request, "No content found in the document.")
            return redirect('documents')
        
        # Check API health first
        api_healthy, _ = colab_client.check_health()
        if not api_healthy:
            messages.warning(request, "The AI service is currently unavailable. Please check the API status.")
            return redirect('documents')
        
        # Reset document status
        document.is_processed = False
        document.chunks = 0
        document.processing_error = None
        document.processing_status = "Starting reprocessing..."
        document.save()
        
        # Process document using Colab API
        try:
            chunks_created = colab_client.process_document(
                document_id=str(document.id),
                content=content,
                user_id=str(request.user.id)
            )
            
            # Update document status
            document.is_processed = True
            document.chunks = chunks_created
            document.processing_status = "Complete"
            document.last_processed = now()
            document.save()
            
            if chunks_created > 0:
                messages.success(request, f"Document reprocessed successfully! Created {chunks_created} chunks.")
            else:
                messages.warning(request, "Document processed but no chunks were created. This might indicate an issue.")
                
        except Exception as e:
            document.processing_error = str(e)
            document.processing_status = f"Failed: {str(e)}"
            document.save()
            messages.error(request, f"Error processing document: {str(e)}")
            
    except Exception as e:
        messages.error(request, f"Unexpected error: {str(e)}")
        
    return redirect('documents')

@login_required
def delete_document(request, document_id):
    """Delete a document and all its related chat sessions."""
    document = get_object_or_404(Document, id=document_id, uploaded_by=request.user)
    
    if request.method == 'POST':
        # Get the document title for the success message
        document_title = document.title
        
        # Delete the document (this will cascade delete related ChatSessions and ChatMessages)
        document.delete()
        
        # Add success message
        messages.success(request, f'Document "{document_title}" and all related chats have been deleted.')
        
        # Redirect to documents list
        return redirect('documents')
    
    # If it's a GET request, show confirmation page
    return render(request, 'confirm_delete.html', {'document': document})

# Add a debug view to check document chunks
@staff_member_required
def debug_document(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    
    # Test connection to Colab API
    api_status, _ = colab_client.check_health()
    
    # Get file information if present
    file_info = None
    if document.file:
        file_info = {
            'name': document.file.name,
            'size': f"{document.file.size / 1024:.1f} KB",
            'type': document.file_type,
        }
    
    # Try to retrieve some chunks
    try:
        # Make a simple query to test retrieval
        response = colab_client.generate_response(
            query="Test query",
            document_id=document_id,
            user_id=request.user.id
        )
        retrieval_success = True
    except Exception as e:
        response = str(e)
        retrieval_success = False
    
    return render(request, 'debug_document.html', {
        'document': document,
        'api_status': api_status,
        'retrieval_success': retrieval_success,
        'response': response,
        'file_info': file_info
    })



