import flet as ft

# Paleta de Colores Kinexus - Dark Glassmorphism
BG_DARK = "#0B132B"
BG_CARD = "#1C2541"
PRIMARY_CYAN = "#00F5D4"
PRIMARY_BLUE = "#00BBF9"
GOLD_VIP = "#FFD166"
TEXT_LIGHT = "#F8F9FA"
TEXT_MUTED = "#A0AAB8"
BORDER_COLOR = "rgba(255, 255, 255, 0.12)"

def apply_kinexus_theme(page: ft.Page):
    page.title = "Smile Aesthetic & Dental Clinic — Dashboard Kinexus"
    page.bgcolor = BG_DARK
    page.padding = 20
    page.theme_mode = ft.ThemeMode.DARK
    page.fonts = {
        "Outfit": "https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700&display=swap",
        "Inter": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap"
    }
