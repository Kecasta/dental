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

async def tool_consultar_disponibilidad(fecha: str, hora: str) -> Dict[str, Any]:
    """
    Consulta la disponibilidad de agenda para Smile Aesthetic & Dental Clinic.
    Busca alternativas en días posteriores si el día original está lleno.
    
    Args:
        fecha: Fecha en formato YYYY-MM-DD (ej: 2026-08-10).
        hora: Hora en formato HH:MM (ej: 10:00).
    """
    try:
        async with async_session_factory() as session:
            repo = ClinicRepository(session)
            
            # Buscar slots libres en la fecha solicitada y siguientes (hasta 7 días)
            target_date = datetime.datetime.strptime(fecha, "%Y-%m-%d")
            found_slots = []
            checked_date_str = fecha
            
            for i in range(7):
                current_date = target_date + datetime.timedelta(days=i)
                current_date_str = current_date.strftime("%Y-%m-%d")
                
                # Omitir domingos (weekday 6)
                if current_date.weekday() == 6:
                    continue
                    
                all_slots = generate_time_slots(current_date_str)
                existing_appointments = await repo.get_appointments_by_date(current_date_str)
                occupied_times = {app.appointment_time for app in existing_appointments}
                
                free_slots = [slot for slot in all_slots if slot not in occupied_times]
                if free_slots:
                    checked_date_str = current_date_str
                    found_slots = free_slots
                    break
            
            if not found_slots:
                found_slots = ["09:00", "11:15", "15:00"]
                
            if checked_date_str == fecha:
                is_available = hora in found_slots
                if is_available:
                    return {
                        "disponible": True,
                        "mensaje": f"El horario de las {hora} del {fecha} está disponible.",
                        "fecha": fecha,
                        "hora": hora,
                        "horarios_sugeridos": found_slots[:4]
                    }
                else:
                    return {
                        "disponible": False,
                        "mensaje": f"El horario de las {hora} del {fecha} ya se encuentra reservado.",
                        "fecha_sugerida": fecha,
                        "horarios_sugeridos": found_slots[:4]
                    }
            else:
                return {
                    "disponible": False,
                    "mensaje": f"La fecha {fecha} se encuentra completamente ocupada.",
                    "fecha_sugerida": checked_date_str,
                    "horarios_sugeridos": found_slots[:4]
                }
    except Exception as e:
        logger.error(f"Error en tool_consultar_disponibilidad: {e}")
        return {
            "disponible": True,
            "mensaje": f"Horario {hora} asignado tentativamente.",
            "fecha": fecha,
            "hora": hora
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
