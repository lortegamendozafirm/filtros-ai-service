# app/services/ai_service.py
"""Vertex AI service for case analysis using Gemini."""

import time
from typing import Tuple

import google.auth
from google.auth.credentials import Credentials
from google.cloud import aiplatform
from google.oauth2 import service_account

# CORRECCIÓN AQUÍ: Volvemos a usar .preview que es compatible con tu versión instalada
from vertexai.preview.generative_models import (
    GenerativeModel, 
    GenerationConfig, 
    HarmCategory, 
    HarmBlockThreshold
)

from app.core.config import settings
from app.core.logging import get_logger

# Import prompts from existing prompts.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.prompts import instrucciones_sistema, prompt_base, NUEVOS_OUTCOMES_VALIDOS

logger = get_logger(__name__)

class AIService:
    """Service for AI-powered case analysis using Vertex AI."""
    
    def __init__(self, credentials: service_account.Credentials):
        if credentials:
            self.credentials = credentials
        else:
            # ADC para Vertex AI
            self.credentials, project_id = google.auth.default()
            # Aseguramos que el settings tenga el proyecto correcto si ADC lo detecta distinto
            if not settings.PROJECT_ID:
                settings.PROJECT_ID = project_id

        self.model = None
        self._initialize_model()
        
    
    def _initialize_model(self) -> None:
        """Initialize Vertex AI model with High Context Window and No Filters."""
        try:
            aiplatform.init(
                project=settings.PROJECT_ID,
                location=settings.LOCATION,
                credentials=self.credentials
            )
            
            # 1. Configuración de Seguridad: PERMITIR TODO (Necesario para casos legales/abuso)
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            }

            generation_config = GenerationConfig(
                max_output_tokens=8192, # Aumentado para reportes largos
                temperature=0.2,        # Bajo para análisis legal preciso
                top_p=0.95,
            )
            
            # 2. Usamos Gemini 1.5 Flash (1 Millón de tokens context)
            model_name = "gemini-2.5-flash" 
            
            logger.info(f"Initializing model: {model_name} (High Context window)")
            
            self.model = GenerativeModel(
                model_name,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            logger.info(f"Vertex AI model initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Vertex AI model: {e}")
            raise
    
    def generate_analysis(
        self,
        transcript_text: str,
        fundamentos: str,
        client_name: str
    ) -> Tuple[str, str]:
        logger.info(f"Generating analysis for client: {client_name}")
        
        # Build analysis prompt
        analysis_text = self._generate_report(transcript_text, fundamentos, client_name)
        
        # Extract outcome
        outcome = self._extract_outcome(analysis_text)
        
        logger.info(f"Analysis complete. Outcome: {outcome}")
        
        return outcome, analysis_text
    
    def _generate_report(
        self,
        transcript_text: str,
        fundamentos: str,
        client_name: str
    ) -> str:
        # Modify prompt_base to remove wait instruction
        prompt_base_modified = prompt_base.replace(
            'No hagas nada hasta que yo te diga "comienza" (instrucción estricta).',
            ''
        ).strip()
        
        # Build complete prompt
        prompt_completo = (
            f"{instrucciones_sistema}\n\n"
            f"{prompt_base_modified}\n\n"
            f"--- FUNDAMENTOS LEGALES ---\n{fundamentos}\n\n"
            f"--- TRANSCRIPCIONES DEL CASO ({client_name}) ---\n"
            f"{transcript_text}\n\n"
            f"INSTRUCCIÓN: Genera el análisis legal completo ahora."
        )
        
        prompt_length = len(prompt_completo)
        logger.info(f"Analysis prompt length: {prompt_length:,} characters (~{int(prompt_length/4):,} tokens)")
        
        for attempt in range(settings.AI_MAX_RETRIES):
            try:
                logger.info(f"Analysis attempt {attempt + 1}/{settings.AI_MAX_RETRIES}")
                
                # generate_content maneja la llamada a la API
                response = self.model.generate_content(prompt_completo)
                
                if not response.text:
                    raise Exception("Model returned empty response (Check safety filters)")
                    
                analysis_text = response.text
                logger.info(f"Analysis generated successfully ({len(analysis_text)} chars)")
                return analysis_text
                
            except Exception as e:
                if attempt < settings.AI_MAX_RETRIES - 1:
                    wait_time = 10 * (attempt + 1)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"FATAL: Analysis failed logic: {e}")
                    raise Exception(f"Failed after retries: {e}")

    def _extract_outcome(self, analysis_text: str) -> str:
        prompt_outcome = (
            f"Basado en el siguiente análisis legal, identifica ÚNICAMENTE la categoría de outcome.\n"
            f"Lista válida: {NUEVOS_OUTCOMES_VALIDOS}\n\n"
            f"--- ANÁLISIS ---\n{analysis_text[:20000]}...\n\n" 
            f"Responde SOLO con el outcome exacto."
        )
        
        try:
            response = self.model.generate_content(prompt_outcome)
            outcome_raw = response.text.strip().replace('"', '').replace("'", "")
            
            for valid in NUEVOS_OUTCOMES_VALIDOS:
                if valid.lower() == outcome_raw.lower():
                    return valid
            
            for valid in NUEVOS_OUTCOMES_VALIDOS:
                if valid in outcome_raw:
                    return valid
                    
            return outcome_raw
            
        except Exception as e:
            logger.error(f"Outcome extraction failed: {e}")
            return "ERROR_EXTRACTING"