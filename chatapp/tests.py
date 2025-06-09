from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Document, ChatSession, ChatMessage
import json
import os
from unittest.mock import patch, MagicMock

class DocumentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        
    def test_document_creation(self):
        document = Document.objects.create(
            title='Test Document',
            content='This is a test document content.',
            uploaded_by=self.user
        )
        self.assertEqual(document.title, 'Test Document')
        self.assertEqual(document.uploaded_by, self.user)

class ChatSessionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.document = Document.objects.create(
            title='Test Document',
            content='This is a test document content.',
            uploaded_by=self.user
        )
        
    def test_chat_session_creation(self):
        session = ChatSession.objects.create(
            user=self.user,
            document=self.document
        )
        self.assertEqual(session.user.username, 'testuser')

class APIViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        self.document = Document.objects.create(
            title='Test Document',
            content='This is a test document content.',
            uploaded_by=self.user
        )
        
    def test_document_upload(self):
        url = reverse('upload_document')
        
        file_path = 'test_document.txt'
        with open(file_path, 'w') as f:
            f.write('Test document content for upload')
        
        # The form expects 'title' and 'content', not 'file'
        with open(file_path, 'rb') as f:
            file_content = f.read().decode('utf-8')
            response = self.client.post(url, {
                'title': 'Uploaded Doc',
                'content': file_content,  # Change 'file' to 'content'
            })
        
        if os.path.exists(file_path):
            os.remove(file_path)
        
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.content}")
        
        self.assertEqual(response.status_code, 302)  # 302 is the redirect status code
        self.assertTrue(Document.objects.filter(title='Uploaded Doc').exists())
    '''
    def test_api_integration(self):
        # Create a session to have a chat
        chat_session = ChatSession.objects.create(
            user=self.user,
            document=self.document
        )
        
        # Mock the API responses instead of making actual calls
        # This is the correct module path to patch
        with patch('chatapp.colab_client.requests.post') as mock_post:
            # Configure the mock
            mock_response = mock_post.return_value
            mock_response.status_code = 200
            mock_response.json.return_value = {'response': 'This is a test response'}
            
            # Test your chat view that calls the API
            response = self.client.post(reverse('send_message', kwargs={'session_id': chat_session.id}), {
                'message': 'What is this document about?'
            })
            
            # Verify the mock was called
            mock_post.assert_called_once()
            
            # Verify the response
            self.assertEqual(response.status_code, 200)
    '''
    def test_colab_client(self):
        """Test that the ColabClient works correctly with mocked responses."""
        from chatapp.colab_client import ColabClient
        import os
        
        # Create a test client with a dummy URL
        test_client = ColabClient(api_url="http://test-url.com")
        
        # Mock the requests.post method
        with patch('chatapp.colab_client.requests.post') as mock_post:
            # Set up mock for process_document
            mock_response_process = MagicMock()
            mock_response_process.status_code = 200
            mock_response_process.json.return_value = {'success': True, 'chunks': 5}
            
            # Set up mock for generate_response
            mock_response_generate = MagicMock()
            mock_response_generate.status_code = 200
            mock_response_generate.json.return_value = {'response': 'This is a test response'}
            
            # Configure mock to return different responses for different API calls
            mock_post.side_effect = [mock_response_process, mock_response_generate]
            
            # Test process_document
            result = test_client.process_document(
                document_id="123",
                content="Test content",
                user_id="456"
            )
            
            # Check the result
            self.assertEqual(result, 5)  # We expect 5 chunks
            
            # Check that requests.post was called with correct arguments for process_document
            self.assertEqual(mock_post.call_count, 1)
            args, kwargs = mock_post.call_args_list[0]
            self.assertEqual(args[0], 'http://test-url.com/process_document')
            self.assertEqual(kwargs['json']['document_id'], "123")
            
            # Test generate_response
            response = test_client.generate_response(
                query="What is this document about?",
                document_id="123",
                user_id="456"
            )
            
            # Check the response
            self.assertEqual(response, 'This is a test response')
            
            # Check that requests.post was called with correct arguments for generate
            self.assertEqual(mock_post.call_count, 2)
            args, kwargs = mock_post.call_args_list[1]
            self.assertEqual(args[0], 'http://test-url.com/generate')
            self.assertEqual(kwargs['json']['query'], "What is this document about?")
