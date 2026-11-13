"""
Direcciones del módulo «eventos», que cuelgan de /eventos/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "eventos"

urlpatterns = [
    # Listas: próximos, pasados y míos; convocar.
    path("", views.proximos, name="proximos"),
    path("pasados/", views.pasados, name="pasados"),
    path("mios/", views.mios, name="mios"),
    path("convocar/", views.convocar, name="convocar"),
    # Cada evento: ficha, editar y cartel.
    path("<int:pk>/", views.evento, name="evento"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/cartel/", views.cartel, name="cartel"),
    # Series: las mías y la ficha de cada una.
    path("series/", views.series, name="series"),
    path("series/<int:pk>/", views.serie, name="serie"),
]
