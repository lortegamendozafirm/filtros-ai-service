"""Request schemas for API endpoints."""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any


class ProcessRequest(BaseModel):
    """Request model for processing a case."""
    
    task_id: str = Field(..., description="Unique task identifier from ClickUp/Nexus")
    client_name: str = Field(..., description="Name of the client")
    intake_url: str = Field(..., description="Google Drive URL to the intake PDF")
    mycase_id: Optional[str] = Field(None, description="Optional MyCase ID")
    nexus_callback_url: str = Field(..., description="Callback URL to send results")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata (case_type, priority, etc.)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "8686abcde",
                "client_name": "Juan Perez",
                "intake_url": "https://drive.google.com/file/d/123.../view",
                "mycase_id": "12345",
                "nexus_callback_url": "https://nexus-legal-api-223080314602.us-central1.run.app/callbacks/filtros",
                "metadata": {
                    "case_type": "inmigracion",
                    "priority": "high"
                }
            }
        }
