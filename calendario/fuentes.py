"""
Lo que el propio módulo «calendario» aporta al calendario común: los recordatorios (ver la
FuenteDeCalendario «calendario.recordatorios» en calendario/apps.py).
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.urls import reverse

from base.contrato import FechaDeCalendario

from . import servicios
from .models import Recordatorio

# Color de los recordatorios en el calendario.
COLOR = "#ca8a04"


# Fechas de los recordatorios que una persona ve entre dos momentos. Se pueden arrastrar los que esa
# persona puede cambiar. 2 consultas, haya los que haya.
#   - usuario: quién mira.
#   - desde, hasta: el trozo de calendario.
def recordatorios(usuario, desde, hasta):
    # Un recordatorio entra si empieza antes de «hasta» y termina (o empieza, si no tiene fin) después de
    # «desde». Los de día entero ocupan hasta el final de su último día.
    termina_despues = Q(fin__gte=desde - timedelta(days=1)) | Q(fin__isnull=True, inicio__gte=desde - timedelta(days=1))
    lista = servicios.recordatorios_visibles(usuario).filter(termina_despues, inicio__lt=hasta).order_by("inicio")
    return [
        FechaDeCalendario(
            id=recordatorio.pk,
            titulo=recordatorio.titulo,
            inicio=recordatorio.inicio,
            fin=recordatorio.fin,
            todo_el_dia=recordatorio.todo_el_dia,
            enlace=reverse("calendario:recordatorio", args=[recordatorio.pk]),
            categoria="Recordatorios",
            se_puede_mover=servicios.puede_gestionar(usuario, recordatorio, ya_lo_ve=True),
        )
        for recordatorio in lista
    ]


# Cambia la fecha de un recordatorio al arrastrarlo en el calendario.
#   - id: el número del recordatorio.
#   - inicio, fin: las fechas nuevas (fin puede ser None).
def mover(usuario, id, inicio, fin):
    recordatorio = Recordatorio.objects.select_related("audiencia", "grupo__organizacion").filter(pk=id).first()
    if recordatorio is None or not servicios.ve(usuario, recordatorio):
        raise ValidationError("Ese recordatorio no existe.")
    servicios.editar_recordatorio(usuario, recordatorio, {"inicio": inicio, "fin": fin})
