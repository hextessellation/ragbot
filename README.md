# RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot built with Django that allows users to upload documents and ask intelligent questions about their content using large language models.

## Features

- **Document Upload & Processing**: Support for PDF, DOCX, and TXT files
- **Intelligent Q&A**: Context-aware responses using RAG pipeline
- **User Authentication**: Secure user registration and login system
- **Real-time Chat Interface**: Interactive chat with conversation history
- **Flexible AI Backend**: Support for both local Ollama and remote API deployment

## Project Structure

```
ragchatbot/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── db.sqlite3               # SQLite database
├── utils/                   # Utility modules
│   └── RAG_pipeline.py      # Core RAG implementation
├── ragchatbot/              # Django project configuration
│   ├── settings.py          # Django settings
│   ├── urls.py              # URL routing
│   └── wsgi.py              # WSGI configuration
├── chatapp/                 # Main Django application
│   ├── models.py            # Database models
│   ├── views.py             # View controllers
│   ├── colab_client.py      # API client for external services
│   ├── file_processor.py    # Document processing utilities
│   └── vector_store.py      # Vector storage management
├── templates/               # HTML templates
└── media/                   # Uploaded documents
```

## Installation

### Prerequisites
- Python 3.8+
- Git

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/hextessellation/ragbot.git
cd ragbot/ragchatbot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Choose AI Backend**

#### Option A: Local Ollama (Recommended)

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull required model
ollama pull llama3.1:8b-instruct-q4_0

# Start Ollama server
ollama serve
```

Update `ragchatbot/settings.py`:
```python
COLAB_API_URL = 'http://localhost:11434'  # Local Ollama endpoint
```

#### Option B: Remote API via Google Colab + Ngrok

1. **Get Ngrok Auth Token**:
   - Sign up at [Ngrok Dashboard](https://dashboard.ngrok.com/signup)
   - Copy your auth token from "Your Authtoken" section

2. **Setup Google Colab**:
   - Open `utils/RAG_pipeline.py` notebook in Google Colab
   - Replace `"YOUR_AUTH_TOKEN"` with your Ngrok token
   - Run all cells and copy the public URL

3. **Update Django Settings**:
```python
# In ragchatbot/settings.py
COLAB_API_URL = 'https://your-ngrok-url.ngrok.io'
```

5. **Initialize Django**
```bash
# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

6. **Access Application**
Navigate to `http://127.0.0.1:8000`

## Usage

### Document Upload
1. Register/Login to the application
2. Upload supported document formats (PDF, DOCX, TXT)
3. Wait for background processing to complete

### Chat Interface
1. Select processed document from document list
2. Ask questions about the document content
3. Receive AI-generated responses based on document context

## Technical Architecture

### Backend Components
- **Django Framework**: Web application framework
- **SQLite Database**: Document and user data storage
- **ChromaDB**: Vector database for embeddings
- **LangChain**: RAG pipeline orchestration
- **HuggingFace Embeddings**: Text embedding generation

### AI Processing
- **Document Chunking**: Intelligent text splitting for optimal retrieval
- **Vector Embeddings**: Semantic search capabilities using e5-small-v2 model
- **Query Processing**: Context-aware response generation
- **Background Tasks**: Asynchronous document processing

## Configuration

### API Configuration
The application includes an admin interface for managing API settings:
- Navigate to `/api-status/` for connection status and URL management
- Test connectivity and update endpoints without restarting the server

### Environment Variables
```bash
export COLAB_API_URL='your-api-url-here'
export DEBUG=True
export SECRET_KEY='your-secret-key'
```

## Supported File Formats

| Format | Extension | Features |
|--------|-----------|----------|
| PDF | `.pdf` | Text extraction, multi-page support |
| Word | `.docx` | Full document processing |
| Text | `.txt` | Direct text processing |

*Note: CSV and Excel file support is experimental and may not work reliably in the current version.*

## Development

### Running Tests
```bash
python manage.py test
```

### Database Management
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Access Django shell
python manage.py shell
```

### Background Tasks
```bash
python manage.py process_tasks
```

## Troubleshooting

### API Connection Issues
```bash
# Test local Ollama
ollama list
curl http://localhost:11434/api/generate -d '{"model": "llama3.1:8b-instruct-q4_0", "prompt": "Hello"}'

# For Colab setup, verify notebook is running and URL is current
```

### Performance Optimization
- Use local Ollama for better performance and privacy
- Adjust chunk size in document processing for large files
- Monitor system resources during processing

## License

This project is licensed under the MIT License.
