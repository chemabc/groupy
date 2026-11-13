"""
Direcciones del módulo «limpieza», que cuelgan de /limpieza/ (ver config/urls.py).
"""

from django.urls import path

from . import views

app_name = "limpieza"

urlpatterns = [
    # El archivo: lo archivado que se ve, con «Conservar» (y, para el superadmin, «Borrar ya»).
    path("", views.archivados, name="archivados"),
    path("<int:pk>/", views.archivado, name="archivado"),
    # El registro de lo borrado.
    path("borrados/", views.borrados, name="borrados"),
    # «Configuración → Limpieza»: los plazos de cada tipo (solo el superadmin).
    path("plazos/", views.plazos, name="plazos"),
]
