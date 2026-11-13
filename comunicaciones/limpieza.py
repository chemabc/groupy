"""
Lo que el módulo «limpieza» necesita de «comunicaciones» (ver comunicaciones/apps.py, apartado
«limpiables»): borrar las notificaciones viejas. No se archivan antes ni se avisa: de partida, las vistas
se borran a los 90 días de verlas y las no vistas a los 365 de llegar.
"""

from django.db import transaction

from .models import Notificacion
from .servicios import _invalidar


# Borra las notificaciones vistas antes de «antes». Devuelve cuántas ha borrado.
def borrar_vistas(antes):
    return Notificacion.objects.filter(vista_el__lt=antes).delete()[1].get("comunicaciones.Notificacion", 0)


# Borra las notificaciones sin ver que llegaron antes de «antes» y pone al día el número sin ver de sus
# personas. Devuelve cuántas ha borrado.
@transaction.atomic
def borrar_sin_ver(antes):
    viejas = Notificacion.objects.filter(vista_el__isnull=True, creada__lt=antes)
    personas = set(viejas.values_list("usuario_id", flat=True))
    borradas = viejas.delete()[1].get("comunicaciones.Notificacion", 0)
    _invalidar(personas)
    return borradas
