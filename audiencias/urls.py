"""
Direcciones del módulo «audiencias», que cuelgan de /configuracion/visibilidad/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "audiencias"

urlpatterns = [
    # Configuración → Visibilidad: qué niveles ofrece cada organización.
    path("", views.visibilidad, name="visibilidad"),
]
