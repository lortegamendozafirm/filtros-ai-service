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

        email_sa = editors[0] if isinstance(editors, list) and editors else editors
        if isinstance(email_sa, list): 
            email_sa = ""

        payload = {
            "nombre": title,
            "carpetaId": settings.TARGET_FOLDER_ID,
            "emailSA": email_sa
        }

        # --- LÓGICA DE REINTENTOS (NUEVO) ---
        max_retries = 3
        last_exception = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Reintento {attempt + 1}/{max_retries} creando Doc: {title}")
                else:
                    logger.info(f"Creating Google Doc via Apps Script: {title}")

                # Aumentamos un poco el timeout y usamos un cliente fresco cada vez
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    response = await client.post(
                        settings.APPS_SCRIPT_URL,
                        json=payload
                    )
                    response.raise_for_status()
                    result = response.json()
                
                # Validación de respuesta lógica
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

            except (httpx.ConnectTimeout, httpx.ConnectError, httpx.ReadTimeout) as e:
                # Capturamos errores de red transitorios
                last_exception = e
                logger.warning(f"⚠️ Fallo de red en intento {attempt + 1}: {type(e).__name__} - {e}")
                
                # Esperamos un poco antes de reintentar (Backoff exponencial: 1s, 2s, 4s...)
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                else:
                    logger.error("❌ Se agotaron los reintentos para conectar con Apps Script.")

            except Exception as e:
                # Otros errores (lógicos, validación) no se reintentan
                logger.error(f"FATAL: Error no recuperable creando documento: {e}", exc_info=True)
                raise e

        # Si salimos del bucle, lanzamos el último error de red capturado
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