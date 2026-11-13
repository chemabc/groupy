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
]
