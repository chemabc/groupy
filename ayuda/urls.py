"""
Direcciones del módulo «ayuda», que cuelgan de /ayuda/ (ver config/urls.py).
"""

from django.urls import path

from . import views
from .documentos import DOCUMENTOS, nombre_de_ruta

app_name = "ayuda"

urlpatterns = [
    # Una página por documento (/ayuda/tutorial/), cada una con su nombre de ruta («ayuda:tutorial»), para
    # que el menú superior marque la pestaña correcta.
    *(
        path(f"{documento.clave}/", views.documento, {"clave": documento.clave}, name=nombre_de_ruta(documento.clave))
        for documento in DOCUMENTOS
    ),
]
