import os
import io
import csv
import chardet
import logging
from PyPDF2 import PdfReader
import docx2txt
import pandas as pd
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

def extract_content_from_file(file):
    """Extract text content from various file types"""
    file_name = file.name if hasattr(file, 'name') else 'unknown'
    extension = os.path.splitext(file_name)[1].lower()
    
    # Reset file pointer to beginning
    if hasattr(file, 'seek'):
        file.seek(0)
    
    try:
        # Handle different file types
        if extension == '.pdf':
            return extract_from_pdf(file)
        elif extension == '.docx':
            return extract_from_docx(file)
        elif extension == '.doc':
            return "DOC format requires external conversion. Please convert to DOCX or PDF."
        elif extension in ['.xlsx', '.xls']:
            return extract_from_excel(file)
        elif extension == '.csv':
            return extract_from_csv(file)
        elif extension in ['.txt', '.md', '.json', '.xml']:
            return extract_from_text(file)
        else:
            # Try to read as plain text by default
            return extract_from_text(file)
    except Exception as e:
        logger.error(f"Error extracting content from {file_name}: {str(e)}")
        raise ValueError(f"Could not extract content from {file_name}: {str(e)}")

def extract_from_pdf(file):
    """Extract text from PDF files"""
    pdf_reader = PdfReader(file)
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        text += pdf_reader.pages[page_num].extract_text() + "\n"
    return text.strip()

def extract_from_docx(file):
    """Extract text from DOCX files"""
    return docx2txt.process(file)

def extract_from_excel(file):
    """Extract text from Excel files"""
    df = pd.read_excel(file)
    return df.to_string()

def extract_from_csv(file):
    """Extract text from CSV files"""
    content = file.read()
    # Try to detect encoding
    result = chardet.detect(content)
    encoding = result['encoding'] if result['encoding'] else 'utf-8'
    
    # Reset file pointer
    file.seek(0)
    
    text = []
    try:
        # Try to parse as CSV
        csv_data = csv.reader(io.StringIO(content.decode(encoding)))
        for row in csv_data:
            text.append(", ".join(row))
        return "\n".join(text)
    except Exception as e:
        # If CSV parsing fails, return as plain text
        logger.warning(f"Could not parse CSV properly, returning raw text: {str(e)}")
        return content.decode(encoding, errors='replace')

def extract_from_text(file):
    """Extract content from text files with encoding detection"""
    content = file.read()
    # Try to detect encoding
    result = chardet.detect(content)
    encoding = result['encoding'] if result['encoding'] else 'utf-8'
    
    # Decode the content with the detected encoding
    return content.decode(encoding, errors='replace')

def process_document_text(text, document_id, user_id):
    # Replace simple chunking with more semantically aware splitting
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,  # Smaller chunks for more precise retrieval
        chunk_overlap=300,  # Larger overlap to maintain context across chunks
        separators=["\n\n", "\n", ".", " ", ""],  # More granular separators for better splitting
        length_function=len
    )
    
    # Split text and create metadata with more context
    chunks = text_splitter.create_documents(
        [text], 
        metadatas=[{"document_id": str(document_id), "user_id": str(user_id), "source": "document"}]
    )
    
    # Add rich metadata to chunks
    enriched_chunks = enrich_chunk_metadata(chunks, document_id)
    
    return enriched_chunks

def enrich_chunk_metadata(chunks, document_id):
    """Add richer metadata to chunks for better retrieval"""
    enriched_chunks = []
    
    for i, chunk in enumerate(chunks):
        # Extract potential section titles or headers
        lines = chunk.page_content.split('\n')
        potential_header = lines[0] if lines else ""
        
        # Determine chunk position in document
        position = "beginning" if i < len(chunks)/3 else "middle" if i < 2*len(chunks)/3 else "end"
        
        # Enhance metadata
        chunk.metadata.update({
            "chunk_id": i,
            "position": position,
            "potential_header": potential_header[:50],
            "content_preview": chunk.page_content[:100].replace("\n", " ")
        })
        enriched_chunks.append(chunk)
    
    return enriched_chunks