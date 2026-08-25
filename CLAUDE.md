# CLAUDE.md — Smile Aesthetic & Dental Clinic (Kinexus Smart Data)

## 📌 Visión General del Proyecto
Sistema Inteligente de Agendamiento de Citas y Calificación de Prospectos 24/7 para **Smile Aesthetic & Dental Clinic** (Dra. Valentina Ríos). El sistema integra un widget web flotante adaptativo, un panel CRM de administración para la recepción, un agente conversacional basado en la API de Google Gemini (v1beta REST) y sincronización con Google Calendar y alertas por correo SMTP.

---

## 🏗️ Arquitectura del Sistema

### 1. Frontend & UI (`src/web/`)
- **Landing Page & Widget**: HTML5, Tailwind CSS y Vanilla JS. Desplegado en **Netlify**: `https://smileaesthetics.netlify.app/`.
- **CRM Admin Dashboard**: Interfaz en `/admin-crm` para visualizar métricas, embudo de leads, próximas citas agendadas y auditoría completa de conversaciones.
- **Diseño Móvil**: Widget conversacional con diseño responsive adaptativo en pantalla completa nativa para teléfonos (`@media (max-width: 768px)`).

### 2. Backend API (`src/main.py` & `src/agent/`)
- **Framework**: FastAPI + Uvicorn corriendo en servidor VPS Hostgator (`http://108.174.153.110:8050`).
- **Motor de IA (Agente Sofía)**: Cliente REST personalizado (`src/agent/gemini_client.py`) conectando con los modelos `gemini-1.5-flash` / `gemini-2.0-flash` (cuota gratuita de 1,500 req/día).
- **Control de Herramientas**: Function Calling nativo para `consultar_disponibilidad`, `agendar_cita` y `calificar_prospecto`.
- **Regla Estricta de Agendamiento**: Captura obligatoria de **Nombre Completo** y **Número de Teléfono Celular/WhatsApp de contacto** antes de confirmar cualquier reserva.

### 3. Persistencia de Datos (`src/database/`)
- **Motor**: SQLite 3 asíncrono (`data/smile_clinic.db`) con **SQLAlchemy 2.0** + **aiosqlite**.
- **Modelos**:
  - `Lead`: Registro de prospecto, scoring de calificación (`VIP`, `Alto`, `Medio`), servicio de interés y notas.
  - `Appointment`: Reservas de citas confirmadas con especialista, fecha, hora y monto de abono.
  - `ConversationMessage`: Historial completo de interacción auditada (usuario y Sofía IA).
- **Deduplicación**: Verificación previa en base de datos para impedir citas duplicadas por un mismo cliente en la misma fecha y hora.

### 4. Integraciones y Servicios (`src/utils/`)
- **Google Calendar API v3** (`calendar_service.py`): Creación automática de eventos con tolerancia a fallos.
- **Alertas SMTP HTML** (`email_service.py`): Envío inmediato de notificaciones por correo a la clínica (`ADMIN_EMAIL`) tras cada confirmación.

---

## 🛠️ Comandos Frecuentes de Desarrollo y Despliegue

### Entorno Local (Windows)
```powershell
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar el servidor en desarrollo
python run_dashboard.py

# Verificar sintaxis del código
python -m py_compile src/main.py src/agent/gemini_client.py
```

### Despliegue en Producción (Hostgator VPS via SSH)
```bash
# Conexión SSH al servidor (Puerto custom 22022)
ssh -p 22022 root@108.174.153.110

# Actualizar cambios desde GitHub y reiniciar el servidor en segundo plano
cd /root/dental ; fuser -k 8050/tcp ; sleep 2 ; git pull ; nohup python3 src/main.py > /root/dental/backend.log 2>&1 &

# Ver los logs del backend en tiempo real
tail -f /root/dental/backend.log
```

---

## 🔑 Variables de Entorno (`.env`)

```env
APP_NAME="Smile Aesthetic & Dental Clinic - Agendador IA"
APP_ENV="production"
PORT=8050
HOST="0.0.0.0"

# Gemini API Key & Model (Usar gemini-1.5-flash o gemini-2.0-flash para 1,500 req/día)
GEMINI_API_KEY="AIzaSy..."
GEMINI_MODEL="gemini-1.5-flash"

# Google Calendar
GOOGLE_CALENDAR_ID="primary"

# Configuración SMTP (Alertas por Correo)
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT=587
SMTP_USER="tu_correo@gmail.com"
SMTP_PASSWORD="tu_contraseña_de_aplicacion"
ADMIN_EMAIL="kecasta@gmail.com"

# Base de Datos
DATABASE_URL="sqlite+aiosqlite:///./data/smile_clinic.db"
```

---

## 📋 Catálogo de Servicios y Lead Scoring

| Servicio | Rango de Precio | Abono Previo | Scoring Lead |
| :--- | :--- | :--- | :--- |
| **Diseño de Sonrisa & Carillas** | $1,200,000 - $3,500,000 COP | $100,000 COP | `VIP` |
| **Armonización Facial & Ácido Hialurónico** | $800,000 - $2,000,000 COP | $80,000 COP | `VIP` |
| **Ortodoncia Invisible (Alineadores)** | $2,500,000 - $5,000,000 COP | $50,000 COP | `Alto` |
| **Blanqueamiento Dental LED** | $350,000 COP | No Aplica | `Alto` |
| **Limpieza Ultrasonido & Profilaxis** | $150,000 COP | No Aplica | `Medio` |
| **Valoración Odontológica General** | $80,000 COP | No Aplica | `Medio` |
