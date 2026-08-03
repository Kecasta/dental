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
        """Ejecuta inferencia en Gemini 2.5/3.5 Flash utilizando Function Calling manual por esquema."""
        from google.genai import types

        model_name = settings.GEMINI_MODEL or 'gemini-2.5-flash'

        # Declarar esquemas de las funciones (evita que el SDK intente ejecutarlas de forma asíncrona automática)
        schema_consultar = types.FunctionDeclaration(
            name="consultar_disponibilidad",
            description="Consulta la disponibilidad de agenda para Smile Aesthetic & Dental Clinic.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "fecha": types.Schema(type=types.Type.STRING, description="Fecha YYYY-MM-DD (ej: 2026-08-10)"),
                    "hora": types.Schema(type=types.Type.STRING, description="Hora HH:MM (ej: 10:00)")
                },
                required=["fecha", "hora"]
            )
        )

        schema_agendar = types.FunctionDeclaration(
            name="agendar_cita",
            description="Reserva y confirma una cita médica/estética en Smile Aesthetic & Dental Clinic.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "nombre": types.Schema(type=types.Type.STRING, description="Nombre completo del paciente"),
                    "servicio": types.Schema(type=types.Type.STRING, description="Servicio (ej: 'Valoración Odontológica', 'Blanqueamiento Dental LED', 'Diseño de Sonrisa & Carillas', 'Armonización Facial & Ácido Hialurónico', 'Ortodoncia Invisible (Alineadores)')"),
                    "fecha": types.Schema(type=types.Type.STRING, description="Fecha YYYY-MM-DD"),
                    "hora": types.Schema(type=types.Type.STRING, description="Hora HH:MM")
                },
                required=["nombre", "servicio", "fecha", "hora"]
            )
        )

        schema_calificar = types.FunctionDeclaration(
            name="calificar_prospecto",
            description="Registra la calificación de scoring del lead o prospecto en el CRM.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "score": types.Schema(type=types.Type.STRING, description="Puntaje de scoring ('VIP', 'Alto', 'Medio', 'Bajo')"),
                    "servicio": types.Schema(type=types.Type.STRING, description="Servicio principal de interés"),
                    "notes": types.Schema(type=types.Type.STRING, description="Comentarios y notas sobre el lead")
                },
                required=["score", "servicio", "notes"]
            )
        )

        # Configurar la instrucción del sistema y las herramientas por esquema
        config = types.GenerateContentConfig(
            system_instruction=CLINIC_SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=[schema_consultar, schema_agendar, schema_calificar])],
            temperature=0.7,
        )

        # Construir el historial estructurado de la conversación
        contents = []
        for h in history[-10:]:
            role = "user" if h["sender"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=h["content"])]
                )
            )
        
        # Añadir el último mensaje del usuario
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message)]
            )
        )

        # Primera llamada al modelo
        response = self.client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config
        )

        tools_called = []
        
        # Bucle para resolver las llamadas de herramientas (Function Calling loop manual)
        while response.function_calls:
            tool_responses = []
            model_parts = []
            
            for function_call in response.function_calls:
                name = function_call.name
                args = function_call.args
                logger.info(f"Gemini solicitó ejecutar la herramienta: '{name}' con argumentos: {args}")
                tools_called.append(name)
                
                # Ejecutar la herramienta correspondiente
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
                            puntaje=args.get("score"),  # notar el cambio a 'puntaje' para concordar con tools.py
                            servicio=args.get("servicio"),
                            notas=args.get("notes")      # notar el cambio a 'notas' para concordar con tools.py
                        )
                except Exception as tool_err:
                    logger.error(f"Error ejecutando herramienta {name}: {tool_err}")
                    result = {"error": str(tool_err)}

                # Añadir la respuesta de la herramienta
                tool_responses.append(
                    types.Part.from_function_response(
                        name=name,
                        response={"result": result}
                    )
                )
                
                # Guardar la llamada hecha por el modelo
                model_parts.append(
                    types.Part.from_function_call(
                        name=name,
                        args=args
                    )
                )
            
            # Añadir las llamadas del modelo y sus respuestas al historial de contents
            contents.append(types.Content(role="model", parts=model_parts))
            contents.append(types.Content(role="user", parts=tool_responses))
            
            # Re-invocar a Gemini con los resultados de las herramientas
            response = self.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )


        reply_text = response.text if response and response.text else "Cita registrada con éxito. ¿Tienes alguna otra duda?"

        # Determinar intención
        intent = "consulta"
        if "agendamiento_exitoso" in tools_called or "agendar_cita" in tools_called:
            intent = "agendamiento"

        return {
            "response_text": reply_text,
            "intent": intent,
            "used_model": model_name,
            "tools_called": tools_called
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

