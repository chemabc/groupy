"""
Direcciones del módulo «comunicaciones», que cuelgan de /comunicaciones/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "comunicaciones"

urlpatterns = [
    # Notificaciones: la bandeja, abrir una (la marca como vista) y las preferencias.
    path("", views.notificaciones, name="notificaciones"),
    path("notificacion/<int:pk>/", views.abrir, name="abrir"),
    path("preferencias/", views.preferencias, name="preferencias"),
    # Conversaciones con la administración: lista, nueva y cada una.
    path("conversaciones/", views.conversaciones, name="conversaciones"),
    # Lo que llega a las administraciones que atiende quien mira (en «Administrar»).
    path("conversaciones/atendidas/", views.atendidas, name="atendidas"),
    path("conversaciones/nueva/", views.nueva_conversacion, name="nueva_conversacion"),
    path("conversaciones/<int:pk>/", views.conversacion, name="conversacion"),
    # Conversaciones con grupos: la lista de salas y la de cada grupo.
    path("grupos/", views.con_grupos_lista, name="con_grupos"),
    path("grupos/<int:pk>/", views.sala, name="sala"),
    # Conversaciones con personas: lista, escribir a alguien (con la lista del selector) y cada una.
    path("personas/", views.con_personas_lista, name="con_personas"),
    path("personas/escribir/", views.escribir_a_persona, name="escribir_a_persona"),
    path("personas/lista/", views.personas_para_escribir, name="personas_para_escribir"),
    path("personas/<int:pk>/", views.con_persona, name="con_persona"),
    # Avisos de la administración: enviar y ver cada uno.
    path("avisos/", views.avisos, name="avisos"),
    path("avisos/<int:pk>/", views.aviso, name="aviso"),
    # Plataforma → Catálogos comunes → Niveles de aviso.
    path("niveles/", views.niveles, name="niveles"),
]
