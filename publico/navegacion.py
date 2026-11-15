"""
Navegación de las miniwebs («🌐 Webs», docs/diseno.md, apartado 15, P8 A): arriba, una barra de camino con
desplegables (ORG ▾ › GRU ▾ › GRU ▾), los subgrupos con web y los «Grupos de actividad» (los que publican
para los tuyos); debajo, las pestañas con las páginas del grupo. Y el mapa de la jerarquía (un grafo de
Mermaid con los grupos que tienen web y que puedes ver).

Solo salen los grupos con páginas que la persona puede ver y los que hay por encima de ellos (para llegar),
así que no se enseña nada que no se pueda abrir. Todo se calcula con unas pocas consultas, haya los grupos
que haya.
"""

from dataclasses import dataclass, field

from django.urls import reverse

from grupos.models import Contencion, Grupo, Organizacion, Pertenencia

from .models import Pagina, RelacionDeConsumo
from .servicios import condicion_visibles


@dataclass
class Mapa:
    """Lo que la persona puede recorrer de las webs internas."""

    # Páginas que ve: lista de (id, título, grupo_id, organizacion_id), en orden.
    paginas: list
    # Grupos por los que se navega (con web, o por encima de uno con web): {id: Grupo}.
    grupos: dict
    # Organizaciones con algo que ver: {id: Organizacion}, por nombre.
    organizaciones: dict
    # Grupos que solo se ven por una relación de publicación y consumo («Grupos de actividad»).
    actividad: set
    # Cuántas páginas tiene cada grupo: {grupo_id: número}.
    por_grupo: dict = field(default_factory=dict)


# Prepara el mapa de lo que una persona puede recorrer. Unas 4 consultas (más las del alcance).
#   - alcance: el de servicios.alcance_de().
def mapa_de(alcance):
    paginas = list(
        Pagina.objects.filter(condicion_visibles(alcance)).order_by("orden", "pk").values_list("pk", "titulo", "grupo_id", "organizacion_id")
    )
    por_grupo = {}
    for _pk, _titulo, grupo_id, _organizacion_id in paginas:
        if grupo_id:
            por_grupo[grupo_id] = por_grupo.get(grupo_id, 0) + 1
    actividad = set(alcance.consumidos) & set(por_grupo)
    # Por encima de cada grupo con web (de los propios), sus antecesores: para poder llegar bajando.
    propios_con_web = set(por_grupo) - actividad
    navegables = set(Contencion.objects.filter(descendiente_id__in=propios_con_web).values_list("antecesor_id", flat=True)) | set(por_grupo)
    grupos = {g.pk: g for g in Grupo.objects.filter(pk__in=navegables).select_related("organizacion").order_by("nombre")}
    ids_de_organizaciones = {g.organizacion_id for pk, g in grupos.items() if pk not in actividad}
    ids_de_organizaciones |= {organizacion_id for _pk, _t, grupo_id, organizacion_id in paginas if not grupo_id and organizacion_id}
    organizaciones = {o.pk: o for o in Organizacion.objects.filter(pk__in=ids_de_organizaciones).order_by("nombre")}
    return Mapa(paginas=paginas, grupos=grupos, organizaciones=organizaciones, actividad=actividad, por_grupo=por_grupo)


# Las páginas de una dueña (un grupo, o una organización sin grupo), en orden: lista de (id, título).
def pestanas(mapa, grupo_id=None, organizacion_id=None):
    if grupo_id:
        return [(pk, titulo) for pk, titulo, g, _o in mapa.paginas if g == grupo_id]
    return [(pk, titulo) for pk, titulo, g, o in mapa.paginas if not g and o == organizacion_id]


# Un tramo de la barra de camino: su nombre, adónde lleva y su desplegable (hermanos u opciones).
@dataclass
class Tramo:
    nombre: str
    url: str
    desplegable: list = field(default_factory=list)


# La barra de camino de una dueña: la organización (con las demás en su desplegable) y, bajando, cada grupo
# hasta el actual (cada uno con sus hermanos con web en el desplegable). Devuelve (tramos, hijos): los
# subgrupos con web del actual van aparte («Subgrupos ▾»). Sin consultas.
#   - mapa: el de mapa_de().
#   - grupo: el grupo que se mira (o None si se mira una organización).
#   - organizacion_id: la organización que se mira (si no hay grupo).
def camino(mapa, grupo=None, organizacion_id=None):
    if grupo is not None and grupo.pk in mapa.actividad:
        otros = [_opcion(g) for pk, g in mapa.grupos.items() if pk in mapa.actividad]
        return [Tramo("Grupos de actividad", "", otros), Tramo(grupo.nombre, _url_de_grupo(grupo.pk))], []
    organizacion_id = grupo.organizacion_id if grupo is not None else organizacion_id
    organizacion = mapa.organizaciones.get(organizacion_id)
    tramos = []
    if organizacion is not None:
        otras = [{"nombre": o.nombre, "url": reverse("publico:organizacion", args=[o.pk]), "actual": o.pk == organizacion_id} for o in mapa.organizaciones.values()]
        tramos.append(Tramo(organizacion.nombre, reverse("publico:organizacion", args=[organizacion.pk]), otras))
    cadena = []
    actual = grupo
    while actual is not None:
        cadena.insert(0, actual)
        actual = mapa.grupos.get(actual.padre_id)
    for eslabon in cadena:
        hermanos = [
            {**_opcion(g), "actual": g.pk == eslabon.pk}
            for g in mapa.grupos.values()
            if g.padre_id == eslabon.padre_id and g.organizacion_id == eslabon.organizacion_id and g.pk not in mapa.actividad
        ]
        tramos.append(Tramo(eslabon.nombre, _url_de_grupo(eslabon.pk), hermanos if len(hermanos) > 1 else []))
    if grupo is not None:
        hijos = [_opcion(g) for g in mapa.grupos.values() if g.padre_id == grupo.pk and g.pk not in mapa.actividad]
    else:
        hijos = [_opcion(g) for g in mapa.grupos.values() if g.organizacion_id == organizacion_id and g.padre_id is None]
    return tramos, hijos


