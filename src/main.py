import os
import sys
import asyncio
from contextlib import asynccontextmanager

# Asegurar que el directorio raíz esté en sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from config.settings import settings
from config.logging_config import logger
from src.database.connection import init_db, get_db_session
from src.database.repository import ClinicRepository
from src.agent.gemini_client import GeminiClinicAgent

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Base de datos e infraestructura de Smile Aesthetic & Dental Clinic inicializada.")
    yield

# Inicializar FastAPI
app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = GeminiClinicAgent()

class ChatRequest(BaseModel):
    phone_number: str
    message: str
    channel: str = "web_chat"

@app.post("/api/chat")
async def handle_chat_api(payload: ChatRequest):
    """Endpoint unificado para mensajes recibidos por Web Widget o Webhook."""
    try:
        async for session in get_db_session():
            repo = ClinicRepository(session)
            
            # Guardar mensaje de usuario
            await repo.save_message(
                phone_number=payload.phone_number,
                sender="user",
                content=payload.message,
                channel=payload.channel
            )
            
            # Historial reciente
            raw_history = await repo.get_conversation_history(payload.phone_number)
            formatted_history = [{"sender": msg.sender, "content": msg.content} for msg in raw_history]

            # Procesar con IA
            result = await agent.process_message(
                phone_number=payload.phone_number,
                user_message=payload.message,
                history=formatted_history
            )

            # Guardar respuesta IA
            await repo.save_message(
                phone_number=payload.phone_number,
                sender="agent",
                content=result["response_text"],
                channel=payload.channel,
                intent_detected=result.get("intent")
            )

            return JSONResponse(content={
                "status": "success",
                "response_text": result["response_text"],
                "intent": result.get("intent"),
                "tools_called": result.get("tools_called", [])
            })
    except Exception as e:
        logger.error(f"Error procesando chat API: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "response_text": "Ha ocurrido un error procesando tu solicitud."}
        )

web_dir = os.path.join(os.path.dirname(__file__), "web")

@app.get("/")
async def root_landing():
    index_path = os.path.join(web_dir, "index.html")
    return FileResponse(index_path)

@app.get("/{filename}")
async def serve_static_assets(filename: str):
    file_path = os.path.join(web_dir, filename)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return JSONResponse(status_code=404, content={"detail": "File not found"})

if __name__ == "__main__":
    import socket
    port = settings.PORT
    # Probar puerto si está disponible, de lo contrario usar 8050
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex((settings.HOST, port)) == 0:
            port = 8050

    logger.info(f"Lanzando Smile Aesthetic & Dental Clinic en http://localhost:{port}")
    logger.info(f"Landing Page Web + Chat Widget: http://localhost:{port}/")
    uvicorn.run("src.main:app", host=settings.HOST, port=port, reload=False)

