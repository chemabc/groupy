"""
Tarjeta «Mis proyectos abiertos» de «Inicio → Panel» (declarada en proyectos/apps.py; dónde sale lo
decide config/inicio.py): los proyectos en los que participas y que siguen abiertos (sin terminar ni
archivar). Participas si lo has creado, si tienes un cometido en él (por ejemplo, la coordinación) o si
eres responsable o colaboras en una de sus tareas.
"""

from django.db.models import F, Q
from django.urls import reverse

from base.contrato import ApartadoDeTarjeta, FilaDeResumen, ResumenDeTarjeta
from permisos.models import Cometido

from .models import Proyecto, Tarea
from .servicios import ANCLA, visibles

# Cuántos proyectos enseña como mucho.
FILAS = 8


# Hace el resumen de la tarjeta para una persona: primero los que tienen fecha límite (la más cercana
# antes), después el resto por título. Cuesta 2 consultas, haya los que haya.
#   - usuario: quien mira.
def abiertos(usuario):
    con_cometido = Cometido.objects.filter(usuario=usuario, ancla_tipo=ANCLA).values("ancla_id")
    con_tarea = Tarea.objects.filter(Q(responsable=usuario) | Q(colaboradores=usuario)).values("proyecto_id")
    consulta = (
        visibles(usuario)
        .filter(Q(creador=usuario) | Q(pk__in=con_cometido) | Q(pk__in=con_tarea))
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
