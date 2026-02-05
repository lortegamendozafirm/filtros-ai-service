# app/services/docs_service.py
"""Document generation service using Apps Script and m2gdw."""

import httpx
import asyncio
from typing import Dict, Any, List, Union

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class DocsService:
    """Service for creating and writing Google Docs."""
    
    async def create_document(self, title: str, editors: Union[List[str], str]) -> Dict[str, str]:
        """Create a new Google Doc using Apps Script with Retry Logic."""
        
        # Validación preventiva
        if not settings.APPS_SCRIPT_URL:
            raise ValueError("APPS_SCRIPT_URL no está configurada")

        # Lógica para extraer un solo email si viene una lista
        email_sa = editors[0] if isinstance(editors, list) and editors else editors
        if isinstance(email_sa, list): 
            email_sa = ""

        payload = {
            "nombre": title,
            "carpetaId": settings.TARGET_FOLDER_ID,
            "emailSA": email_sa
        }
        
        # CONFIGURACIÓN CRÍTICA DE RED:
        # connect=10.0: Si no hay respuesta TCP en 10s, abortar (evita colgarse infinitamente).
        # read=60.0: Apps Script es lento generando docs, damos hasta 60s para esperar el JSON de éxito.
        timeout_config = httpx.Timeout(60.0, connect=10.0)

        max_retries = 5
        last_exception = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Reintento {attempt + 1}/{max_retries} creando Doc: {title}")
                else:
                    logger.info(f"Creating Google Doc via Apps Script: {title}")

                # AJUSTES DEL CLIENTE HTTP:
                # http2=False: VITAL. Cloud Run a veces falla negociando HTTP/2 con Google Scripts. Forzamos HTTP/1.1.
                # follow_redirects=True: VITAL. Apps Script devuelve un 302 siempre.
                async with httpx.AsyncClient(
                    timeout=timeout_config, 
                    follow_redirects=True, 
                    http2=False,
                    verify=True # Mantenemos seguridad SSL
                ) as client:
                    response = await client.post(
                        settings.APPS_SCRIPT_URL,
                        json=payload
                    )
                    response.raise_for_status()
                    result = response.json()
                
                # Validación de respuesta lógica del script
                if result.get("status") != "success":
                    raise Exception(f"Apps Script logical error: {result.get('message')}")
                    
                doc_id = result.get("docId")
                doc_url = result.get("url")
                
                if not doc_id:
                    raise Exception(f"Invalid response format: {result}")
                
                logger.info(f"✅ Document created successfully: {doc_id}")
                
                return {
                    "doc_id": doc_id,
                    "doc_url": doc_url
                }

            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
                last_exception = e
                # Backoff exponencial más agresivo: 2, 4, 8, 16 segundos
                wait_time = 2 ** attempt 
                logger.warning(f"⚠️ Fallo de red. Reintentando en {wait_time}s...")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                # Si es un error de lógica de Apps Script (ej. cuota excedida), 
                # lanzamos un error que podamos capturar arriba.
                raise e

        # Si salimos del bucle por agotamiento de intentos
        if last_exception:
            logger.error(f"FATAL: Error creating document after {max_retries} attempts.", exc_info=True)
            raise last_exception
    
    async def write_content(self, doc_id: str, markdown_content: str) -> None:
        """Write Markdown content to Google Doc using m2gdw service."""
        try:
            logger.info(f"Writing content to document: {doc_id}")
            
            payload = {
                "document_id": doc_id,
                "markdown_content": markdown_content
            }
            
            # Timeout generoso para escritura (m2gdw)
            async with httpx.AsyncClient(timeout=200.0) as client:
                response = await client.post(
                    settings.M2GDW_URL,
                    json=payload
                )
                response.raise_for_status()
            
            logger.info(f"Content written successfully to {doc_id}")
            
        except Exception as e:
            logger.error(f"Error writing content to document: {e}")
            raise
    
    async def generate_report_document(
        self,
        client_name: str,
        outcome: str,
        analysis_content: str
    ) -> Dict[str, str]:
        """Create document and write analysis content."""
        
        # Create document title
        title = f"Análisis - {client_name} ({outcome})"

        sa_email = "docs-writer-sa@ortega-473114.iam.gserviceaccount.com" 
        
        # Create document (Apps Script le dará permisos a este email)
        doc_info = await self.create_document(title, sa_email)
        
        # Prepare content with header
        full_content = f"# Análisis de Filtro - Cliente {client_name} ({outcome})\n\n{analysis_content}"
        
        # Write content
        await self.write_content(doc_info["doc_id"], full_content)
        
        return doc_info