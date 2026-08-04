import datetime
from typing import Dict, Any, List, Optional
from src.database.connection import async_session_factory
from src.database.repository import ClinicRepository
from src.agent.prompts import CLINIC_SERVICES
from src.utils.calendar_service import google_calendar_service
from config.logging_config import logger


def generate_time_slots(date_str: str) -> List[str]:
    """Genera slots de atención estándar entre 8:00 AM y 5:15 PM cada 45 mins."""
    slots = []
    start = datetime.time(8, 0)
    end = datetime.time(17, 15)
    current = datetime.datetime.strptime(f"{date_str} {start.strftime('%H:%M')}", "%Y-%m-%d %H:%M")
    end_dt = datetime.datetime.strptime(f"{date_str} {end.strftime('%H:%M')}", "%Y-%m-%d %H:%M")

    while current <= end_dt:
        slots.append(current.strftime("%H:%M"))
        current += datetime.timedelta(minutes=45)
    return slots

async def tool_consultar_disponibilidad(fecha: str = None, hora: str = None) -> Dict[str, Any]:
    """
    Consulta la disponibilidad de agenda para Smile Aesthetic & Dental Clinic.
    Genera 4 opciones numeradas entre mañanas y tardes de los próximos días hábiles.
    """
    try:
        if not fecha:
            fecha = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        if not hora:
            hora = "09:00"

        # Sanear formato de fecha si viene con hora o espacios
        if "T" in str(fecha):
            fecha = str(fecha).split("T")[0]
        elif " " in str(fecha):
            fecha = str(fecha).split(" ")[0]

        async with async_session_factory() as session:
            repo = ClinicRepository(session)
            
            today = datetime.date.today()
            tomorrow = today + datetime.timedelta(days=1)

            try:
                target_date = datetime.datetime.strptime(fecha, "%Y-%m-%d").date()
                if target_date < today:
                    target_date = tomorrow
            except Exception:
                target_date = tomorrow
                fecha = target_date.strftime("%Y-%m-%d")


            dias_semana_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            meses_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

            opciones_numeradas = []
            option_id = 1

            for i in range(7):
                curr_date = target_date + datetime.timedelta(days=i)
                if curr_date.weekday() == 6: # Omitir domingos
                    continue

                curr_date_str = curr_date.strftime("%Y-%m-%d")
                day_name = dias_semana_es[curr_date.weekday()]
                month_name = meses_es[curr_date.month - 1]
                formatted_date_label = f"{day_name} {curr_date.day} de {month_name}"

                all_slots = generate_time_slots(curr_date_str)
                existing = await repo.get_appointments_by_date(curr_date_str)
                occupied = {app.appointment_time for app in existing}
                free = [s for s in all_slots if s not in occupied]

                morning_slots = [s for s in free if int(s.split(":")[0]) < 12]
                afternoon_slots = [s for s in free if int(s.split(":")[0]) >= 12]

                if morning_slots and option_id <= 4:
                    slot = morning_slots[0]
                    opciones_numeradas.append({
                        "id": option_id,
                        "label": f"{formatted_date_label} — {slot} AM (Mañana)",
                        "fecha": curr_date_str,
                        "hora": slot
                    })
                    option_id += 1

                if afternoon_slots and option_id <= 4:
                    slot = afternoon_slots[0]
                    h_int = int(slot.split(":")[0])
                    m_str = slot.split(":")[1]
                    h_12 = h_int - 12 if h_int > 12 else h_int
                    if h_12 == 0:
                        h_12 = 12
                    opciones_numeradas.append({
                        "id": option_id,
                        "label": f"{formatted_date_label} — {h_12}:{m_str} PM (Tarde)",
                        "fecha": curr_date_str,
                        "hora": slot
                    })
                    option_id += 1

                if option_id > 4:
                    break

            return {
                "disponible": True,
                "mensaje": "Opciones de agendamiento generadas con éxito.",
                "opciones_numeradas": opciones_numeradas
            }
    except Exception as e:
        logger.error(f"Error en tool_consultar_disponibilidad: {e}")
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        return {
            "disponible": True,
            "opciones_numeradas": [
                {"id": 1, "label": "Mañana 09:00 AM (Mañana)", "fecha": tomorrow, "hora": "09:00"},
                {"id": 2, "label": "Mañana 02:30 PM (Tarde)", "fecha": tomorrow, "hora": "14:30"},
                {"id": 3, "label": "Pasado Mañana 08:45 AM (Mañana)", "fecha": tomorrow, "hora": "08:45"},
                {"id": 4, "label": "Pasado Mañana 03:15 PM (Tarde)", "fecha": tomorrow, "hora": "15:15"}
            ]
        }




