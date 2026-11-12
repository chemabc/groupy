"""
Direcciones para las pruebas de la pantalla «sin permiso»: las de la aplicación más una vista que exige
el permiso «grupos.editar_grupo» en el grupo de la dirección.
"""

from django.http import HttpResponse
from django.urls import include, path

from permisos.decoradores import requiere_permiso


# Vista de prueba: si se tiene el permiso, responde «Editando»; si no, el decorador lanza SinPermiso.
@requiere_permiso("grupos.editar_grupo", grupo=lambda request, grupo_id: grupo_id)
def editar(request, grupo_id):
    return HttpResponse("Editando")


urlpatterns = [
    path("prueba-permiso/<int:grupo_id>/", editar),
    path("", include("config.urls")),
]
