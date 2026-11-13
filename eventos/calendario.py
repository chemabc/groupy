"""
Lo que «eventos» aporta al calendario común (ver la FuenteDeCalendario «eventos.eventos» en
eventos/apps.py): las fechas de los eventos que ve cada persona, con un color por tipo, y mover un evento
al arrastrarlo. El módulo «calendario» llama a estas funciones por su ruta, sin importar este módulo.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.urls import reverse

from base.contrato import FechaDeCalendario
from tipologias.models import Tipologia
from tipologias.servicios import cadena

from . import servicios
from .models import Evento

# Color de cada tipo principal de evento. Los subtipos toman el de su tipo principal; los tipos que no
# están aquí (los que cree una organización desde cero), el de la fuente.
COLORES = {"Reunión": "#7c3aed", "Acción": "#dc2626", "Recaudatorio": "#16a34a", "Genérico": "#0284c7"}

# Lo más que se busca hacia atrás un evento que empezó antes del trozo pintado y aún dura (dos días).
_MAXIMA_DURACION = timedelta(days=2)


# Fechas de los eventos que una persona ve entre dos momentos: los convocados, los cancelados (tachados
# con «Cancelado:») y sus reuniones pendientes de apoyos. Cada uno con el color y el nombre de su tipo
# principal; se pueden arrastrar los que esa persona gestiona. Unas 3 consultas, haya los que haya.
#   - usuario: quién mira el calendario.
#   - desde, hasta: el trozo de calendario que se pinta.
def fechas(usuario, desde, hasta):
    eventos = list(
        servicios.visibles(usuario).filter(inicio__lt=hasta, inicio__gte=desde - _MAXIMA_DURACION).select_related("lugar").order_by("inicio")
    )
    tipologias = {t.pk: t for t in Tipologia.objects.filter(familia=Tipologia.EVENTO)}
    resultado = []
    for evento in eventos:
        if evento.fin <= desde:
            continue
        principal = cadena(tipologias[evento.tipologia_id], tipologias)[0].nombre
        titulo = evento.titulo
        if evento.estado == Evento.CANCELADO:
            titulo = f"Cancelado: {titulo}"
        elif evento.estado == Evento.PENDIENTE:
            titulo = f"Pendiente de apoyos: {titulo}"
        resultado.append(
            FechaDeCalendario(
                id=evento.pk,
                titulo=titulo,
                inicio=evento.inicio,
                fin=evento.fin,
                enlace=reverse("eventos:evento", args=[evento.pk]),
                categoria=principal,
                color="#94a3b8" if evento.estado == Evento.CANCELADO else COLORES.get(principal, ""),
                lugar=evento.lugar.nombre if evento.lugar else (evento.direccion or evento.url),
                se_puede_mover=evento.estado != Evento.CANCELADO and servicios.puede_gestionar(usuario, evento),
            )
        )
    return resultado


# Cambia la fecha de un evento al arrastrarlo en el calendario: nueva hora de inicio y, si se estira,
# nueva duración. Solo quien lo gestiona (ver servicios.puede_gestionar).
#   - usuario: quien lo arrastra.
#   - id: el número del evento.
#   - inicio, fin: las fechas nuevas (fin puede ser None: se mantiene la duración).
def mover(usuario, id, inicio, fin):
    evento = Evento.objects.select_related("grupo__organizacion", "tipologia").filter(pk=id).first()
    if evento is None or not servicios.ve(usuario, evento):
        raise ValidationError("Ese evento no existe.")
    if evento.estado == Evento.CANCELADO:
        raise ValidationError("Un evento cancelado no se mueve.")
    datos = {"inicio": inicio}
    if fin is not None:
        minutos = int((fin - inicio).total_seconds() // 60)
        if minutos <= 0:
            raise ValidationError("Tiene que terminar después de empezar.")
        datos["duracion"] = minutos
    servicios.editar(usuario, evento, datos)
