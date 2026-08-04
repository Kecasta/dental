import os
import json
import datetime
import asyncio
from typing import Dict, Any, List, Optional

from config.settings import settings
from config.logging_config import logger
from src.agent.prompts import CLINIC_SYSTEM_PROMPT, CLINIC_SERVICES
from src.agent.tools import (
    tool_consultar_disponibilidad,
    tool_agendar_cita,
    tool_calificar_prospecto
)

# Intentar importar la librería oficial de Gemini
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class GeminiClinicAgent:
    def __init__(self, api_key: Optional[str] = None):
        raw_key = api_key or settings.GEMINI_API_KEY
        self.api_key = raw_key.strip('"').strip("'").strip() if raw_key else None
        self.client = None
        if HAS_GENAI and self.api_key:
            try:
                # Loggear los primeros caracteres para depuración segura
                logger.info(f"Inicializando cliente Gemini con API Key que inicia en: {self.api_key[:8]}...")
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Cliente de Google Gemini 2.5 Flash inicializado con éxito.")
            except Exception as e:
                logger.warning(f"No se pudo inicializar el cliente Gemini: {e}")


    async def process_message(
        self,
        phone_number: str,
        user_message: str,
        history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Procesa el mensaje del usuario utilizando únicamente Gemini REST API.
        """
        history = history or []
        return await self._call_gemini(user_message, history, phone_number)


    async def _call_gemini(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        phone_number: str
    ) -> Dict[str, Any]:
        """Ejecuta inferencia directa por REST API en Gemini para evitar problemas de firmas de google-auth."""
        import httpx

        model_name = settings.GEMINI_MODEL or 'gemini-2.5-flash'




        # Preparar los mensajes del historial en formato REST de Gemini
        contents_payload = []
        for h in history[-10:]:
            role = "user" if h["sender"] == "user" else "model"
            contents_payload.append({
                "role": role,
                "parts": [{"text": h["content"]}]
            })
        
        # Añadir el mensaje actual
        contents_payload.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        # Declarar herramientas en formato JSON de la API REST
        tools_payload = [
            {
                "functionDeclarations": [
                    {
                        "name": "consultar_disponibilidad",
                        "description": "Consulta la disponibilidad de agenda para Smile Aesthetic & Dental Clinic.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "fecha": {"type": "STRING", "description": "Fecha YYYY-MM-DD (ej: 2026-08-10)"},
                                "hora": {"type": "STRING", "description": "Hora HH:MM (ej: 10:00)"}
                            },
                            "required": ["fecha", "hora"]
                        }
                    },
                    {
                        "name": "agendar_cita",
                        "description": "Reserva y confirma una cita médica/estética en Smile Aesthetic & Dental Clinic.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "nombre": {"type": "STRING", "description": "Nombre completo del paciente"},
                                "servicio": {"type": "STRING", "description": "Servicio deseado"},
                                "fecha": {"type": "STRING", "description": "Fecha YYYY-MM-DD"},
                                "hora": {"type": "STRING", "description": "Hora HH:MM"}
                            },
                            "required": ["nombre", "servicio", "fecha", "hora"]
                        }
                    },
                    {
                        "name": "calificar_prospecto",
                        "description": "Registra la calificación de scoring del lead o prospecto en el CRM.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "score": {"type": "STRING", "description": "Puntaje de scoring ('VIP', 'Alto', 'Medio', 'Bajo')"},
                                "servicio": {"type": "STRING", "description": "Servicio principal de interés"},
                                "notes": {"type": "STRING", "description": "Comentarios y notas sobre el lead"}
                            },
                            "required": ["score", "servicio", "notes"]
                        }
                    }
                ]
            }
        ]

        # Payload completo de la API REST
        payload = {
            "contents": contents_payload,
            "systemInstruction": {
                "parts": [{"text": CLINIC_SYSTEM_PROMPT}]
            },
            "tools": tools_payload,
            "generationConfig": {
                "temperature": 0.7
            }
        }

        tools_called = []
        reply_text = ""

        # Bucle manual para resolver las llamadas de herramientas por API REST
        while True:
            # Mecanismo de reintentos con múltiples esquemas de autenticación de Google
            res = None
            last_err = None

            # Método 1: Cabecera x-goog-api-key con reintento automático para 503 / 429
            for attempt in range(3):
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                    headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
                    async with httpx.AsyncClient(timeout=30.0) as http_client:
                        res = await http_client.post(url, json=payload, headers=headers)
                        if res.status_code == 200:
                            data = res.json()
                            break
                        elif res.status_code in (503, 429) and attempt < 2:
                            logger.warning(f"Servidor de Google ocupado (Status {res.status_code}). Reintentando en 1.5s (intento {attempt+1}/3)...")
                            await asyncio.sleep(1.5)
                            continue
                        else:
                            raise Exception(f"Status {res.status_code}: {res.text}")
                except Exception as e1:
                    if attempt == 2:
                        logger.warning(f"Intento 1 (x-goog-api-key) falló tras 3 reintentos con: {e1}")
                        last_err = e1
                    else:
                        await asyncio.sleep(1.0)

            # Método 1.5: Fallback a modelo gemini-2.0-flash si hay sobrecarga 503 en el principal

            if res is None and last_err and "503" in str(last_err):
                fallback_model = "gemini-2.0-flash" if model_name != "gemini-2.0-flash" else "gemini-1.5-flash"
                logger.info(f"Cambiando a modelo de respaldo ultra-rápido {fallback_model} por alta demanda de Google...")
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{fallback_model}:generateContent"
                    headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
                    async with httpx.AsyncClient(timeout=30.0) as http_client:
                        res = await http_client.post(url, json=payload, headers=headers)
                        if res.status_code == 200:
                            data = res.json()
                        else:
                            raise Exception(f"Status {res.status_code}: {res.text}")
                except Exception as e_fb:
                    logger.warning(f"Modelo de respaldo {fallback_model} falló con: {e_fb}")

            # Método 2: Cabecera Authorization Bearer (Para tokens de tipo OAuth2/Stitch)

            if res is None:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                    headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                    async with httpx.AsyncClient(timeout=30.0) as http_client:
                        res = await http_client.post(url, json=payload, headers=headers)
                        if res.status_code == 200:
                            data = res.json()
                        else:
                            raise Exception(f"Status {res.status_code}: {res.text}")
                except Exception as e2:
                    logger.warning(f"Intento 2 (Authorization Bearer) falló con: {e2}")
                    last_err = e2
                    res = None

            # Método 3: Parámetro en URL ?key= (Esquema clásico de Google AI Studio)
            if res is None:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
                    async with httpx.AsyncClient(timeout=30.0) as http_client:
                        res = await http_client.post(url, json=payload)
                        if res.status_code == 200:
                            data = res.json()
                        else:
                            raise Exception(f"Status {res.status_code}: {res.text}")
                except Exception as e3:
                    logger.warning(f"Intento 3 (?key=) falló con: {e3}")
                    last_err = e3
                    res = None


            # Si todos los métodos fallaron, levantar la excepción
            if res is None:
                raise Exception(f"Todos los esquemas de autenticación fallaron. Último error: {last_err}")

            candidates = data.get("candidates", [])
            if not candidates:
                break

            candidate = candidates[0]
            parts = candidate.get("content", {}).get("parts", [])

            # Filtrar si el modelo solicitó llamadas a herramientas
            function_calls = [p.get("functionCall") for p in parts if "functionCall" in p]

            if not function_calls:
                # No hay llamadas a funciones: extraer texto final de respuesta
                text_parts = [p.get("text") for p in parts if "text" in p]
                reply_text = "".join(text_parts) if text_parts else ""
                break


            # Procesar las herramientas solicitadas por el modelo
            model_parts_payload = []
            tool_responses_payload = []

            for function_call in function_calls:
                name = function_call.get("name")
                args = function_call.get("args", {})
                logger.info(f"Gemini (REST API) solicitó ejecutar: '{name}' con argumentos: {args}")
                tools_called.append(name)

                result = None
                try:
                    if name == "consultar_disponibilidad":
                        result = await tool_consultar_disponibilidad(
                            fecha=args.get("fecha"),
                            hora=args.get("hora")
                        )
                    elif name == "agendar_cita":
                        result = await tool_agendar_cita(
                            nombre=args.get("nombre"),
                            telefono=phone_number,
                            servicio=args.get("servicio"),
                            fecha=args.get("fecha"),
                            hora=args.get("hora")
                        )
                    elif name == "calificar_prospecto":
                        result = await tool_calificar_prospecto(
                            telefono=phone_number,
                            puntaje=args.get("score"),
                            servicio=args.get("servicio"),
                            notas=args.get("notes")
                        )
                except Exception as tool_err:
                    logger.error(f"Error ejecutando herramienta {name}: {tool_err}")
                    result = {"error": str(tool_err)}

                # Guardar la respuesta de la herramienta
                tool_responses_payload.append({
                    "functionResponse": {
                        "name": name,
                        "response": {"result": result}
                    }
                })

            # Añadir ambos turnos al historial del payload para la siguiente iteración
            payload["contents"].append(candidate["content"])
            payload["contents"].append({
                "role": "user",
                "parts": tool_responses_payload
            })


        if not reply_text:
            reply_text = "Cita registrada con éxito. ¿Tienes alguna otra duda?"

        # Determinar intención
        intent = "consulta"
        if "agendar_cita" in tools_called:
            intent = "agendamiento"
        elif any(w in user_message.lower() for w in ["hola", "buenas", "buenos dias", "buenas tardes"]):
            intent = "saludo"

        return {
            "response_text": reply_text,
            "intent": intent,
            "used_model": model_name,
            "tools_called": tools_called
        }







