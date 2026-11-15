"""
Direcciones web del módulo «base». Se incluyen desde config/urls.py.
"""

from django.urls import path

from . import views, vistas_del_editor

# Espacio de nombres: las rutas se nombran «base:inicio», «base:componentes»…
app_name = "base"

urlpatterns = [
    # Portada de cada cuenta (sección «Inicio», vista «Panel»).
    path("", views.inicio, name="inicio"),
    # Resumen de los datos de la cuenta («Inicio → Mis datos»).
    path("mis-datos/", views.mis_datos, name="mis_datos"),
    # Demostración de la plantilla («Desarrollo y mantenimiento → Componentes»): estructura y componentes.
    path("estructura/", views.estructura, name="estructura"),
    path("componentes/", views.componentes, name="componentes"),
    # Editor colaborativo en tiempo real (base/vistas_del_editor.py): el pase del navegador y las dos
    # llamadas firmadas del servidor del editor.
    path("editor/pase/", vistas_del_editor.pase, name="editor_pase"),
    path("editor/texto/", vistas_del_editor.texto, name="editor_texto"),
    path("editor/guardado/", vistas_del_editor.guardado, name="editor_guardado"),
]
