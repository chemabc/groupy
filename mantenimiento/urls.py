"""
Direcciones del módulo «mantenimiento», que cuelgan de /mantenimiento/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "mantenimiento"

urlpatterns = [
    # Documentación: el primer documento, o el que se nombre. Las dos llevan el mismo nombre de ruta
    # para que el menú marque «Documentación» en las dos.
    path("documentacion/", views.documentacion, name="documentacion"),
    path("documentacion/<slug:nombre>/", views.documentacion, name="documentacion"),
    # La entrada a la trastienda.
    path("trastienda/", views.trastienda, name="trastienda"),
]
