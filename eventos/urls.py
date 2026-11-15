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
    path("mios/pasados/", views.mios, {"pasados": True}, name="mios_pasados"),
    # «Administrar → Eventos de mis grupos»: los de los grupos que administro, en cuatro pestañas.
    path("administrados/", views.administrados, {"cual": "proximos"}, name="administrados"),
    path("administrados/esperan-apoyos/", views.administrados, {"cual": "pendientes"}, name="administrados_pendientes"),
    path("administrados/pasados/", views.administrados, {"cual": "pasados"}, name="administrados_pasados"),
    path("administrados/cancelados/", views.administrados, {"cual": "cancelados"}, name="administrados_cancelados"),
    path("convocar/", views.convocar, name="convocar"),
    # Cada evento: ficha, editar y cartel.
    path("<int:pk>/", views.evento, name="evento"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/cartel/", views.cartel, name="cartel"),
    # Series: las mías y la ficha de cada una.
    path("series/", views.series, name="series"),
    path("series/<int:pk>/", views.serie, name="serie"),
]
