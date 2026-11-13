"""
Notificaciones del módulo «eventos» (las reparte «comunicaciones»; ver eventos/apps.py).
"""

from django.urls import reverse
from django.utils import timezone

from audiencias.servicios import personas_de
from base.contrato import AvisoPreparado
from grupos.models import Contencion, Pertenencia

from .models import Asistencia, Evento


# El evento con su grupo, o None si ya no existe.
def _evento(evento_id):
    return Evento.objects.select_related("grupo__organizacion", "audiencia", "tipologia").filter(pk=evento_id).first()


# Fecha y hora de un evento, en palabras cortas: «el 20/11/2026 a las 18:00».
def _cuando(evento):
    return f"el {timezone.localtime(evento.inicio):%d/%m/%Y a las %H:%M}"


# «GRU Henares convoca «Asamblea de noviembre» (Reunión) el 20/11/2026 a las 18:00.» A quienes lo ven
# (si es público, a las personas del grupo que convoca y de sus subgrupos), menos a quien lo convoca.
def convocado(evento_id, **resto):
    evento = _evento(evento_id)
    if evento is None or evento.estado != Evento.CONVOCADO:
        return []
    personas = personas_de(evento.audiencia)
    if personas is None:
        subarbol = Contencion.objects.filter(antecesor=evento.grupo).values("descendiente_id")
        personas = set(Pertenencia.objects.filter(grupo_id__in=subarbol).values_list("usuario_id", flat=True))
    personas.discard(evento.convocante_id)
    texto = f"{evento.grupo} convoca «{evento.titulo}» ({evento.tipologia}) {_cuando(evento)}."
    return [AvisoPreparado(tuple(sorted(personas)), texto, reverse("eventos:evento", args=[evento.pk]))]


# «Se ha cancelado «Asamblea de noviembre» (el 20/11/2026…).» A quienes iban o dudaban.
def cancelado(evento_id, **resto):
    evento = _evento(evento_id)
    if evento is None:
        return []
    personas = set(evento.asistencias.exclude(respuesta=Asistencia.NO).values_list("usuario_id", flat=True))
    personas.discard(evento.convocante_id)
    texto = f"Se ha cancelado «{evento.titulo}», que era {_cuando(evento)}."
    return [AvisoPreparado(tuple(sorted(personas)), texto, reverse("eventos:evento", args=[evento.pk]))]
