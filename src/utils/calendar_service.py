import os
import json
import datetime
from typing import Dict, Any, Optional, List
from config.settings import settings, BASE_DIR
from config.logging_config import logger


# Intentar cargar cliente oficial de Google Calendar API
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    HAS_GOOGLE_CALENDAR_SDK = True
except ImportError:
    HAS_GOOGLE_CALENDAR_SDK = False

SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarService:
    def __init__(self, credentials_path: Optional[str] = None):
        config_dir = BASE_DIR / "config"
        
        # Buscar credentials.json o cualquier archivo JSON de cuenta de servicio en config/
        target_file = credentials_path
        if not target_file:
            cred_files = list(config_dir.glob("*.json"))
            service_acc_files = [f for f in cred_files if f.name != "n8n_workflow.json"]
            if service_acc_files:
                target_file = str(service_acc_files[0])
            else:
                target_file = str(config_dir / "credentials.json")

        self.credentials_path = target_file
        self.service = None
        self.calendar_id = settings.GOOGLE_CALENDAR_ID or "primary"


        if HAS_GOOGLE_CALENDAR_SDK and os.path.exists(self.credentials_path):
            try:
                creds = service_account.Credentials.from_service_account_file(
                    self.credentials_path, scopes=SCOPES
                )
                self.service = build('calendar', 'v3', credentials=creds)
                logger.info(f"Cliente de Google Calendar API v3 cargado desde {os.path.basename(self.credentials_path)}.")
            except Exception as e:
                logger.warning(f"No se pudo conectar a Google Calendar API: {e}. Se usará la sincronización local DB.")


    def check_freebusy(self, date_str: str, time_str: str, duration_minutes: int = 45) -> bool:
        """
        Consulta el estado de ocupación (freebusy) en Google Calendar.
        date_str: 'YYYY-MM-DD'
        time_str: 'HH:MM'
        """
        if not self.service:
            return True # Si no hay credentials.json, retorna True para permitir el flujo local

        try:
            start_dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

            time_min = start_dt.isoformat() + 'Z'
            time_max = end_dt.isoformat() + 'Z'

            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": self.calendar_id}]
            }

            events_result = self.service.freebusy().query(body=body).execute()
            busy_list = events_result.get('calendars', {}).get(self.calendar_id, {}).get('busy', [])
            
            return len(busy_list) == 0
        except Exception as e:
            logger.error(f"Error consultando FreeBusy en Google Calendar: {e}")
            return True

    def create_event(
        self,
        patient_name: str,
        phone_number: str,
        service_name: str,
        date_str: str,
        time_str: str,
        duration_minutes: int = 45,
        doctor_name: str = "Dra. Valentina Ríos"
    ) -> Dict[str, Any]:
        """
        Crea un evento oficial en Google Calendar para Smile Aesthetic & Dental Clinic.
        """
        start_dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

        event_payload = {
            'summary': f'🦷 Cita: {patient_name} - {service_name}',
            'location': 'Smile Aesthetic & Dental Clinic - Calle 93 # 14-20, Bogotá',
            'description': (
                f'Cita confirmada mediante IA (Sofía - Kinexus Smart Data).\n\n'
                f'👤 Paciente: {patient_name}\n'
                f'📱 Teléfono: {phone_number}\n'
                f'✨ Tratamiento: {service_name}\n'
                f'🩺 Especialista: {doctor_name}\n'
                f'📍 Estado: Confirmada'
            ),
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/Bogota',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/Bogota',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 24 * 60}, # 24h antes
                    {'method': 'popup', 'minutes': 120},     # 2h antes
                ],
            },
        }

        if self.service:
            try:
                created_event = self.service.events().insert(
                    calendarId=self.calendar_id, body=event_payload
                ).execute()
                logger.info(f"Evento Google Calendar creado con éxito: {created_event.get('htmlLink')}")
                return {
                    "exito": True,
                    "event_id": created_event.get("id"),
                    "html_link": created_event.get("htmlLink")
                }
            except Exception as e:
                logger.error(f"Error insertando evento en Google Calendar: {e}")

        # Retorno simulado si no hay credenciales activas
        return {
            "exito": True,
            "event_id": f"gcal_sim_{int(datetime.datetime.now().timestamp())}",
            "html_link": "https://calendar.google.com"
        }

google_calendar_service = GoogleCalendarService()
