"""
Direcciones del módulo «mantenimiento», que cuelgan de /mantenimiento/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "mantenimiento"

urlpatterns = [
    # Pruebas: importar grupos y usuarios, sus plantillas y el interruptor del alta masiva.
    path("pruebas/grupos/", views.importar_grupos, name="importar_grupos"),
    path("pruebas/grupos/plantilla.ods", views.plantilla_grupos, name="plantilla_grupos"),
    path("pruebas/usuarios/", views.importar_usuarios, name="importar_usuarios"),
    path("pruebas/usuarios/plantilla.ods", views.plantilla_usuarios, name="plantilla_usuarios"),
    path("pruebas/usuarios/permitir/", views.permitir_alta_masiva, name="permitir_alta_masiva"),
    path("pruebas/ejemplos/", views.datos_de_ejemplo, name="datos_de_ejemplo"),
    # La entrada a la trastienda.
    path("trastienda/", views.trastienda, name="trastienda"),
]
