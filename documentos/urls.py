"""
Direcciones del módulo «documentos», que cuelgan de /documentos/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "documentos"

urlpatterns = [
    # Lista y crear (escribir un texto, subir un archivo o enlazar).
    path("", views.lista, name="lista"),
    path("nuevo/", views.nuevo, name="nuevo"),
    path("nuevo/archivo/", views.subir, name="subir"),
    path("nuevo/enlace/", views.enlazar, name="enlazar"),
    # Lo eliminado (se recupera durante 30 días) y cuánto pueden ocupar los archivos (el superadmin).
    path("papelera/", views.papelera, name="papelera"),
    path("espacio/", views.espacio, name="espacio"),
    # Cada documento: ficha (leer, comentar, aprobar, redacción; o el archivo o el enlace) y escribir.
    path("<int:pk>/", views.documento, name="documento"),
    path("<int:pk>/escribir/", views.escribir, name="escribir"),
    # El archivo (la última versión, o una anterior), para verlo o descargarlo.
    path("<int:pk>/archivo/", views.descargar, name="descargar"),
    path("<int:pk>/archivo/<int:numero>/", views.descargar, name="descargar_version"),
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
