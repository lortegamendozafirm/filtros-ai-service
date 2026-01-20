"""API v1 endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
import uuid

from app.api.deps import verify_api_key, generate_request_id, get_credentials
from app.schemas.request import ProcessRequest
from app.schemas.response import ProcessResponse, HealthResponse
from app.services.orchestrator import ProcessingOrchestrator
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


async def run_orchestrator_task(task_id: str, client_name: str, intake_url: str, callback_url: str):
    """
    Función Wrapper que se ejecuta completamente en background.
    """
    logger.info(f"🚀 Iniciando background task real para {task_id}")
    try:
        # CAMBIO 2: Obtenemos credenciales via ADC.
        # Esto es seguro tanto en local (lee JSON) como en Cloud Run (lee metadata).
        credentials = get_credentials()
        
        # Inicialización de servicios. Pasamos las credenciales explícitamente
        # para mantener la coherencia, aunque el Orchestrator ya soportaría None.
        orchestrator = ProcessingOrchestrator(credentials=credentials)
        
        # 3. Procesamiento del caso
        await orchestrator.process_case(
            task_id=task_id,
            client_name=client_name,
            intake_url=intake_url,
            callback_url=callback_url
        )
    except Exception as e:
        logger.critical(f"FATAL: Error ejecutando background task para {task_id}: {e}", exc_info=True)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=settings.VERSION
    )


@router.post("/process", response_model=ProcessResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_case(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Process a case analysis request."""
    
    # Generate unique request ID
    request_id = generate_request_id()
    
    logger.info(
        f"Received process request: task_id={request.task_id}, client={request.client_name}",
        extra={"request_id": request_id, "task_id": request.task_id}
    )
    
    # Add background task
    background_tasks.add_task(
        run_orchestrator_task,
        task_id=request.task_id,
        client_name=request.client_name,
        intake_url=request.intake_url,
        callback_url=request.nexus_callback_url
    )
    
    logger.info(
        f"Request accepted and enqueued for task_id={request.task_id}",
        extra={"request_id": request_id, "task_id": request.task_id}
    )
    
    return ProcessResponse(
        status="processing",
        request_id=request_id,
        message="Solicitud encolada correctamente. El procesamiento iniciará en background."
    )