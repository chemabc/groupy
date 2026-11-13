"""
Direcciones del módulo «tipologias», que cuelgan de /configuracion/tipologias/ (ver config/urls.py).
"""

from django.urls import path

from . import views
from .models import Tipologia

app_name = "tipologias"

urlpatterns = [
    # Las tipologías de cada familia (cada una, una pestaña del menú superior).
    path("eventos/", views.tipologias, {"familia": Tipologia.EVENTO}, name="eventos"),
    path("proyectos/", views.tipologias, {"familia": Tipologia.PROYECTO}, name="proyectos"),
    # Guarda el orden de los campos al arrastrarlos.
    path("ordenar/", views.ordenar, name="ordenar"),
]
