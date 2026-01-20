# app/service/driver_service.py
"""Google Drive service for PDF download and text extraction."""

import re
import io
import tempfile
from typing import Optional, Tuple
from pathlib import Path

import google.auth
from google.auth.transport.requests import Request
from google.auth.credentials import Credentials

import fitz  # PyMuPDF
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.core.config import settings
from app.core.logging import get_logger
from app.utils.text_cleaner import clean_extracted_text, sanitize_filename

logger = get_logger(__name__)


def extract_id_from_url(url: str) -> Optional[str]:
    """Extract Google Drive file ID from various URL formats.
    
    Args:
        url: Google Drive URL
        
    Returns:
        File ID or None if not found
    """
    patterns = [
        r'/d/([-\w]{25,})',  # /d/ID
        r'id=([-\w]{25,})',  # id=ID
        r'open\?id=([-\w]{25,})'  # open?id=ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


class DriveService:
    """Service for interacting with Google Drive."""
    
    def __init__(self, credentials: service_account.Credentials):
        """Initialize Drive service.
        
        Args:
            credentials: Google Auth Credentials. If None, uses ADC.
        """
        if credentials:
            self.credentials = credentials
        else:
            # MAGIA DE ADC: Busca JSON local o Identidad de Cloud Run automáticamente
            self.credentials, _ = google.auth.default(
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            
        self.service = build('drive', 'v3', credentials=self.credentials)
        
    
    def download_file(self, file_id: str) -> Tuple[bytes, str]:
        """Download file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Tuple of (file_bytes, mime_type)
            
        Raises:
            Exception: If download fails
        """
        try:
            # Get file metadata
            file_metadata = self.service.files().get(fileId=file_id).execute()
            mime_type = file_metadata.get('mimeType')
            name = file_metadata.get('name')
            
            logger.info(f"Downloading file: {name} ({mime_type})")
            
            # Determine download method based on MIME type
            if mime_type == 'application/vnd.google-apps.document':
                # Export Google Doc as PDF
                logger.info("Exporting Google Doc to PDF...")
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='application/pdf'
                )
                mime_type = 'application/pdf'
            else:
                # Download file directly
                logger.info("Downloading file...")
                request = self.service.files().get_media(fileId=file_id)
            
            # Download to bytes
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Download progress: {int(status.progress() * 100)}%")
            
            file_bytes = fh.getvalue()
            logger.info(f"Downloaded {len(file_bytes)} bytes")
            
            return file_bytes, mime_type
            
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            raise
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes using PyMuPDF.
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            Extracted text
            
        Raises:
            Exception: If extraction fails
        """
        try:
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            total_pages = len(doc)
            logger.info(f"Extracting text from PDF ({total_pages} pages)...")
            
            # Limit pages if configured
            max_pages = min(total_pages, settings.MAX_PDF_PAGES)
            if max_pages < total_pages:
                logger.warning(f"Limiting extraction to first {max_pages} pages")
            
            text = ""
            for page_num in range(max_pages):
                page = doc[page_num]
                text += page.get_text()
            
            doc.close()
            
            # Clean extracted text
            text = clean_extracted_text(text)
            
            logger.info(f"Extracted {len(text)} characters from PDF")
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def download_and_extract(self, drive_url: str) -> str:
        """Download PDF from Drive and extract text.
        
        Args:
            drive_url: Google Drive URL
            
        Returns:
            Extracted text
            
        Raises:
            ValueError: If URL is invalid
            Exception: If download or extraction fails
        """
        # Extract file ID
        file_id = extract_id_from_url(drive_url)
        if not file_id:
            raise ValueError(f"Could not extract file ID from URL: {drive_url}")
        
        logger.info(f"Processing Drive file: {file_id}")
        
        # Download file
        pdf_bytes, mime_type = self.download_file(file_id)
        
        # Verify it's a PDF
        if mime_type != 'application/pdf':
            raise ValueError(f"Expected PDF, got {mime_type}")
        
        # Extract text
        text = self.extract_text_from_pdf(pdf_bytes)
        
        # Truncate if too long
        if len(text) > settings.MAX_TEXT_LENGTH:
            logger.warning(
                f"Text length ({len(text)}) exceeds maximum ({settings.MAX_TEXT_LENGTH}), truncating"
            )
            text = text[:settings.MAX_TEXT_LENGTH]
        
        return text
