import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import flet as ft
from src.ui.app import dashboard_app


if __name__ == "__main__":
    ft.app(target=dashboard_app.main)
