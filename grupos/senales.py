"""
Señales de Django del módulo «grupos»: avisos que Django da al guardar o borrar filas, también desde la
trastienda. Se conectan al arrancar, en GruposConfig.ready() (grupos/apps.py).
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .contadores import invalidar_invitaciones
from .models import InvitacionDeGrupo


# Al crear, cambiar o borrar una invitación, los números de «Invitaciones (N)» del menú se recalculan.
@receiver([post_save, post_delete], sender=InvitacionDeGrupo, dispatch_uid="grupos_invitaciones_cambian")
def invitacion_cambiada(sender, **datos):
    invalidar_invitaciones()
