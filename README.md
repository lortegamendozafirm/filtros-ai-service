# FILTROS AI Service

Microservicio stateless para automatizar el análisis legal preliminar de casos de inmigración usando IA.

## Descripción

FILTROS AI Service es un microservicio basado en FastAPI que:

- Recibe solicitudes HTTP con detalles de casos y enlaces a PDFs de intake
- Descarga y extrae texto de documentos PDF almacenados en Google Drive
- Analiza la viabilidad del caso usando Vertex AI (Gemini) con contexto legal
- Genera reportes estructurados en formato Markdown
- Crea Google Docs vía Apps Script y los llena usando el servicio m2gdw
- Envía resultados al sistema solicitante (Nexus Legal) vía callback

## Arquitectura

```
Cliente (Nexus Legal)
    ↓ POST /v1/process
FILTROS AI Service
    ↓ Descarga PDF
Google Drive API
    ↓ Análisis con contexto legal
Vertex AI (Gemini)
    ↓ Crear documento
Apps Script
    ↓ Escribir contenido
m2gdw Service
    ↓ Callback con resultados
Cliente (Nexus Legal)
```

## Estructura del Proyecto

```
filtrosmendoza/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   └── endpoints.py      # Rutas POST /process, GET /health
│   │   └── deps.py               # Dependencias (Auth, Credentials)
│   ├── core/
│   │   ├── config.py             # Configuración (Pydantic Settings)
│   │   └── logging.py            # Logging estructurado
│   ├── services/
│   │   ├── drive_service.py      # Descarga PDF y extracción (PyMuPDF)
│   │   ├── ai_service.py         # Vertex AI (Gemini) interacción
│   │   ├── docs_service.py       # Orquestación Apps Script + m2gdw
│   │   └── orchestrator.py       # Pipeline principal
│   ├── schemas/
│   │   ├── request.py            # Modelos Pydantic entrada
│   │   └── response.py           # Modelos Pydantic salida
│   ├── utils/
│   │   ├── text_cleaner.py       # Normalización de texto
│   │   └── fundamentals.py       # Carga de contexto legal
│   ├── data/
│   │   └── fundamentals/         # Archivos .md de contexto legal
│   └── main.py                   # Entrypoint FastAPI
├── tests/                        # Tests (pytest)
├── Dockerfile
├── cloudbuild.yaml
├── requirements.txt
├── .env.example
├── prompts.py                    # Configuración de prompts
└── README.md
```

## Requisitos

- Python 3.11+
- Google Cloud Project con:
  - Vertex AI habilitado
  - Service Account con permisos para Drive, Sheets, Vertex AI
- Apps Script desplegado como Web App
- Servicio m2gdw accesible

## Instalación Local

### 1. Clonar y configurar entorno

```bash
cd /home/ortega/filtrosmendoza
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus valores
```

Variables requeridas:
- `PROJECT_ID`: ID del proyecto GCP
- `LOCATION`: Región GCP (us-central1)
- `VERTEX_ENDPOINT_ID`: ID del endpoint de Vertex AI
- `GOOGLE_APPLICATION_CREDENTIALS`: Ruta al JSON de service account
- `APPS_SCRIPT_URL`: URL del Apps Script Web App
- `M2GDW_URL`: URL del servicio m2gdw
- `TARGET_FOLDER_ID`: ID de carpeta de Drive para reportes
- `API_KEY`: Clave de API para autenticación

### 3. Ejecutar localmente

```bash
uvicorn app.main:app --reload --port 8080
```

La aplicación estará disponible en `http://localhost:8080`

## Uso

### Health Check

```bash
curl http://localhost:8080/health
```

Respuesta:
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### Procesar un caso

```bash
curl -X POST http://localhost:8080/v1/process \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "task_id": "8686abcde",
    "client_name": "Juan Perez",
    "intake_url": "https://drive.google.com/file/d/123.../view",
    "nexus_callback_url": "https://nexus-legal.app/callback/filtros"
  }'
```

Respuesta inmediata (202 Accepted):
```json
{
  "status": "processing",
  "request_id": "req_abc123",
  "message": "Solicitud recibida. El resultado será enviado al callback URL."
}
```

### Callback enviado al completar

```json
{
  "task_id": "8686abcde",
  "status": "success",
  "outcome": "POTENTIAL VAWA",
  "artifacts": {
    "doc_id": "1AbC...",
    "doc_url": "https://docs.google.com/document/d/1AbC..."
  },
  "diagnostics": {
    "processing_time_ms": 45000,
    "model_version": "gemini-pro-tuned-v1"
  },
  "error": null
}
```

## Deployment en Cloud Run

### Opción 1: Cloud Build (Recomendado)

```bash
gcloud builds submit --config cloudbuild.yaml
```

### Opción 2: Manual

```bash
# 1. Construir imagen
gcloud builds submit --tag gcr.io/woven-operative-419903/filtros-ai-service:v1

# 2. Desplegar
gcloud run deploy filtros-ai-service \
  --image gcr.io/woven-operative-419903/filtros-ai-service:v1 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300s \
  --set-env-vars PROJECT_ID=woven-operative-419903,LOCATION=us-central1,VERTEX_ENDPOINT_ID=5192293029079154688
```

### Configurar Secrets

```bash
# Crear secret para API Key
echo -n "your-api-key" | gcloud secrets create filtros-api-key --data-file=-

# Crear secret para Service Account
gcloud secrets create filtros-sa-key --data-file=service-account.json

# Actualizar servicio para usar secrets
gcloud run services update filtros-ai-service \
  --update-secrets=API_KEY=filtros-api-key:latest \
  --update-secrets=GOOGLE_APPLICATION_CREDENTIALS=filtros-sa-key:latest
```

## Testing

```bash
# Instalar dependencias de testing
pip install pytest pytest-asyncio pytest-cov httpx

# Ejecutar tests
pytest tests/ -v

# Con coverage
pytest tests/ --cov=app --cov-report=html
```

## Outcomes Válidos

- Pass
- DENIED
- NO INFO_SOLO QUEST
- POTENTIAL VAWA
- NQ-NOT QAL RELATION
- POTENTIAN VISA T
- N/Q - TS
- NON VAWA
- NQ - GMC
- NQ - VAWA_VISA T
- NQ - VISA U
- NQ - FORCED LABOR
- POSSIBLE NON VAWA
- Reactivation
- VAWA - NEA
- VISA U
- VAWA SPOUSE

## Logs

Los logs están estructurados en formato JSON para compatibilidad con Cloud Logging:

```json
{
  "timestamp": "2026-01-14T16:00:00Z",
  "severity": "INFO",
  "message": "Starting case processing",
  "task_id": "8686abcde",
  "request_id": "req_abc123"
}
```

## Troubleshooting

### Error: "DOCUMENT_ACCESS_DENIED"
- Verificar que el Service Account tenga acceso al archivo en Drive
- Verificar que el file ID sea correcto

### Error: "AI_TIMEOUT"
- Aumentar el timeout en Cloud Run
- Verificar conectividad con Vertex AI
- Revisar cuotas de Vertex AI

### Error: "PARSING_ERROR"
- Verificar que el archivo sea un PDF válido
- Revisar logs para detalles del error de extracción

## Licencia

Propietario: Ortega EO

## Contacto

Para soporte o preguntas, contactar al equipo de desarrollo.
