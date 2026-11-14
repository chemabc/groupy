"""
Cercanía: las personas que ven algo, ordenadas por lo cerca que están del grupo desde el que se publicó.

Lo usa el selector de personas (base/formularios.py, SelectorDePersonas) para elegir, por ejemplo, quién
se encarga de una tarea: primero salen las personas del propio grupo, después las de sus subgrupos y luego,
nivel a nivel, las de los grupos de más arriba, hasta donde llega quién lo ve. Ver docs/diseno.md,
apartado 4, «Selector de personas».

Reglas (acordadas el 14 de noviembre de 2026):
- Solo salen las personas que **ven** lo que se está editando: nadie de fuera, nada inventado.
- La cercanía se mide desde el **grupo de referencia** (el que coordina el proyecto, o el de la tarea
  suelta), con los mismos niveles que la visibilidad («grupo:0», «grupo:1»…).
- La **lista** solo se enseña a quien puede ver los miembros del grupo de referencia (quien lo administra
  y, si la organización no lo ha cerrado, sus miembros; ver grupos/acceso.py). Los demás solo pueden
  escribir el alias exacto, que se comprueba igual.

Todo se calcula con unas pocas consultas, haya las personas que haya.
"""

from dataclasses import dataclass

from django.db.models import Q

from grupos.acceso import alcance_de, ve_miembros
from grupos.models import Contencion, Pertenencia

from .models import Audiencia


@dataclass(frozen=True)
class PersonaCercana:
    """Una persona de la lista, con lo que se enseña de ella."""

    # Su alias, tal como se ve y se escribe.
    alias: str
    # Una marca corta junto al alias («admin», «tú», «admin · tú»), o vacío.
    marca: str


@dataclass(frozen=True)
class GrupoCercano:
    """Un grupo dentro de un bloque, con las personas que salen en él."""

    # Nombre del grupo («GRU Sorbe»).
    nombre: str
    # Sus personas, por orden alfabético.
    personas: tuple


@dataclass(frozen=True)
class Bloque:
    """Un escalón de cercanía: «Aquí», «En sus subgrupos», «Un nivel por encima»…"""

    # Título del bloque («Un nivel por encima: GRU Jarama»).
    titulo: str
    # Una frase que explica quién está en él.
    explicacion: str
    # Etiqueta corta de cercanía («Muy cerca», «Cerca», «Más lejos», «Lejos»).
    cercania: str
    # Posición del escalón: 0 el más cercano. La plantilla la usa para el color (más intenso cuanto más cerca).
    nivel: int
    # Sus grupos, con sus personas.
    grupos: tuple

    # Cuántas personas tiene el bloque.
    @property
    def total(self):
        return sum(len(grupo.personas) for grupo in self.grupos)


@dataclass(frozen=True)
class Cercania:
    """Lo que necesita el selector de personas: si se enseña la lista y, si es así, sus bloques."""

    # Si quien elige puede ver la lista (si no, solo puede escribir el alias exacto).
    ve_la_lista: bool
    # Los bloques, del más cercano al más lejano (vacío si no ve la lista).
    bloques: tuple

    # Los datos para la isla «selectorDePersonas» (base/static/base/interfaz.js), listos para JSON.
    def como_datos(self):
        return {
            "ve_la_lista": self.ve_la_lista,
            "bloques": [
                {
                    "titulo": bloque.titulo,
                    "explicacion": bloque.explicacion,
                    "cercania": bloque.cercania,
                    "nivel": bloque.nivel,
                    "grupos": [
                        {"nombre": grupo.nombre, "personas": [{"alias": p.alias, "marca": p.marca} for p in grupo.personas]}
                        for grupo in bloque.grupos
                    ],
                }
                for bloque in self.bloques
            ],
        }


# Etiqueta de cercanía de cada escalón, por su posición.
ETIQUETAS_DE_CERCANIA = ("Muy cerca", "Cerca", "Más lejos", "Lejos")

# Nombre de cada altura por encima del grupo de referencia.
ALTURAS = {1: "Un nivel por encima", 2: "Dos niveles por encima"}


