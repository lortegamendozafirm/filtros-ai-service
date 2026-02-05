"""API v1 endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
import uuid

from app.api.deps import verify_api_key, generate_request_id, get_credentials
from app.schemas.request import ProcessRequest
from app.schemas.response import ProcessResponse, HealthResponse
from app.services.orchestrator import ProcessingOrchestrator
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=settings.VERSION
    )

@router.post("/process", response_model=ProcessResponse, status_code=status.HTTP_200_OK)
async def process_case(
    request: ProcessRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Process a case analysis request.
    Este endpoint será invocado por Cloud Tasks y debe esperar hasta terminar.
    """
    
    # Generate unique request ID
    request_id = generate_request_id()
    
    logger.info(
        f"🏁 [Worker Start] Received task from Queue: task_id={request.task_id}",
        extra={"request_id": request_id, "task_id": request.task_id}
    )
    
    try:
        # 1. Inicializar
        orchestrator = ProcessingOrchestrator(credentials=get_credentials())

        # 2. Procesamiento SÍNCRONO (Await real)
        await orchestrator.process_case(
            task_id=request.task_id,
            client_name=request.client_name,
            intake_url=request.intake_url,
            callback_url=request.nexus_callback_url
        )
        
        logger.info(f"✅ [Worker Success] Job finished for {request.task_id}")

        return ProcessResponse(
            status="success",
            request_id=request_id,
            message="Procesamiento completado exitosamente."
        )

    except Exception as e:
        logger.error(f"❌ [Worker Fail] {request.task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en procesamiento: {str(e)}"
        )