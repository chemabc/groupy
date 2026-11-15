"""
Direcciones del módulo «debates», que cuelgan de /debates/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "debates"

urlpatterns = [
    # Lista y proponer.
    path("", views.lista, name="lista"),
    path("nuevo/", views.nuevo, name="nuevo"),
    # Ficha de un debate (votar, argumentar, opciones, facilitación, cerrar).
    path("<int:pk>/", views.debate, name="debate"),
    # Límites de la plataforma y de cada organización.
    path("limites/", views.limites, name="limites"),
]
