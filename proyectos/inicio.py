"""
Tarjeta «Mis proyectos abiertos» de «Inicio → Panel» (declarada en proyectos/apps.py; dónde sale lo
decide config/inicio.py): los proyectos en los que participas y que siguen abiertos (sin terminar ni
archivar). Participas si lo has creado, si tienes un cometido en él (por ejemplo, la coordinación) o si
eres responsable o colaboras en una de sus tareas.
"""

from django.db.models import F
from django.urls import reverse

from base.contrato import ApartadoDeTarjeta, FilaDeResumen, ResumenDeTarjeta
from .arboles import en_los_que_participa
from .models import Proyecto
from .servicios import visibles

# Cuántos proyectos enseña como mucho.
FILAS = 8


# Hace el resumen de la tarjeta para una persona: primero los que tienen fecha límite (la más cercana
# antes), después el resto por título. Cuesta 2 consultas, haya los que haya.
#   - usuario: quien mira.
def abiertos(usuario):
    consulta = (
        visibles(usuario)
        .filter(pk__in=en_los_que_participa(usuario))
        .filter(terminado__isnull=True, raiz__archivado__isnull=True)
        .exclude(estado=Proyecto.FINALIZADO)
        .select_related("grupo", "raiz")
        .order_by(F("limite").asc(nulls_last=True), "titulo")
    )
    filas = []
    for proyecto in consulta[:FILAS]:
        partes = [proyecto.get_estado_display()]
        partes.append("personal" if proyecto.personal else proyecto.grupo.nombre if proyecto.grupo else "")
        if proyecto.padre_id:
            partes.append(f"dentro de «{proyecto.raiz.titulo}»")
        if proyecto.limite:
            partes.append(f"hasta el {proyecto.limite:%d/%m/%Y}")
        filas.append(FilaDeResumen(proyecto.titulo, reverse("proyectos:proyecto", args=[proyecto.pk]), " · ".join(p for p in partes if p)))
    return ResumenDeTarjeta(
        apartados=(
            ApartadoDeTarjeta(
                filas=tuple(filas),
                total=consulta.count(),
                enlace=reverse("proyectos:proyectos"),
                vacio="No participas en ningún proyecto abierto.",
            ),
        ),
        enlace=reverse("proyectos:proyectos"),
        boton="Ir a proyectos",
    )
