"""
Lo que el módulo «limpieza» necesita de «eventos» (ver eventos/apps.py, apartado «limpiables»): qué
eventos terminaron antes de un momento.
"""

from datetime import timedelta

from .models import Evento

# Lo más que puede durar un evento a efectos de la limpieza (una acampada de una semana): así la consulta
# usa el índice por fecha de inicio y el final exacto se mira después.
DURACION_MAXIMA = timedelta(days=7)


# Eventos convocados o cancelados que terminaron antes de «antes», sin archivar. Los pendientes de apoyos
# (reuniones que nunca se convocaron) no entran: solo los veía quien los convocó y caducan con su
# solicitud.
def eventos(antes):
    candidatos = Evento.objects.filter(inicio__lt=antes, archivado__isnull=True).exclude(estado=Evento.PENDIENTE)
    ids = [
        pk
        for pk, inicio, duracion in candidatos.values_list("pk", "inicio", "duracion")
        if inicio + timedelta(minutes=duracion) < antes or inicio < antes - DURACION_MAXIMA
    ]
    return Evento.objects.filter(pk__in=ids)