async def tool_agendar_cita(
    nombre: str,
    telefono: str,
    servicio: str,
    fecha: str,
    hora: str
) -> Dict[str, Any]:
    """
    Reserva y confirma una cita médica/estética en Smile Aesthetic & Dental Clinic.
    """
    try:
        service_info = CLINIC_SERVICES.get(servicio, {})
        requires_deposit = service_info.get("requires_deposit", False)
        deposit_amount = service_info.get("deposit_amount", "$0 COP")

        async with async_session_factory() as session:
            repo = ClinicRepository(session)
            appointment = await repo.create_appointment(
                phone_number=telefono,
                patient_name=nombre,
                service_name=servicio,
                appointment_date=fecha,
                appointment_time=hora
            )
            
            # Sincronizar con Google Calendar API v3
            gcal_res = google_calendar_service.create_event(
                patient_name=nombre,
                phone_number=telefono,
                service_name=servicio,
                date_str=fecha,
                time_str=hora
            )

            # Calificación automática basada en el servicio
            qualification = service_info.get("category", "Medio")
            await repo.update_lead_qualification(
                phone_number=telefono,
                score=qualification,
                service=servicio,
                notes=f"Cita confirmada para el {fecha} a las {hora}. GCal: {gcal_res.get('event_id')}"
            )

            # Enviar alerta de correo electrónico al administrador
            from src.utils.email_service import send_appointment_alert
            send_appointment_alert(
                patient_name=nombre,
                phone_number=telefono,
                service_name=servicio,
                date_str=fecha,
                time_str=hora,
                lead_score=qualification
            )

            res_msg = f"¡Cita confirmada con éxito para {nombre}! Servicio: {servicio}. Fecha: {fecha} a las {hora}."

            if requires_deposit:
                res_msg += f" Este servicio requiere un abono previo de {deposit_amount} para congelar la agenda de la especialista."

            return {
                "exito": True,
                "id_cita": appointment.id,
                "mensaje": res_msg,
                "gcal_link": gcal_res.get("html_link"),
                "requiere_abono": requires_deposit,
                "monto_abono": deposit_amount,
                "link_pago_simulado": f"https://smileclinic.kinexus.co/pay?id={appointment.id}" if requires_deposit else None
            }
    except Exception as e:
        logger.error(f"Error en tool_agendar_cita: {e}")
        return {
            "exito": False,
            "mensaje": f"No se pudo completar la reserva automáticamente: {str(e)}"
        }


async def tool_calificar_prospecto(
    telefono: str,
    puntaje: str,
    servicio: str,
    notas: str
) -> Dict[str, Any]:
    """
    Registra o actualiza la calificación del prospecto (Lead Scoring) en el CRM interno.
    
    Args:
        telefono: Teléfono del paciente.
        puntaje: Categoría de valor ('VIP', 'Alto', 'Medio', 'Bajo').
        servicio: Servicio de interés principal.
        notas: Comentarios relevantes sobre el perfil del cliente.
    """
    try:
        async with async_session_factory() as session:
            repo = ClinicRepository(session)
            lead = await repo.update_lead_qualification(
                phone_number=telefono,
                score=puntaje,
                service=servicio,
                notes=notas
            )
            return {
                "exito": True,
                "mensaje": f"Lead {lead.full_name} calificado exitosamente como {puntaje}."
            }
    except Exception as e:
        logger.error(f"Error en tool_calificar_prospecto: {e}")
        return {"exito": False, "mensaje": str(e)}
