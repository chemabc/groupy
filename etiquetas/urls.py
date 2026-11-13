"""
Direcciones del módulo «etiquetas», que cuelgan de /etiquetas/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "etiquetas"

urlpatterns = [
    # Sugerencias mientras se escribe (JSON).
    path("sugerencias/", views.sugerencias, name="sugerencias"),
]
