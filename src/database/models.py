import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(150), nullable=True, default="Cliente Prospecto")
    email = Column(String(150), nullable=True)
    service_interest = Column(String(100), nullable=True)
    qualification_score = Column(String(20), default="Medio") # VIP, Alto, Medio, Bajo
    budget_level = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    appointments = relationship("Appointment", back_populates="lead", cascade="all, delete-orphan")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    patient_name = Column(String(150), nullable=False)
    phone_number = Column(String(50), nullable=False)
    service_name = Column(String(100), nullable=False)
    specialist = Column(String(100), default="Dra. Valentina Ríos (Estética & Sonrisa)")
    appointment_date = Column(String(10), nullable=False) # YYYY-MM-DD
    appointment_time = Column(String(8), nullable=False)  # HH:MM
    duration_minutes = Column(Integer, default=45)
    status = Column(String(30), default="Confirmada")      # Confirmada, Pendiente_Pago, Reagendada, Cancelada
    payment_status = Column(String(30), default="Pendiente") # Pagado, Pendiente, No_Aplica
    payment_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    lead = relationship("Lead", back_populates="appointments")

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(50), index=True, nullable=False)
    sender = Column(String(20), nullable=False) # user, agent, system
    channel = Column(String(20), default="web_chat") # web_chat, whatsapp
    message_type = Column(String(20), default="text") # text, audio, interactive
    content = Column(Text, nullable=False)
    intent_detected = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
