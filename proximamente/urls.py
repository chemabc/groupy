"""
Direcciones del módulo «proximamente», que cuelgan de /proximamente/ (ver config/urls.py): una por cada
herramienta pendiente, con su propio nombre para que el menú marque su entrada.
"""

from django.urls import path

from . import views
from .apps import PENDIENTES

app_name = "proximamente"

urlpatterns = [
    path(f"{pendiente.clave.replace('_', '-')}/", views.pendiente, {"clave": pendiente.clave}, name=pendiente.clave)
    for pendiente in PENDIENTES
]
