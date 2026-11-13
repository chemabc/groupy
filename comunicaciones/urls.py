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
    path("conversaciones/nueva/", views.nueva_conversacion, name="nueva_conversacion"),
    path("conversaciones/<int:pk>/", views.conversacion, name="conversacion"),
    # Avisos de la administración: enviar y ver cada uno.
    path("avisos/", views.avisos, name="avisos"),
    path("avisos/<int:pk>/", views.aviso, name="aviso"),
    # Configuración → Niveles de aviso.
    path("niveles/", views.niveles, name="niveles"),
]
