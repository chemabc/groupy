"""
Tarjeta «Mis talentos» de «Inicio → Mis datos» (declarada en talentos/apps.py; dónde sale lo decide
config/inicio.py): tus talentos, con su detalle y con cuántos grupos los compartes. El botón «Editar» va a
«Configuración de mi cuenta → Mis datos → Talentos».
"""

from django.db.models import Count
from django.urls import reverse

from base.contrato import ApartadoDeTarjeta, FilaDeResumen, ResumenDeTarjeta

from .models import TalentoDePersona


# Hace el resumen de la tarjeta para una persona. Cuesta 1 consulta, tenga los talentos que tenga.
#   - usuario: quien mira.
def mios(usuario):
    talentos = (
        TalentoDePersona.objects.filter(usuario=usuario)
        .select_related("talento")
        .annotate(grupos=Count("compartidos"))
        .order_by("talento__nombre")
    )
    filas = []
    for talento in talentos:
        compartido = f"compartido con {talento.grupos} grupo{'s' if talento.grupos != 1 else ''}" if talento.grupos else "sin compartir"
        filas.append(FilaDeResumen(talento.talento.nombre, detalle=" · ".join(p for p in (talento.detalle, compartido) if p)))
    return ResumenDeTarjeta(
        apartados=(ApartadoDeTarjeta(filas=tuple(filas), total=len(filas), vacio="Aún no has apuntado ningún talento."),),
        enlace=reverse("talentos:mis_talentos"),
        boton="Editar",
    )
