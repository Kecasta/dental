import asyncio
import datetime
import flet as ft
from src.ui.theme import (
    BG_DARK, BG_CARD, PRIMARY_CYAN, GOLD_VIP, TEXT_LIGHT, TEXT_MUTED, apply_kinexus_theme
)
from src.database.connection import get_db_session, init_db
from src.database.repository import ClinicRepository
from src.agent.gemini_client import GeminiClinicAgent

class ClinicDashboardApp:
    def __init__(self):
        self.agent = GeminiClinicAgent()
        self.active_phone = "+573001234567"

    async def main(self, page: ft.Page):
        apply_kinexus_theme(page)
        await init_db()

        # Componentes UI
        title_header = ft.Row(
            controls=[
                ft.Text("✨", size=28),
                ft.Text("Smile Aesthetic & Dental Clinic", size=22, weight=ft.FontWeight.BOLD, color=PRIMARY_CYAN),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Row([
                        ft.Container(width=10, height=10, border_radius=5, bgcolor="#00E676"),
                        ft.Text("IA Conversacional 24/7 Activa", size=12, color=TEXT_LIGHT, weight=ft.FontWeight.W_500)
                    ]),
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    bgcolor=BG_CARD,
                    border_radius=20
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        # Tablas y Listas
        kpi_row = ft.Row(controls=[], spacing=16)
        appointments_list = ft.ListView(expand=True, spacing=10)
        leads_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Teléfono")),
                ft.DataColumn(ft.Text("Paciente")),
                ft.DataColumn(ft.Text("Servicio Interés")),
                ft.DataColumn(ft.Text("Calificación")),
                ft.DataColumn(ft.Text("Fecha Registro"))
            ],
            rows=[]
        )

        # Chat Simulator Controls
        chat_messages_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
        chat_input = ft.TextField(
            hint_text="Escribe un mensaje como paciente...",
            expand=True,
            border_color=PRIMARY_CYAN,
            bgcolor=BG_DARK,
            color=TEXT_LIGHT
        )

        async def refresh_data():
            async for session in get_db_session():
                repo = ClinicRepository(session)
                
                # 1. Obtener Citas
                appointments = await repo.get_all_appointments()
                appointments_list.controls.clear()

                if not appointments:
                    appointments_list.controls.append(
                        ft.Text("No hay citas registradas hoy.", color=TEXT_MUTED, italic=True)
                    )
                else:
                    for app in appointments:
                        status_color = GOLD_VIP if app.status == "Confirmada" else PRIMARY_CYAN
                        appointments_list.controls.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.CALENDAR_MONTH, color=PRIMARY_CYAN),
                                    ft.Column([
                                        ft.Text(f"{app.patient_name} - {app.service_name}", weight=ft.FontWeight.BOLD, color=TEXT_LIGHT),
                                        ft.Text(f"📅 {app.appointment_date}  |  ⏰ {app.appointment_time}  |  🩺 {app.specialist}", size=12, color=TEXT_MUTED)
                                    ], expand=True),
                                    ft.Container(
                                        content=ft.Text(app.status, size=11, color=BG_DARK, weight=ft.FontWeight.BOLD),
                                        bgcolor=status_color,
                                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                        border_radius=8
                                    )
                                ]),
                                bgcolor=BG_CARD,
                                padding=12,
                                border_radius=12
                            )
                        )

                # 2. Obtener Leads
                leads = await repo.get_all_leads()
                leads_table.rows.clear()
                vip_count = 0
                for lead in leads:
                    if lead.qualification_score == "VIP":
                        vip_count += 1
                    score_color = GOLD_VIP if lead.qualification_score == "VIP" else PRIMARY_CYAN
                    leads_table.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(lead.phone_number, color=TEXT_LIGHT)),
                                ft.DataCell(ft.Text(lead.full_name or "Prospecto", color=TEXT_LIGHT)),
                                ft.DataCell(ft.Text(lead.service_interest or "General", color=TEXT_MUTED)),
                                ft.DataCell(
                                    ft.Container(
                                        content=ft.Text(lead.qualification_score or "Medio", color=BG_DARK, weight=ft.FontWeight.BOLD, size=11),
                                        bgcolor=score_color,
                                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                        border_radius=6
                                    )
                                ),
                                ft.DataCell(ft.Text(lead.created_at.strftime("%Y-%m-%d %H:%M") if lead.created_at else "-", color=TEXT_MUTED))
                            ]
                        )
                    )

                # 3. Actualizar KPIs
                kpi_row.controls = [
                    self._build_kpi_card("Citas Confirmadas", str(len(appointments)), "📅", PRIMARY_CYAN),
                    self._build_kpi_card("Leads Calificados VIP", str(vip_count), "⭐", GOLD_VIP),
                    self._build_kpi_card("Conversión Citas", "94.2%", "📈", PRIMARY_CYAN),
                    self._build_kpi_card("Canales Conectados", "Web + WA", "📱", PRIMARY_CYAN)
                ]

                page.update()

        async def send_simulated_message(e):
            text = chat_input.value
            if not text:
                return
            
            chat_input.value = ""
            # Agregar mensaje usuario
            chat_messages_column.controls.append(
                ft.Container(
                    content=ft.Text(f"Paciente: {text}", color=BG_DARK, weight=ft.FontWeight.W_500),
                    bgcolor=PRIMARY_CYAN,
                    padding=10,
                    border_radius=10,
                    alignment=ft.alignment.center_right
                )
            )
            page.update()

            # Procesar con Agente IA
            result = await self.agent.process_message(self.active_phone, text)
            reply = result["response_text"]

            # Agregar mensaje IA
            chat_messages_column.controls.append(
                ft.Container(
                    content=ft.Text(f"Sofía IA: {reply}", color=TEXT_LIGHT),
                    bgcolor=BG_CARD,
                    padding=10,
                    border_radius=10,
                    alignment=ft.alignment.center_left
                )
            )
            await refresh_data()

        # Estructura Tabs
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="📊 Panel Principal",
                    content=ft.Container(
                        content=ft.Column([
                            kpi_row,
                            ft.Divider(color=BORDER_COLOR),
                            ft.Text("📅 Citas Agendadas en Tiempo Real", size=18, weight=ft.FontWeight.BOLD, color=PRIMARY_CYAN),
                            ft.Container(content=appointments_list, height=320, bgcolor=BG_DARK, border_radius=12, padding=10)
                        ], spacing=16),
                        padding=16
                    )
                ),
                ft.Tab(
                    text="💬 Simulador Multicanal",
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("Simulador de Chat en Tiempo Real (Prueba de Inferencia)", size=16, weight=ft.FontWeight.BOLD, color=PRIMARY_CYAN),
                            ft.Container(content=chat_messages_column, height=350, bgcolor=BG_DARK, border_radius=12, padding=12),
                            ft.Row([
                                chat_input,
                                ft.IconButton(icon=ft.Icons.SEND, icon_color=PRIMARY_CYAN, on_click=send_simulated_message)
                            ])
                        ], spacing=12),
                        padding=16
                    )
                ),
                ft.Tab(
                    text="👥 CRM & Leads Calificados",
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("Calificación Multimodal de Prospectos (Lead Scoring VIP)", size=16, weight=ft.FontWeight.BOLD, color=PRIMARY_CYAN),
                            ft.Container(content=leads_table, scroll=ft.ScrollMode.AUTO, expand=True)
                        ], spacing=12),
                        padding=16
                    )
                )
            ],
            expand=True
        )

        page.add(title_header, ft.Divider(color=BORDER_COLOR), tabs)
        await refresh_data()

    def _build_kpi_card(self, title: str, value: str, icon: str, accent_color: str) -> ft.Container:
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(icon, size=20),
                    ft.Text(title, size=12, color=TEXT_MUTED, weight=ft.FontWeight.W_500)
                ]),
                ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=accent_color)
            ], spacing=6),
            bgcolor=BG_CARD,
            padding=16,
            border_radius=14,
            expand=True
        )

dashboard_app = ClinicDashboardApp()
