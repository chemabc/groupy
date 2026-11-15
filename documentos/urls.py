"""
Direcciones del módulo «documentos», que cuelgan de /documentos/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "documentos"

urlpatterns = [
    # Lista y crear.
    path("", views.lista, name="lista"),
    path("nuevo/", views.nuevo, name="nuevo"),
    # Cada documento: ficha (leer, comentar, aprobar, redacción) y escribir.
    path("<int:pk>/", views.documento, name="documento"),
    path("<int:pk>/escribir/", views.escribir, name="escribir"),
    # Vista previa del texto mientras se escribe (la pide htmx).
    path("vista-previa/", views.vista_previa, name="vista_previa"),
]
