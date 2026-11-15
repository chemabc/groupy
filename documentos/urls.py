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
    path("<int:pk>/versiones/<int:numero>/", views.version, name="version"),
    # Vista previa del texto mientras se escribe (la pide htmx).
    path("vista-previa/", views.vista_previa, name="vista_previa"),
    # Cuántas personas escriben y comentan a la vez (plataforma, organización o grupo).
    path("limites/", views.limites, name="limites"),
    # La biblioteca del editor: plantillas, cabeceras y pies, imágenes y la enciclopedia de fragmentos.
    path("plantillas/", views.biblioteca, {"clase": "plantilla"}, name="plantillas"),
    path("plantillas/cabeceras-y-pies/", views.biblioteca, {"clase": "membrete"}, name="membretes"),
    path("plantillas/imagenes/", views.biblioteca, {"clase": "imagen"}, name="imagenes"),
    path("fragmentos/", views.biblioteca, {"clase": "fragmento"}, name="fragmentos"),
]
