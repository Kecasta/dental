from typing import List, Optional, Dict, Any
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import Lead, Appointment, ConversationMessage

class ClinicRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- LEADS ---
    async def get_or_create_lead(self, phone_number: str, full_name: Optional[str] = None) -> Lead:
        result = await self.session.execute(select(Lead).where(Lead.phone_number == phone_number))
        lead = result.scalars().first()
        if not lead:
            lead = Lead(phone_number=phone_number, full_name=full_name or "Cliente Prospecto")
            self.session.add(lead)
            await self.session.commit()
            await self.session.refresh(lead)
        elif full_name and lead.full_name == "Cliente Prospecto":
            lead.full_name = full_name
            await self.session.commit()
            await self.session.refresh(lead)
        return lead

    async def update_lead_qualification(
        self, phone_number: str, score: str, service: str, notes: Optional[str] = None
    ) -> Lead:
        lead = await self.get_or_create_lead(phone_number)
        lead.qualification_score = score
        if service:
            lead.service_interest = service
        if notes:
            lead.notes = (lead.notes or "") + f"\n[{score}] {notes}"
        await self.session.commit()
        await self.session.refresh(lead)
        return lead

    async def get_all_leads(self) -> List[Lead]:
        result = await self.session.execute(select(Lead).order_by(Lead.updated_at.desc()))
        return result.scalars().all()

    # --- APPOINTMENTS ---
    async def get_appointments_by_date(self, date_str: str) -> List[Appointment]:
        result = await self.session.execute(
            select(Appointment).where(Appointment.appointment_date == date_str, Appointment.status != "Cancelada")
        )
        return result.scalars().all()

    async def create_appointment(
        self,
        phone_number: str,
        patient_name: str,
        service_name: str,
        appointment_date: str,
        appointment_time: str,
        specialist: str = "Dra. Valentina Ríos (Estética & Sonrisa)",
        payment_amount: float = 0.0
    ) -> Appointment:
        lead = await self.get_or_create_lead(phone_number, full_name=patient_name)
        appointment = Appointment(
            lead_id=lead.id,
            patient_name=patient_name,
            phone_number=phone_number,
            service_name=service_name,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            specialist=specialist,
            payment_amount=payment_amount,
            status="Confirmada"
        )
        self.session.add(appointment)
        await self.session.commit()
        await self.session.refresh(appointment)
        return appointment

    async def check_availability(self, date_str: str, time_str: str) -> bool:
        result = await self.session.execute(
            select(Appointment).where(
                Appointment.appointment_date == date_str,
                Appointment.appointment_time == time_str,
                Appointment.status != "Cancelada"
            )
        )
        existing = result.scalars().first()
        return existing is None

    async def get_all_appointments(self) -> List[Appointment]:
        result = await self.session.execute(select(Appointment).order_by(Appointment.created_at.desc()))
        return result.scalars().all()

    # --- CONVERSATIONS ---
    async def save_message(
        self,
        phone_number: str,
        sender: str,
        content: str,
        channel: str = "web_chat",
        message_type: str = "text",
        intent_detected: Optional[str] = None
    ) -> ConversationMessage:
        msg = ConversationMessage(
            phone_number=phone_number,
            sender=sender,
            content=content,
            channel=channel,
            message_type=message_type,
            intent_detected=intent_detected
        )
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return msg

    async def get_conversation_history(self, phone_number: str, limit: int = 20) -> List[ConversationMessage]:
        result = await self.session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.phone_number == phone_number)
            .order_by(ConversationMessage.timestamp.asc())
            .limit(limit)
        )
        return result.scalars().all()
