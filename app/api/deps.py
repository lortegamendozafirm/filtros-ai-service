# app/api/deps.py
"""FastAPI dependencies for authentication and shared resources."""

import os
from typing import Optional
import uuid

from fastapi import Header, HTTPException, status
import google.auth
from google.auth.credentials import Credentials

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key from request header.
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not x_api_key:
        logger.warning("Request received without API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header."
        )
    
    # Nota de seguridad: En producción asegúrate de que settings.API_KEY esté cargado
    # desde Secrets Manager o variables de entorno inyectadas.
    if x_api_key != settings.API_KEY:
        logger.warning(f"Invalid API key attempt: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return x_api_key


def generate_request_id() -> str:
    """Generate a unique request ID.
    
    Returns:
        UUID-based request ID
    """
    return f"req_{uuid.uuid4().hex[:12]}"


def get_credentials() -> Credentials:
    """Load Google Cloud credentials using ADC with EXPLICIT Scopes."""
    try:
        # 1. Definimos los scopes necesarios (Drive Readonly es VITAL)
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.readonly', 
            'https://www.googleapis.com/auth/cloud-platform'
        ]
        
        logger.info("Iniciando carga de credenciales...")

        # --- CORRECCIÓN CRÍTICA 1: Puenteo de Variable de Entorno ---
        # Aseguramos que google.auth vea la ruta definida en .env
        # Esto es necesario porque Pydantic lee el .env pero google.auth lee os.environ
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            # Verificamos si es un archivo local (solo pasa en local)
            if os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
                logger.info(f"Forzando uso de Service Account Local: {settings.GOOGLE_APPLICATION_CREDENTIALS}")
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
            else:
                # Si no existe el archivo, asumimos que estamos en Cloud Run y esto es correcto
                logger.debug("Ruta de credenciales no es un archivo local, asumiendo entorno Cloud Run managed.")

        # --- CORRECCIÓN CRÍTICA 2: Inyección directa de Scopes ---
        # Pasamos los scopes AQUÍ, no después. Esto obliga a la librería a
        # pedir el token correcto desde el nacimiento del objeto.
        creds, project_id = google.auth.default(scopes=scopes)
        
        logger.info(f"Credenciales cargadas exitosamente. Tipo: {type(creds).__name__}")
        
        return creds

    except Exception as e:
        logger.error(f"FATAL: Fallo al cargar credenciales ADC: {e}")
        raise