"""
Lo que «proyectos» aporta al calendario común (ver las FuenteDeCalendario de proyectos/apps.py): las
fechas límite de los proyectos y de las tareas que ve cada persona, como días enteros, y moverlas al
arrastrarlas. El módulo «calendario» llama a estas funciones por su ruta.
"""

from datetime import datetime, time

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from base.contrato import FechaDeCalendario

from . import servicios
from .models import Proyecto, Tarea


# Un día como momento: a las 00:00 de aquí (lo que espera una fecha de día entero).
def _momento(dia):
    return timezone.make_aware(datetime.combine(dia, time()))


# Fechas límite de los proyectos que ve una persona entre dos momentos («Límite: Huerto»). Se pueden
# arrastrar los que gestiona (si no es superadmin, una consulta más por proyecto solo si coordina algo).
#   - usuario: quién mira.
#   - desde, hasta: el trozo de calendario.
def proyectos(usuario, desde, hasta):
    lista = servicios.visibles(usuario).filter(limite__gte=timezone.localtime(desde).date(), limite__lt=timezone.localtime(hasta).date())
    return [
        FechaDeCalendario(
            id=proyecto.pk,
            titulo=f"Límite: {proyecto.titulo}",
            inicio=_momento(proyecto.limite),
            todo_el_dia=True,
            enlace=reverse("proyectos:proyecto", args=[proyecto.pk]),
            categoria="Proyectos",
            se_puede_mover=proyecto.creador_id == usuario.pk,
        )
        for proyecto in lista.order_by("limite")
    ]


# Fechas límite de las tareas que ve una persona que aún no están hechas. Se pueden arrastrar las suyas.
def tareas(usuario, desde, hasta):
    lista = (
        servicios.tareas_visibles(usuario)
        .exclude(estado=Tarea.HECHA)
        .filter(limite__gte=timezone.localtime(desde).date(), limite__lt=timezone.localtime(hasta).date())
        .order_by("limite")
    )
    return [
        FechaDeCalendario(
            id=tarea.pk,
            titulo=tarea.titulo,
            inicio=_momento(tarea.limite),
            todo_el_dia=True,
            enlace=reverse("proyectos:tarea", args=[tarea.pk]),
            categoria="Tareas",
            se_puede_mover=usuario.pk in (tarea.responsable_id, tarea.creador_id),
        )
        for tarea in lista
    ]


# Cambia la fecha límite de un proyecto al arrastrarla.
#   - id: el número del proyecto.
#   - inicio: el día nuevo (fin no se usa).
def mover_proyecto(usuario, id, inicio, fin):
    proyecto = Proyecto.objects.select_related("grupo__organizacion").filter(pk=id).first()
    if proyecto is None or not servicios.ve(usuario, proyecto):
        raise ValidationError("Ese proyecto no existe.")
    servicios.editar_proyecto(usuario, proyecto, {"limite": timezone.localtime(inicio).date()})


# Cambia la fecha límite de una tarea al arrastrarla.
def mover_tarea(usuario, id, inicio, fin):
    tarea = Tarea.objects.select_related("proyecto__audiencia").filter(pk=id).first()
    if tarea is None:
        raise ValidationError("Esa tarea no existe.")
    servicios.editar_tarea(usuario, tarea, {"limite": timezone.localtime(inicio).date()})
