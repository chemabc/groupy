"""
Decorador para las vistas que necesitan un permiso.

Ejemplo, en la vista de convocar una reunión de un grupo (la dirección lleva el id del grupo):

    @requiere_permiso("eventos.convocar_reunion", grupo=lambda request, grupo_id: grupo_id)
    def convocar(request, grupo_id): ...

Si falta el permiso, se muestra la pantalla 403 con la explicación (qué falta y a quién pedirlo).
"""

from functools import wraps

from .servicios import exigir


# Devuelve un decorador que comprueba un permiso antes de ejecutar la vista.
#   - permiso: código del permiso.
#   - grupo: función opcional que recibe la petición y los parámetros de la dirección y devuelve el
#     grupo (o su id) donde se comprueba.
#   - organizacion: igual, para los permisos de organización.
def requiere_permiso(permiso, grupo=None, organizacion=None):
    def decorador(vista):
        @wraps(vista)
        def vista_con_permiso(request, *args, **kwargs):
            exigir(
                request.user,
                permiso,
                grupo=grupo(request, **kwargs) if grupo else None,
                organizacion=organizacion(request, **kwargs) if organizacion else None,
            )
            return vista(request, *args, **kwargs)

        return vista_con_permiso

    return decorador
