"""
Direcciones del módulo «calendario», que cuelgan de /calendario/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "calendario"

urlpatterns = [
    # El calendario, sus fechas en JSON y mover arrastrando.
    path("", views.calendario, name="calendario"),
    path("datos/", views.datos, name="datos"),
    path("mover/", views.mover, name="mover"),
    # Recordatorios: lista, apuntar uno y ficha.
    path("recordatorios/", views.recordatorios, name="recordatorios"),
    path("recordatorios/nuevo/", views.nuevo, name="nuevo"),
    path("recordatorios/<int:pk>/", views.recordatorio, name="recordatorio"),
    # Suscripción: la pantalla y el fichero .ics (sin sesión, con la clave secreta).
    path("suscripcion/", views.suscripcion, name="suscripcion"),
    path("ics/<str:clave>.ics", views.ics, name="ics"),
]
