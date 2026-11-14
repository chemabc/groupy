"""
Árboles de proyectos: cada proyecto principal con sus subproyectos colgando y, dentro de cada uno, sus
tareas plegadas (ver docs/diseno.md, apartado 14.1.4, «Árboles de proyectos»). Sigue el mismo protocolo
visual que los árboles de grupos (grupos/arboles.py):

- Arriba de cada árbol, el grupo que coordina el proyecto principal, en una etiqueta («Personal», si lo es).
- Con fondo amarillo, los proyectos en los que participa quien mira (los creó, tiene un cometido o tiene
  una tarea en ellos).
- Con recuadro rojo, el proyecto cuya ficha se está mirando.
- En gris, los finalizados.
- Junto a cada proyecto, sus tareas hechas y totales entre paréntesis, «(3/5)», y una flecha para
  desplegarlas (plegadas de entrada).

Lo calcula arboles_de_proyectos() y lo pintan «proyectos/arboles.html» y «proyectos/nodo_de_proyecto.html».
Lo usan «Tareas y proyectos → Proyectos» (De mis grupos y Personales) y la ficha de cada proyecto
(proyectos/views.py).
"""

from dataclasses import dataclass, field

from django.db.models import Q

from permisos.models import Cometido

from .models import Proyecto, Tarea
from .servicios import ANCLA


@dataclass
class NodoDeProyecto:
    """
    Un proyecto dentro del árbol, con sus tareas (plegadas al pintarlo) y sus subproyectos colgando.
    """

    # El proyecto (objeto Proyecto, con su tipología cargada).
    proyecto: object
    # Si quien mira participa en él (fondo amarillo).
    participa: bool = False
    # Si es el proyecto cuya ficha se mira (recuadro rojo).
    actual: bool = False
    # Sus tareas, en el orden del kanban (estado y posición).
    tareas: list = field(default_factory=list)
    # Cuántas de ellas están hechas.
    hechas: int = 0
    # Los subproyectos que también salen, por título.
    hijos: list = field(default_factory=list)


@dataclass
class ArbolDeProyecto:
    """
    Un proyecto principal con todo lo que cuelga de él, y el grupo que lo coordina para la cabecera.
    """

    # El grupo que coordina el proyecto de arriba (con su organización), o None si es personal.
    grupo: object
    # El nodo de arriba.
    raiz: NodoDeProyecto


# Consulta (sin ejecutar) con los ids de los proyectos en los que participa una persona: los que ha
# creado, aquellos en los que tiene un cometido y aquellos en los que es responsable o colabora en una
# tarea. La usan estos árboles y la tarjeta de Inicio (proyectos/inicio.py).
#   - usuario: quién.
def en_los_que_participa(usuario):
    con_cometido = Cometido.objects.filter(usuario=usuario, ancla_tipo=ANCLA).values("ancla_id")
    con_tarea = Tarea.objects.filter(Q(responsable=usuario) | Q(colaboradores=usuario)).values("proyecto_id")
    return Proyecto.objects.filter(Q(creador=usuario) | Q(pk__in=con_cometido) | Q(pk__in=con_tarea)).values("pk")


# Monta los árboles de una lista de proyectos que quien mira ya puede ver. Un proyecto cuyo padre no está
# en la lista (porque no lo ve) sale como principal de su propio árbol. Los árboles van ordenados por el
# grupo que coordina y por título. Cuesta 2 consultas, sean cuantos sean los proyectos y las tareas.
#   - usuario: quien mira.
#   - proyectos: lista de proyectos (con «tipologia» y «grupo__organizacion» cargados).
#   - actual: número del proyecto cuya ficha se mira, o None.
def arboles_de_proyectos(usuario, proyectos, actual=None):
    ids = [proyecto.pk for proyecto in proyectos]
    if not ids:
        return []
    participa = set(Proyecto.objects.filter(pk__in=ids).filter(pk__in=en_los_que_participa(usuario)).values_list("pk", flat=True))
    tareas = {}
    for tarea in Tarea.objects.filter(proyecto_id__in=ids, archivado__isnull=True).select_related("responsable").order_by("estado", "orden", "pk"):
        tareas.setdefault(tarea.proyecto_id, []).append(tarea)
    nodos = {}
    for proyecto in proyectos:
        suyas = tareas.get(proyecto.pk, [])
        nodos[proyecto.pk] = NodoDeProyecto(
            proyecto=proyecto,
            participa=proyecto.pk in participa,
            actual=proyecto.pk == actual,
            tareas=suyas,
            hechas=sum(1 for tarea in suyas if tarea.estado == Tarea.HECHA),
        )
    raices = []
    for proyecto in sorted(proyectos, key=lambda p: (p.titulo.lower(), p.pk)):
        padre = nodos.get(proyecto.padre_id)
        if padre is not None:
            padre.hijos.append(nodos[proyecto.pk])
        else:
            raices.append(ArbolDeProyecto(grupo=proyecto.grupo, raiz=nodos[proyecto.pk]))
    raices.sort(key=lambda arbol: (arbol.grupo is None, arbol.grupo.nombre.lower() if arbol.grupo else "", arbol.raiz.proyecto.titulo.lower()))
    return raices