# Los grupos de actividad (solo por una relación), para su tramo de la barra.
def grupos_de_actividad(mapa):
    return [_opcion(g) for pk, g in mapa.grupos.items() if pk in mapa.actividad]


# Dónde empieza una persona al abrir «🌐 Webs»: su asamblea base si tiene web (o está encima de una), si no
# su primera organización con algo, o el primer grupo de actividad. Devuelve una dirección o "". Una consulta.
def inicio_de(usuario, mapa):
    if usuario.is_authenticated:
        base = Pertenencia.objects.filter(usuario=usuario, es_base=True).values_list("grupo_id", flat=True).first()
        if base in mapa.grupos:
            return _url_de_grupo(base)
    if mapa.organizaciones:
        return reverse("publico:organizacion", args=[next(iter(mapa.organizaciones))])
    if mapa.actividad:
        return _url_de_grupo(next(iter(mapa.actividad)))
    return ""


# Opción de un desplegable: nombre (con cuántas páginas) y dirección.
def _opcion(grupo):
    return {"nombre": grupo.nombre, "url": _url_de_grupo(grupo.pk), "actual": False}


# Dirección de la web de un grupo.
def _url_de_grupo(grupo_id):
    return reverse("publico:grupo", args=[grupo_id])


# ── Mapa de la jerarquía (pestaña «Jerarquía») ───────────────────────────────────────────────────────


# Texto del grafo de Mermaid con los grupos que tienen web (y los de encima), cada organización en su caja,
# y los grupos de actividad aparte con flechas de puntos hacia los grupos para los que publican. Cada nodo
# dice cuántas páginas tiene y se pulsa. Devuelve (texto, enlaces). Una consulta (las relaciones).
#   - mapa: el de mapa_de().
def grafo(mapa):
    if not mapa.grupos and not mapa.organizaciones:
        return "", {}
    lineas = ["flowchart TD"]
    lineas.append("  classDef conweb fill:#ecfeff,stroke:#0e7490,color:#083344,font-weight:bold")
    lineas.append("  classDef paso fill:#f8fafc,stroke:#cbd5e1,color:#64748b")
    lineas.append("  classDef organizacion fill:#ede9fe,stroke:#7c3aed,color:#3b0764")
    lineas.append("  classDef actividad fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-dasharray:4 3")
    enlaces = {}
    for organizacion in mapa.organizaciones.values():
        lineas.append(f"  subgraph caja{organizacion.pk}[{_texto(organizacion.nombre)}]")
        nodo = f"o{organizacion.pk}"
        paginas = len(pestanas(mapa, organizacion_id=organizacion.pk))
        lineas.append(f"    {nodo}[{_texto(organizacion.nombre + _cuantas(paginas))}]:::organizacion")
        enlaces[nodo] = reverse("publico:organizacion", args=[organizacion.pk])
        for grupo in mapa.grupos.values():
            if grupo.organizacion_id == organizacion.pk and grupo.pk not in mapa.actividad:
                lineas.append(f"    g{grupo.pk}[{_texto(grupo.nombre + _cuantas(mapa.por_grupo.get(grupo.pk, 0)))}]:::{'conweb' if grupo.pk in mapa.por_grupo else 'paso'}")
                enlaces[f"g{grupo.pk}"] = _url_de_grupo(grupo.pk)
        lineas.append("  end")
    for grupo in mapa.grupos.values():
        if grupo.pk in mapa.actividad:
            continue
        origen = f"g{grupo.padre_id}" if grupo.padre_id in mapa.grupos else f"o{grupo.organizacion_id}"
        lineas.append(f"  {origen} --> g{grupo.pk}")
    if mapa.actividad:
        lineas.append(f"  subgraph actividad[{_texto('Grupos de actividad')}]")
        for pk in mapa.actividad:
            lineas.append(f"    g{pk}[{_texto(mapa.grupos[pk].nombre + _cuantas(mapa.por_grupo.get(pk, 0)))}]:::actividad")
            enlaces[f"g{pk}"] = _url_de_grupo(pk)
        lineas.append("  end")
        relaciones = RelacionDeConsumo.objects.filter(estado=RelacionDeConsumo.ACEPTADA, productor_id__in=mapa.actividad).values_list("productor_id", "consumidor_id")
        for productor, consumidor in relaciones:
            if consumidor in mapa.grupos:
                lineas.append(f"  g{productor} -. publica para .-> g{consumidor}")
    return "\n".join(lineas), enlaces


# « (3 páginas)», « (1 página)» o nada.
def _cuantas(numero):
    return f" ({numero} página{'s' if numero != 1 else ''})" if numero else ""


# Un texto entre comillas para Mermaid (las comillas de dentro, con su código).
def _texto(texto):
    return '"' + str(texto).replace('"', "#quot;") + '"'
