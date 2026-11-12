"""
Invalidación de la caché de permisos cuando cambia algo de lo que dependen.

Se usan señales de Django (post_save y post_delete) en lugar de solo los avisos de eventos_sw porque así
también se invalida lo que se cambia desde la trastienda, que no pasa por los servicios. Se conectan en
PermisosConfig.ready() (permisos/apps.py).
"""

from django.db.models.signals import post_delete, post_save

from grupos.models import AdminDeOrganizacion, Grupo, Pertenencia

from .models import Cometido, ExcepcionDePermiso, PermisoDeRol, Rol
from .servicios import invalidar_todos, invalidar_usuario


# Receptor para lo que solo afecta a una persona: sus pertenencias, su admin de organización, sus
# excepciones y sus cometidos. Borra su cálculo de la caché.
#   - instance: la fila guardada o borrada (tiene usuario_id).
def _invalidar_a_su_usuario(sender, instance, **resto):
    invalidar_usuario(instance.usuario_id)


# Receptor para lo que afecta a todo el mundo: los grupos (crear o mover uno cambia la herencia), los
# roles y sus permisos.
def _invalidar_a_todos(sender, **resto):
    invalidar_todos()


# Conecta los receptores a las tablas. La llama PermisosConfig.ready().
def conectar():
    for modelo in (Pertenencia, AdminDeOrganizacion, ExcepcionDePermiso, Cometido):
        post_save.connect(_invalidar_a_su_usuario, sender=modelo, dispatch_uid=f"permisos.{modelo.__name__}.guardar")
        post_delete.connect(_invalidar_a_su_usuario, sender=modelo, dispatch_uid=f"permisos.{modelo.__name__}.borrar")
    for modelo in (Grupo, Rol, PermisoDeRol):
        post_save.connect(_invalidar_a_todos, sender=modelo, dispatch_uid=f"permisos.{modelo.__name__}.guardar")
        post_delete.connect(_invalidar_a_todos, sender=modelo, dispatch_uid=f"permisos.{modelo.__name__}.borrar")
