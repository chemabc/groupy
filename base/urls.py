"""
Direcciones web del módulo «base». Se incluyen desde config/urls.py.
"""

from django.urls import path

from . import views

# Espacio de nombres: las rutas se nombran «base:inicio», «base:componentes»…
app_name = "base"

urlpatterns = [
    # Portada de la aplicación (sección «Inicio», vista «Estructura»).
    path("", views.inicio, name="inicio"),
    # Escaparate de componentes (sección «Inicio», vista «Componentes»).
    path("componentes/", views.componentes, name="componentes"),
]
