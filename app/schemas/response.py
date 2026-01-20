"""Response schemas for API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum


class ProcessStatus(str, Enum):
    """Processing status enum."""
    PROCESSING = "processing"
    SUCCESS = "success"
    ERROR = "error"


class ProcessResponse(BaseModel):
    """Immediate response for process endpoint (202 Accepted)."""
    
    status: str = Field(..., description="Processing status")
    request_id: str = Field(..., description="Unique request identifier")
    message: str = Field(..., description="Human-readable message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "processing",
                "request_id": "req_uuid_123456",
                "message": "Solicitud recibida. El resultado será enviado al callback URL."
            }
        }


class ArtifactsInfo(BaseModel):
    """Information about generated artifacts."""
    
    doc_id: str = Field(..., description="Google Doc ID")
    doc_url: str = Field(..., description="Google Doc URL")


class DiagnosticsInfo(BaseModel):
    """Processing diagnostics information."""
    
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    version: str = Field(..., description="AI model version used")


class CallbackPayload(BaseModel):
    """Payload sent to Nexus Legal callback URL."""
    
    task_id: str = Field(..., description="Original task ID")
    status: ProcessStatus = Field(..., description="Final processing status")
    outcome: Optional[str] = Field(None, description="Case outcome classification")
    artifacts: Optional[ArtifactsInfo] = Field(None, description="Generated artifacts")
    diagnostics: Optional[DiagnosticsInfo] = Field(None, description="Processing diagnostics")
    error: Optional[str] = Field(None, description="Error message if status is error")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "8686abcde",
                "status": "success",
                "outcome": "POTENTIAL VAWA",
                "artifacts": {
                    "doc_id": "1AbC...",
                    "doc_url": "https://docs.google.com/document/d/1AbC..."
                },
                "diagnostics": {
                    "processing_time_ms": 45000,
                    "version": "gemini-pro-tuned-v1"
                },
                "error": None
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "version": "1.0.0"
            }
        }
