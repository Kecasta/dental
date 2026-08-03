import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import settings
from config.logging_config import logger

def send_appointment_alert(
    patient_name: str,
    phone_number: str,
    service_name: str,
    date_str: str,
    time_str: str,
    lead_score: str
):
    """
    Envía una alerta de correo electrónico al administrador al registrarse una nueva cita.
    """
    subject = f"🔔 Nueva Cita Registrada [{lead_score}] - {patient_name}"
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #111c2c; background-color: #f9f9ff; padding: 20px;">
        <h2 style="color: #0d3b3f;">✨ Notificación de Cita: Smile Aesthetic</h2>
        <hr style="border: 0; border-top: 1px solid #c0c8c9;" />
        <p>Se ha registrado y calificado automáticamente una nueva cita en el sistema:</p>
        
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
            <tr>
                <td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Paciente:</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{patient_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Teléfono:</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{phone_number}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Tratamiento:</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; color: #0d3b3f; font-weight: bold;">{service_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Horario:</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">📅 {date_str} a las ⏰ {time_str}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Calificación Lead:</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">
                    <span style="background-color: {'#FFD166' if lead_score == 'VIP' else '#bcedda'}; color: #002428; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;">
                        {lead_score}
                    </span>
                </td>
            </tr>
        </table>
        
        <p style="margin-top: 25px; font-size: 12px; color: #717879;">
            Enviado automáticamente por <strong>Kinexus Smart Data</strong>.
        </p>
    </body>
    </html>
    """

    # Validar si tenemos las credenciales SMTP configuradas
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.info(f"[SIMULACIÓN EMAIL] Alerta enviada a {settings.ADMIN_EMAIL} - Asunto: {subject}")
        logger.debug(f"[SIMULACIÓN EMAIL CUERPO]:\n{body}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.ADMIN_EMAIL

        part = MIMEText(body, "html")
        msg.attach(part)

        # Conectar con el servidor SMTP
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, settings.ADMIN_EMAIL, msg.as_string())
        
        logger.info(f"Alerta de correo electrónico enviada exitosamente al administrador: {settings.ADMIN_EMAIL}")
        return True
    except Exception as e:
        logger.error(f"Error enviando alerta de correo electrónico: {e}")
        return False