# Devuelve la cercanía de las personas que ven algo, para enseñarla a quien elige. Unas 5 consultas.
#   - usuario: quien elige (para saber si puede ver la lista).
#   - grupo: el grupo de referencia (con su organización cargada).
#   - audiencia: la audiencia de lo que se edita (un proyecto, una tarea guardada…), o None.
#   - clave: si aún no hay audiencia, la opción de visibilidad elegida («grupo:1», «organizacion»…).
def cercania(usuario, grupo, audiencia=None, clave=None):
    if not ve_la_lista(usuario, grupo):
        return Cercania(ve_la_lista=False, bloques=())
    encima = {antecesor: (distancia, nombre) for antecesor, distancia, nombre in _encima(grupo)}
    filas = list(
        Pertenencia.objects.filter(_quienes(grupo, audiencia, clave, encima), usuario__activo=True)
        .values_list("usuario_id", "usuario__alias", "grupo_id", "grupo__nombre", "rol")
        .order_by("grupo__nombre", "usuario__alias")
    )
    # Para cada grupo de las filas, los grupos de encima del de referencia que lo contienen (también el
    # propio grupo de referencia, a distancia 0). Una consulta.
    contenedores = {}
    for descendiente, antecesor in Contencion.objects.filter(
        descendiente_id__in={fila[2] for fila in filas}, antecesor_id__in=list(encima)
    ).values_list("descendiente_id", "antecesor_id"):
        contenedores.setdefault(descendiente, []).append(antecesor)
    # Cada persona va al escalón más cercano de los suyos, y dentro de él, a su primer grupo.
    mejor = {}
    for usuario_id, alias, grupo_id, nombre, rol in filas:
        escalon = _escalon(grupo_id, grupo.pk, contenedores.get(grupo_id, []), encima)
        actual = mejor.get(usuario_id)
        if actual is None or escalon < actual[0]:
            marcas = ["admin"] if rol == Pertenencia.ADMIN_GRUPO else []
            if usuario_id == usuario.pk:
                marcas.append("tú")
            marca = " · ".join(marcas)
            mejor[usuario_id] = (escalon, nombre, PersonaCercana(alias=alias, marca=marca))
    if audiencia is not None and audiencia.tipo == Audiencia.PRIVADA:
        _anadir_sin_grupo(audiencia, mejor)
    return Cercania(ve_la_lista=True, bloques=_bloques(mejor, grupo, encima))


# Ids de las personas que ven algo: las mismas que salen en la lista (también las que no se enseñan a
# quien no puede ver la lista). Para comprobar lo elegido. Unas 2 consultas.
#   - grupo, audiencia, clave: como en cercania().
def ids_que_ven(grupo, audiencia=None, clave=None):
    encima = {antecesor: (distancia, nombre) for antecesor, distancia, nombre in _encima(grupo)}
    ids = set(Pertenencia.objects.filter(_quienes(grupo, audiencia, clave, encima), usuario__activo=True).values_list("usuario_id", flat=True))
    if audiencia is not None and audiencia.tipo == Audiencia.PRIVADA:
        ids |= set(audiencia.personas.filter(usuario__activo=True).values_list("usuario_id", flat=True))
    return ids


# Dice si una persona puede ver la lista de quienes ven algo publicado en un grupo: la regla de la lista
# de miembros (grupos/acceso.py, ve_miembros). El superadmin, siempre. Unas 2 consultas.
#   - usuario: quien elige.
#   - grupo: el grupo de referencia (con su organización cargada).
def ve_la_lista(usuario, grupo):
    if usuario.is_superuser:
        return True
    return ve_miembros(usuario, grupo, alcance_de(usuario))


# Los grupos que contienen al de referencia (también él mismo, a distancia 0), con su distancia y su
# nombre. Una consulta.
#   - grupo: el grupo de referencia.
def _encima(grupo):
    return Contencion.objects.filter(descendiente=grupo).values_list("antecesor_id", "distancia", "antecesor__nombre")


# Condición sobre las pertenencias de las personas que ven algo.
#   - grupo: el grupo de referencia.
#   - audiencia: la audiencia, o None (entonces manda la clave).
#   - clave: la opción de visibilidad, si no hay audiencia. «privado» (una tarea suelta que aún no tiene
#     sus personas) deja elegir entre las del propio grupo y sus subgrupos.
#   - encima: los grupos de encima, de _encima().
def _quienes(grupo, audiencia, clave, encima):
    if audiencia is not None:
        if audiencia.tipo == Audiencia.PRIVADA:
            return Q(usuario__in=audiencia.personas.values("usuario_id"))
        if audiencia.tipo == Audiencia.GRUPOS:
            return Q(grupo__ascendencia__antecesor__in=audiencia.grupos.values("grupo_id"))
        # Toda la organización o público: las personas de la organización (nunca de otras).
        return Q(grupo__organizacion_id=audiencia.organizacion_id or grupo.organizacion_id)
    if clave in ("organizacion", "publico"):
        return Q(grupo__organizacion_id=grupo.organizacion_id)
    altura = int(clave.split(":")[1]) if clave and clave.startswith("grupo:") else 0
    raiz = next((antecesor for antecesor, (distancia, _nombre) in encima.items() if distancia == altura), grupo.pk)
    return Q(grupo__ascendencia__antecesor_id=raiz)


