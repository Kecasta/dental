import asyncio
import os
import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, Lead, Appointment, ConversationMessage

DB_PATH = os.path.abspath("data/smile_clinic.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

DEMO_PATIENTS = [
    {
        "name": "Camila Morales",
        "phone": "+573104882910",
        "service": "Ortodoncia Invisible (Alineadores)",
        "score": "VIP",
        "date": "2026-08-05",
        "time": "09:00",
        "chat": [
            ("user", "Hola, me interesa saber sobre los alineadores invisibles"),
            ("agent", "¡Hola Camila! ✨ Con gusto te asesoro sobre nuestra Ortodoncia Invisible. Son alineadores transparentes sin brackets."),
            ("user", "Genial, quisiera agendar una valoración para el miércoles en la mañana"),
            ("agent", "¡Perfecto! He confirmado tu cita para el Miércoles 05 de Agosto a las 09:00 AM con la Dra. Valentina Ríos.")
        ]
    },
    {
        "name": "Alejandro Gómez",
        "phone": "+573209182374",
        "service": "Diseño de Sonrisa & Carillas",
        "score": "VIP",
        "date": "2026-08-05",
        "time": "11:30",
        "chat": [
            ("user", "Buenas tardes, quiero cotizar carillas cerámicas para diseño de sonrisa"),
            ("agent", "¡Hola Alejandro! Con el mayor gusto. El diseño de sonrisa con carillas incluye escáner 3D y evaluación estética completa."),
            ("user", "Listo, agendemos para este miércoles a las 11:30 AM"),
            ("agent", "¡Excelente decisión! Cita agendada para el Miércoles 05 de Agosto a las 11:30 AM.")
        ]
    },
    {
        "name": "Mariana Silva",
        "phone": "+573017654321",
        "service": "Armonización Facial & Ácido Hialurónico",
        "score": "VIP",
        "date": "2026-08-06",
        "time": "10:00",
        "chat": [
            ("user", "Hola Sofía, quisiera consultar por perfilado de labios con ácido hialurónico"),
            ("agent", "¡Hola Mariana! ✨ La Dra. Valentina Ríos es especialista en armonización facial y perfilado labial biocompatible."),
            ("user", "Me gustaría agendar el jueves a las 10:00 AM"),
            ("agent", "¡Confirmada tu valoración de Armonización Facial para el Jueves 06 de Agosto a las 10:00 AM!")
        ]
    },
    {
        "name": "Juan Sebastián Pérez",
        "phone": "+573158889900",
        "service": "Blanqueamiento Dental LED",
        "score": "Alto",
        "date": "2026-08-06",
        "time": "14:00",
        "chat": [
            ("user", "Hola, cuánto cuesta el blanqueamiento dental LED?"),
            ("agent", "¡Hola Juan Sebastián! El blanqueamiento dental LED intensivo tiene un costo de $350,000 COP en 1 sola sesión."),
            ("user", "Perfecto, agéndame para el jueves en la tarde a las 2 PM"),
            ("agent", "¡Cita reservada con éxito para el Jueves 06 de Agosto a las 02:00 PM!")
        ]
    },
    {
        "name": "Daniela Gutiérrez",
        "phone": "+573024445566",
        "service": "Diseño de Sonrisa & Carillas",
        "score": "VIP",
        "date": "2026-08-07",
        "time": "08:30",
        "chat": [
            ("user", "Hola, me recomendaron a la Dra. Valentina para diseño de sonrisa"),
            ("agent", "¡Bienvenida Daniela! La Dra. Valentina Ríos estará encantada de diseñar tu mejor sonrisa."),
            ("user", "Quiero una cita a primera hora del viernes"),
            ("agent", "¡Cita agendada para el Viernes 07 de Agosto a las 08:30 AM!")
        ]
    },
    {
        "name": "Carlos Eduardo Ruiz",
        "phone": "+573183332211",
        "service": "Limpieza Ultrasonido & Profilaxis",
        "score": "Medio",
        "date": "2026-08-07",
        "time": "15:30",
        "chat": [
            ("user", "Buenas tardes, tienen disponible cita para limpieza dental?"),
            ("agent", "¡Hola Carlos! Sí, la profilaxis con ultrasonido elimina cálculo y hace un pulido profundo."),
            ("user", "Por favor para el viernes a las 3:30 PM"),
            ("agent", "¡Quedó agendada tu Limpieza Ultrasonido para el Viernes 07 de Agosto a las 03:30 PM!")
        ]
    },
    {
        "name": "Sofía Ramírez",
        "phone": "+573001112233",
        "service": "Ortodoncia Invisible (Alineadores)",
        "score": "Alto",
        "date": "2026-08-08",
        "time": "11:00",
        "chat": [
            ("user", "Hola Sofía, deseo asesoría para alineadores transparentes"),
            ("agent", "¡Hola tocaia! ✨ Claro que sí, evaluaremos tu caso con escaneo 3D sin brackets."),
            ("user", "Agendemos el sábado a las 11 AM"),
            ("agent", "¡Cita reservada para el Sábado 08 de Agosto a las 11:00 AM!")
        ]
    },
    {
        "name": "Mateo Hernández",
        "phone": "+573129998877",
        "service": "Valoración Odontológica General",
        "score": "Medio",
        "date": "2026-08-08",
        "time": "16:00",
        "chat": [
            ("user", "Hola, me gustaría una cita de valoración general"),
            ("agent", "¡Hola Mateo! Con gusto te agendamos una valoración diagnóstica completa."),
            ("user", "Tienen disponible el sábado en la tarde?"),
            ("agent", "¡Confirmado! Tu cita es el Sábado 08 de Agosto a las 04:00 PM.")
        ]
    },
    {
        "name": "Valeria Valencia",
        "phone": "+573057776655",
        "service": "Armonización Facial & Ácido Hialurónico",
        "score": "VIP",
        "date": "2026-08-10",
        "time": "09:30",
        "chat": [
            ("user", "Hola, quiero agendar rinomodelación y perfilado labial"),
            ("agent", "¡Hola Valeria! Bienvenida. La Dra. Valentina Ríos realiza perfilado armónico con ácido hialurónico."),
            ("user", "Me sirve para el lunes a las 9:30 AM"),
            ("agent", "¡Cita confirmada de Armonización Facial para el Lunes 10 de Agosto a las 09:30 AM!")
        ]
    },
    {
        "name": "Santiago Restrepo",
        "phone": "+573165554433",
        "service": "Blanqueamiento Dental LED",
        "score": "Alto",
        "date": "2026-08-10",
        "time": "14:30",
        "chat": [
            ("user", "Hola! Deseo blanqueamiento dental antes de un evento"),
            ("agent", "¡Hola Santiago! Te recomendamos nuestro blanqueamiento LED intensivo de 1 sesión."),
            ("user", "Agéndame para el lunes a las 2:30 PM"),
            ("agent", "¡Cita confirmada para el Lunes 10 de Agosto a las 02:30 PM!")
        ]
    }
]

async def seed_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        print("🌱 Insertando 10 pacientes de prueba en la base de datos...")

        for p in DEMO_PATIENTS:
            # 1. Crear o buscar Lead
            lead = Lead(
                phone_number=p["phone"],
                full_name=p["name"],
                service_interest=p["service"],
                qualification_score=p["score"],
                notes=f"[{p['score']}] Cita confirmada para el {p['date']} a las {p['time']}."
            )
            session.add(lead)
            await session.flush()

            # 2. Crear Cita
            appointment = Appointment(
                lead_id=lead.id,
                patient_name=p["name"],
                phone_number=p["phone"],
                service_name=p["service"],
                specialist="Dra. Valentina Ríos (Estética & Sonrisa)",
                appointment_date=p["date"],
                appointment_time=p["time"],
                status="Confirmada"
            )
            session.add(appointment)

            # 3. Crear Historial de Conversación
            for sender, text in p["chat"]:
                msg = ConversationMessage(
                    phone_number=p["phone"],
                    sender=sender,
                    content=text,
                    channel="web_chat",
                    intent_detected="agendar_cita" if sender == "agent" else "consulta"
                )
                session.add(msg)

        await session.commit()
        print("✅ 10 Pacientes de prueba agregados con éxito.")

if __name__ == "__main__":
    asyncio.run(seed_data())
