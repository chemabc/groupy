"""
Direcciones del módulo «solicitudes», que cuelgan de /solicitudes/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "solicitudes"

urlpatterns = [
    # Listas: pendientes, pasadas y las mías; pedir algo; cada solicitud.
    path("", views.pendientes, name="pendientes"),
    path("pasadas/", views.pasadas, name="pasadas"),
    path("mias/", views.mias, name="mias"),
    path("nueva/", views.nueva, name="nueva"),
    path("<int:pk>/", views.solicitud, name="solicitud"),
    # Configuración → Solicitudes: apoyos y plazos.
    path("ajustes/", views.ajustes, name="ajustes"),
]
