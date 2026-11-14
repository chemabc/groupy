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
    # Lo que espera el sí de la administración (en «Administrar»).
    path("por-aprobar/", views.por_aprobar, name="por_aprobar"),
    path("mias/", views.mias, name="mias"),
    path("nueva/", views.nueva, name="nueva"),
    path("<int:pk>/", views.solicitud, name="solicitud"),
    # Administrar → Mi organización → Apoyos y plazos.
    path("ajustes/", views.ajustes, name="ajustes"),
]
