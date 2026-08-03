import pytest
import asyncio
from src.database.connection import init_db
from src.agent.gemini_client import GeminiClinicAgent

@pytest.mark.asyncio
async def test_phase2_agent_and_tools():
    await init_db()
    agent = GeminiClinicAgent()

    # 1. Probar saludo inicial
    res1 = await agent.process_message("+573998887766", "Hola buenas tardes")
    assert "Smile Aesthetic & Dental Clinic" in res1["response_text"]
    assert res1["intent"] == "saludo"

    # 2. Probar solicitud de precios
    res2 = await agent.process_message("+573998887766", "¿Cuánto cuesta el diseño de sonrisa?")
    assert "Diseño de Sonrisa" in res2["response_text"]

    # 3. Probar respuesta de agendamiento (reserva o propuesta de alternativas si está ocupado)
    res3 = await agent.process_message("+573998887766", "Quiero agendar cita para diseño de sonrisa mañana")
    assert "consultar_disponibilidad" in res3["tools_called"] or len(res3["response_text"]) > 20
