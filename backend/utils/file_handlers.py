"""
File handling utilities for resume parsing
"""
import io
from typing import Union
from PyPDF2 import PdfReader
from docx import Document


def extract_text_from_pdf(file_content: Union[bytes, io.BytesIO]) -> str:
    """Extract text from PDF file"""
    try:
        if isinstance(file_content, bytes):
            file_content = io.BytesIO(file_content)
        
        reader = PdfReader(file_content)
        text_parts = []
        
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        
        return "\n".join(text_parts)
    
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def extract_text_from_docx(file_content: Union[bytes, io.BytesIO]) -> str:
    """Extract text from DOCX file"""
    try:
        if isinstance(file_content, bytes):
            file_content = io.BytesIO(file_content)
        
        doc = Document(file_content)
        text_parts = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
        
        # Also extract from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text_parts.append(cell.text)
        
        return "\n".join(text_parts)
    
    except Exception as e:
        raise ValueError(f"Failed to extract text from DOCX: {str(e)}")


def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """Extract text from file based on extension"""
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.pdf'):
        return extract_text_from_pdf(file_content)
    elif filename_lower.endswith('.docx'):
        return extract_text_from_docx(file_content)
    elif filename_lower.endswith('.txt'):
        return file_content.decode('utf-8')
    else:
        raise ValueError(f"Unsupported file format: {filename}")

