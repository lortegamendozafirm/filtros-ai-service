# app/services/orchestrator.py
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
    def __init__(self, credentials: Optional[Credentials] = None):
        self.credentials = credentials
        self.drive_service = DriveService(credentials)
        self.ai_service = AIService(credentials)
        self.docs_service = DocsService()
    
    async def process_case(self, task_id: str, client_name: str, intake_url: str, callback_url: str) -> None:
        start_time = time.time()
        extra = {"task_id": task_id}
        
        # --- PASO 1: RESERVAR/CREAR EL DOC (Validación temprana) ---
        # Si esto falla, lanzará una excepción y el endpoint la capturará.
        logger.info("Step 1: Creating placeholder Google Doc", extra=extra)
        # Nota: Usamos un título temporal o definitivo si ya lo tenemos
        doc_info = await self.docs_service.create_document(
            title=f"Análisis en proceso - {client_name}", 
            editors="docs-writer-sa@ortega-473114.iam.gserviceaccount.com"
        )
        doc_id = doc_info["doc_id"]
        doc_url = doc_info["doc_url"]

        try:
            # --- PASO 2: DESCARGA Y EXTRACCIÓN ---
            logger.info("Step 2: Downloading and extracting PDF", extra=extra)
            transcript_text = self.drive_service.download_and_extract(intake_url)
            if not transcript_text:
                raise Exception("No text extracted from PDF")
            
            # --- PASO 3: IA ---
            logger.info("Step 3: Generating AI analysis", extra=extra)
            outcome, analysis_text = self.ai_service.generate_analysis(
                transcript_text, load_fundamentals(), client_name
            )
            
            # --- PASO 4: ESCRIBIR RESULTADO EN EL DOC ---
            # Ya tenemos el doc_id desde el paso 1, solo escribimos.
            logger.info("Step 4: Writing analysis to Doc", extra=extra)
            full_content = f"# Análisis de Filtro - {client_name} ({outcome})\n\n{analysis_text}"
            await self.docs_service.write_content(doc_id, full_content)

            # --- PASO 5: CALLBACK ÉXITO ---
            processing_time_ms = int((time.time() - start_time) * 1000)
            await self._send_callback(callback_url, CallbackPayload(
                task_id=task_id,
                status=ProcessStatus.SUCCESS,
                outcome=outcome,
                artifacts=ArtifactsInfo(doc_id=doc_id, doc_url=doc_url),
                diagnostics=DiagnosticsInfo(processing_time_ms=processing_time_ms, version="gemini-pro-tuned-v1")
            ))

        except Exception as e:
            await self._handle_processing_error(task_id, e, start_time, callback_url, extra)
            raise e # Esto es correcto, permite que el endpoint capture el error

    async def _handle_processing_error(self, task_id, error, start_time, callback_url, extra):
        processing_time_ms = int((time.time() - start_time) * 1000)
        try:
            await self._send_callback(callback_url, CallbackPayload(
                task_id=task_id,
                status=ProcessStatus.ERROR,
                diagnostics=DiagnosticsInfo(processing_time_ms=processing_time_ms, version="gemini-pro-tuned-v1"),
                error=str(error)
            ))
        except Exception as e:
            logger.error(f"Could not send error callback. error:{e}")
            

    async def _send_callback(self, callback_url: str, payload: CallbackPayload) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(callback_url, json=payload.model_dump())
            response.raise_for_status()