import os
import json
import datetime
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
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.client = None
        if HAS_GENAI and self.api_key:
            try:
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
        Procesa el mensaje del usuario utilizando Gemini o el motor heurístico de contingencia.
        """
        history = history or []

        # Si tenemos API Key y librería, usar Gemini con Function Calling
        if self.client:
            try:
                return await self._call_gemini(user_message, history, phone_number)
            except Exception as e:
                logger.error(f"Error procesando con Gemini API: {e}. Usando fallback inteligente.")

        # Fallback Heurístico Intuitivo (Demostración Garantizada)
        return await self._heuristic_fallback(phone_number, user_message)

    async def _call_gemini(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        phone_number: str
    ) -> Dict[str, Any]:
        """Ejecuta inferencia en Gemini 2.5/3.5 Flash."""
        # Estructurar contexto de conversación
        prompt_content = f"{CLINIC_SYSTEM_PROMPT}\n\n"
        prompt_content += f"Número del cliente actual: {phone_number}\n"
        prompt_content += "Historial reciente:\n"
        for h in history[-5:]:
            prompt_content += f"- {h['sender']}: {h['content']}\n"
        prompt_content += f"- user: {user_message}\n\nResponde como Sofía (IA de Smile Clinic):"

        model_name = settings.GEMINI_MODEL or 'gemini-2.5-flash'
        response = self.client.models.generate_content(
            model=model_name,
            contents=prompt_content,
        )
        
        reply_text = response.text if response and response.text else "¡Hola! Bienvenido a Smile Aesthetic & Dental Clinic. ¿En qué te puedo asesorar hoy?"

        # Verificar intención básica de agendamiento
        intent = "consulta"
        if "agend" in user_message.lower() or "cita" in user_message.lower() or "reserv" in user_message.lower():
            intent = "agendamiento"

        return {
            "response_text": reply_text,
            "intent": intent,
            "used_model": model_name,
            "tools_called": []
        }


    async def _heuristic_fallback(self, phone_number: str, user_message: str) -> Dict[str, Any]:
        """Motor heurístico para asegurar respuestas fluidas de demostración."""
        msg_lower = user_message.lower()
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        tomorrow_str = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        # 1. Saludo Inicial
        if any(w in msg_lower for w in ["hola", "buenas", "buenos dias", "buenas tardes", "información", "inicio"]):
            return {
                "response_text": (
                    "¡Hola! ✨ Bienvenido a **Smile Aesthetic & Dental Clinic** 🦷. "
                    "Soy Sofía, tu asesora virtual. ¿En qué tratamiento estás interesado hoy?\n\n"
                    "💎 *Diseño de Sonrisa & Carillas*\n"
                    "✨ *Armonización Facial & Ácido Hialurónico*\n"
                    "🦷 *Ortodoncia Invisible*\n"
                    "🌟 *Blanqueamiento Dental LED*\n"
                    "🩺 *Valoración Odontológica*"
                ),
                "intent": "saludo",
                "used_model": "heuristic_fallback",
                "tools_called": []
            }

        # 2. Solicitud de Cita, Disponibilidad o Tratamientos Específicos
        booking_keywords = [
            "cita", "agendar", "reservar", "diseño", "armonización", "mañana", "lunes", 
            "valoracion", "valoración", "blanqueamiento", "ortodoncia", "limpieza", 
            "disponibilidad", "disponible", "horario", "horarios", "cupo", "cupos", "agenda"
        ]
        if any(w in msg_lower for w in booking_keywords):
            # Identificar servicio
            service_detected = "Valoración Odontológica"
            if "diseño" in msg_lower or "carillas" in msg_lower:
                service_detected = "Diseño de Sonrisa & Carillas"
            elif "armonización" in msg_lower or "ácido" in msg_lower or "facial" in msg_lower:
                service_detected = "Armonización Facial & Ácido Hialurónico"
            elif "ortodoncia" in msg_lower or "alineador" in msg_lower:
                service_detected = "Ortodoncia Invisible (Alineadores)"
            elif "blanqueamiento" in msg_lower:
                service_detected = "Blanqueamiento Dental LED"
            elif "limpieza" in msg_lower:
                service_detected = "Limpieza Ultrasonido & Profilaxis"

            # Ejecutar tool de disponibilidad
            check_res = await tool_consultar_disponibilidad(tomorrow_str, "10:00")

            if check_res.get("disponible"):
                # Ejecutar tool de agendamiento
                book_res = await tool_agendar_cita(
                    nombre="Paciente Demo",
                    telefono=phone_number,
                    servicio=service_detected,
                    fecha=tomorrow_str,
                    hora="10:00"
                )
                return {
                    "response_text": (
                        f"¡Con gusto! He agendado una cita de **{service_detected}** con la Dra. Valentina Ríos.\n\n"
                        f"📅 **Fecha:** {tomorrow_str}\n"
                        f"⏰ **Hora:** 10:00 AM\n"
                        f"📍 **Ubicación:** Smile Clinic - Sede Principal Calle 93 # 14-20\n\n"
                        f"{'💳 *Nota:* Este procedimiento requiere abono de reserva. ' if book_res.get('requiere_abono') else ''}"
                        "¿Te queda bien este horario para confirmar tus datos?"
                    ),
                    "intent": "agendamiento_exitoso",
                    "used_model": "heuristic_fallback",
                    "tools_called": ["consultar_disponibilidad", "agendar_cita"]
                }
            else:
                sug = check_res.get("horarios_sugeridos", ["11:15 AM", "03:00 PM"])
                return {
                    "response_text": (
                        f"Para {service_detected}, el horario solicitado está ocupado, pero tengo estos 3 horarios disponibles para mañana:\n\n"
                        f"1️⃣ {sug[0]} (Mañana)\n"
                        f"2️⃣ {sug[1] if len(sug)>1 else '02:30 PM'} (Tarde)\n\n"
                        "¿Cuál de estos horarios te queda mejor?"
                    ),
                    "intent": "reagendamiento_opciones",
                    "used_model": "heuristic_fallback",
                    "tools_called": ["consultar_disponibilidad"]
                }

        # 3. Precios y Tarifas
        if any(w in msg_lower for w in ["precio", "cuanto cuesta", "costo", "tarifa", "valores", "cuánto cuesta"]):
            return {
                "response_text": (
                    "Con gusto te comparto nuestras tarifas preferenciales 📋:\n\n"
                    "• **Diseño de Sonrisa & Carillas:** desde $1,200,000 COP\n"
                    "• **Armonización Facial:** desde $800,000 COP\n"
                    "• **Ortodoncia Invisible:** desde $2,500,000 COP\n"
                    "• **Blanqueamiento LED:** $350,000 COP\n"
                    "• **Valoración Odontológica:** $80,000 COP (incluye radiografía)\n\n"
                    "¿Deseas agendar tu valoración con la especialista?"
                ),
                "intent": "consulta_precios",
                "used_model": "heuristic_fallback",
                "tools_called": []
            }

        # Respuesta General
        return {
            "response_text": (
                "Entendido. En **Smile Aesthetic & Dental Clinic** ofrecemos Diseño de Sonrisa, "
                "Ortodoncia Invisible, Armonización Facial y Blanqueamiento Dental.\n\n"
                "¿Te gustaría agendar una valoración mañana o conocer los precios de algún tratamiento?"
            ),
            "intent": "general",
            "used_model": "heuristic_fallback",
            "tools_called": []
        }