# Escalón de un grupo respecto al de referencia: 0 el propio grupo, 1 sus subgrupos, 1 + k los grupos
# que cuelgan del que está k niveles por encima, y uno más que todos para los que no cuelgan de ninguno
# (otros árboles de la organización o grupos invitados).
#   - grupo_id: el grupo.
#   - referencia: id del grupo de referencia.
#   - contenedores: los grupos de encima del de referencia que contienen a este.
#   - encima: los grupos de encima, de _encima().
def _escalon(grupo_id, referencia, contenedores, encima):
    if grupo_id == referencia:
        return 0
    if referencia in contenedores:
        return 1
    if contenedores:
        return 1 + min(encima[antecesor][0] for antecesor in contenedores)
    return 1 + max((distancia for distancia, _nombre in encima.values()), default=0) + 1


# Añade las personas de una audiencia privada que no han salido por ningún grupo (por ejemplo, alguien sin
# grupo en esta organización), en el escalón más lejano. Una consulta.
#   - audiencia: la audiencia privada.
#   - mejor: lo calculado hasta ahora ({usuario_id: (escalon, grupo, persona)}), que se completa.
def _anadir_sin_grupo(audiencia, mejor):
    for usuario_id, alias in audiencia.personas.filter(usuario__activo=True).exclude(usuario_id__in=list(mejor)).values_list(
        "usuario_id", "usuario__alias"
    ):
        mejor[usuario_id] = (99, "", PersonaCercana(alias=alias, marca=""))


# Reparte las personas en bloques, del escalón más cercano al más lejano, y en cada bloque, por grupos.
#   - mejor: {usuario_id: (escalon, nombre del grupo, persona)}.
#   - grupo: el grupo de referencia.
#   - encima: los grupos de encima, de _encima().
def _bloques(mejor, grupo, encima):
    por_escalon = {}
    for escalon, nombre, persona in mejor.values():
        por_escalon.setdefault(escalon, {}).setdefault(nombre, []).append(persona)
    nombre_a_la_altura = {distancia: nombre for distancia, nombre in encima.values()}
    bloques = []
    for posicion, escalon in enumerate(sorted(por_escalon)):
        titulo, explicacion = _titulo(escalon, grupo, nombre_a_la_altura)
        grupos = tuple(
            GrupoCercano(nombre=nombre, personas=tuple(sorted(personas, key=lambda p: p.alias.lower())))
            for nombre, personas in sorted(por_escalon[escalon].items())
        )
        etiqueta = ETIQUETAS_DE_CERCANIA[min(posicion, len(ETIQUETAS_DE_CERCANIA) - 1)]
        bloques.append(Bloque(titulo=titulo, explicacion=explicacion, cercania=etiqueta, nivel=posicion, grupos=grupos))
    return tuple(bloques)


# Título y explicación de un escalón.
#   - escalon: el escalón (ver _escalon).
#   - grupo: el grupo de referencia.
#   - nombre_a_la_altura: {distancia: nombre del grupo que está a esa altura}.
def _titulo(escalon, grupo, nombre_a_la_altura):
    if escalon == 0:
        return f"Aquí: {grupo.nombre}", "Personas de este mismo grupo."
    if escalon == 1:
        return "En sus subgrupos", f"Grupos que están dentro de {grupo.nombre}."
    altura = escalon - 1
    if altura in nombre_a_la_altura:
        nombre = nombre_a_la_altura[altura]
        que = ALTURAS.get(altura, f"{altura} niveles por encima")
        return f"{que}: {nombre}", f"El resto de {nombre} y de sus subgrupos."
    if escalon == 99:
        return "Otras personas que lo ven", "Personas añadidas a mano que no están en estos grupos."
    return "Más lejos", "Otros grupos de la organización o grupos invitados."
