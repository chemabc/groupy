"""
Direcciones web del módulo «base». Se incluyen desde config/urls.py.
"""

from django.urls import path

from . import views

# Espacio de nombres: las rutas se nombran «base:inicio», «base:componentes»…
app_name = "base"

urlpatterns = [
    # Portada de cada cuenta (sección «Inicio», vista «Panel»).
    path("", views.inicio, name="inicio"),
    # Resumen de los datos de la cuenta («Inicio → Mis datos»).
    path("mis-datos/", views.mis_datos, name="mis_datos"),
    # Demostración de la plantilla («Desarrollo y mantenimiento → Componentes»): estructura y componentes.
    path("estructura/", views.estructura, name="estructura"),
    path("componentes/", views.componentes, name="componentes"),
]
