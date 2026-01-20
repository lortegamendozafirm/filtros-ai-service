"""Main orchestrator for processing pipeline."""

import time
import httpx
import json
from typing import Dict, Any, Optional

from google.auth.credentials import Credentials 

from app.core.config import settings
from app.core.logging import get_logger
from app.services.drive_service import DriveService
from app.services.ai_service import AIService
from app.services.docs_service import DocsService
from app.utils.fundamentals import load_fundamentals
from app.schemas.response import CallbackPayload, ProcessStatus, ArtifactsInfo, DiagnosticsInfo

logger = get_logger(__name__)


class ProcessingOrchestrator:
    """Orchestrates the complete case processing pipeline."""
    
    def __init__(self, credentials: Optional[Credentials] = None):
        """Initialize orchestrator with services."""
        self.credentials = credentials
        self.drive_service = DriveService(credentials)
        self.ai_service = AIService(credentials)
        self.docs_service = DocsService()
    
    async def process_case(
        self,
        task_id: str,
        client_name: str,
        intake_url: str,
        callback_url: str
    ) -> None:
        """Process a complete case from intake to callback."""

        start_time = time.time()
        
        # Set up logging context
        extra = {"task_id": task_id}
        logger.info(f"Starting case processing for task: {task_id}", extra=extra)
        
        try:
            # Step 1: Download and extract PDF text
            logger.info("Step 1: Downloading and extracting PDF", extra=extra)
            transcript_text = self.drive_service.download_and_extract(intake_url)
            
            if not transcript_text:
                raise Exception("No text extracted from PDF")
            
            # Step 2: Load legal fundamentals
            logger.info("Step 2: Loading legal fundamentals", extra=extra)
            fundamentos = load_fundamentals()
            
            # Step 3: Generate AI analysis
            logger.info("Step 3: Generating AI analysis", extra=extra)
            outcome, analysis_text = self.ai_service.generate_analysis(
                transcript_text,
                fundamentos,
                client_name
            )
            # ✨ MEJORA DE VISIBILIDAD: Ver el resultado inmediatamente
            logger.info(f"⚖️ AI Outcome decided: {outcome}", extra=extra)
            
            # Step 4: Create and populate Google Doc
            logger.info("Step 4: Creating Google Doc", extra=extra)
            doc_info = await self.docs_service.generate_report_document(
                client_name,
                outcome,
                analysis_text
            )
            # ✨ MEJORA DE VISIBILIDAD: Link clickeable en logs
            logger.info(f"📄 Doc created: {doc_info.get('doc_url')}", extra=extra)
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Step 5: Send success callback
            logger.info("Step 5: Sending success callback", extra=extra)
            await self._send_callback(
                callback_url,
                CallbackPayload(
                    task_id=task_id,
                    status=ProcessStatus.SUCCESS,
                    outcome=outcome,
                    artifacts=ArtifactsInfo(
                        doc_id=doc_info["doc_id"],
                        doc_url=doc_info["doc_url"]
                    ),
                    diagnostics=DiagnosticsInfo(
                        processing_time_ms=processing_time_ms,
                        version="gemini-pro-tuned-v1" # <--- ¡Bien corregido!
                    )
                )
            )
            
            logger.info(
                f"Case processing completed successfully in {processing_time_ms}ms",
                extra=extra
            )
            
        except Exception as e:
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.error(f"Case processing failed: {e}", extra=extra, exc_info=True)
            
            # Determine error type
            error_message = str(e)
            if "file ID" in error_message.lower():
                error_code = "DOCUMENT_ACCESS_DENIED"
            elif "timeout" in error_message.lower():
                error_code = "AI_TIMEOUT"
            elif "extract" in error_message.lower() or "pdf" in error_message.lower():
                error_code = "PARSING_ERROR"
            else:
                error_code = "PROCESSING_ERROR"
            
            # Send error callback
            try:
                await self._send_callback(
                    callback_url,
                    CallbackPayload(
                        task_id=task_id,
                        status=ProcessStatus.ERROR,
                        outcome=None,
                        artifacts=None,
                        diagnostics=DiagnosticsInfo(
                            processing_time_ms=processing_time_ms,
                            version="gemini-pro-tuned-v1"
                        ),
                        error=f"{error_code}: {error_message}"
                    )
                )
            except Exception as callback_error:
                logger.error(
                    f"Failed to send error callback: {callback_error}",
                    extra=extra
                )
    
    async def _send_callback(self, callback_url: str, payload: CallbackPayload) -> None:
        """Send callback to Nexus Legal."""
        try:
            payload_data = payload.model_dump()
            
            # Estos logs son excelentes para debug
            logger.info(f"🚀 Iniciando Callback a: {callback_url}")
            logger.info(f"📦 Payload a enviar: {json.dumps(payload_data)}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    callback_url,
                    json=payload_data
                )
                logger.info(f"⬅️ Respuesta del Callback (Status): {response.status_code}")
                
                # Opcional: Si la respuesta es muy larga, podrías querer truncarla
                # pero para depurar ahora está bien completa.
                logger.info(f"⬅️ Respuesta del Callback (Body): {response.text}")
                
                response.raise_for_status()
            
            logger.info("Callback sent successfully")
            
        except Exception as e:
            # Aquí ya tienes el logger.error que lo atrapará en process_case, 
            # pero está bien dejarlo si quieres logging específico del método.
            logger.error(f"Error sending callback inner: {e}")
            raise