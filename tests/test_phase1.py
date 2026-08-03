import pytest
import asyncio
from config.settings import settings
from src.database.connection import init_db, async_session_factory
from src.database.repository import ClinicRepository

@pytest.mark.asyncio
async def test_database_initialization_and_repository():
    # Inicializar DB
    await init_db()
    
    async with async_session_factory() as session:
        repo = ClinicRepository(session)
        
        # 1. Crear / Obtener Lead
        lead = await repo.get_or_create_lead("+573001234567", full_name="Carlos Mendoza")
        assert lead is not None
        assert lead.full_name == "Carlos Mendoza"
        assert lead.phone_number == "+573001234567"
        
        # 2. Calificar Lead
        updated_lead = await repo.update_lead_qualification(
            phone_number="+573001234567",
            score="VIP",
            service="Diseño de Sonrisa & Carillas",
            notes="Cliente interesado en valoración estética inmediata"
        )
        assert updated_lead.qualification_score == "VIP"
        assert updated_lead.service_interest == "Diseño de Sonrisa & Carillas"

        # 3. Crear Cita y Verificar Disponibilidad
        date_test = "2026-08-10"
        time_test = "10:00"
        
        is_free_before = await repo.check_availability(date_test, time_test)
        assert is_free_before is True

        appointment = await repo.create_appointment(
            phone_number="+573001234567",
            patient_name="Carlos Mendoza",
            service_name="Diseño de Sonrisa & Carillas",
            appointment_date=date_test,
            appointment_time=time_test,
            payment_amount=100000.0
        )
        assert appointment is not None
        assert appointment.status == "Confirmada"

        is_free_after = await repo.check_availability(date_test, time_test)
        assert is_free_after is False

        # 4. Mensajes de conversación
        msg = await repo.save_message(
            phone_number="+573001234567",
            sender="user",
            content="Hola, quiero información para un diseño de sonrisa",
            channel="web_chat"
        )
        assert msg.id is not None
