"""
Árboles de grupos: el componente que dibuja, por cada organización, sus grupos colgando unos de otros
(ver docs/diseno.md, apartado 8.1, «Árboles de grupos»).

Qué sale en el árbol de una persona:
- Los grupos en los que está (directos), con su rol si no es «usuario».
- Los que contienen a uno de los suyos: también es miembro de ellos, por herencia (en gris).
- Los que administra, con todos sus subgrupos (marcados «administras»).
- Si se pide, un grupo concreto «que se está mirando» (recuadro rojo) y los que lo contienen.

Colores (los mismos en todas las pantallas): la organización, en violeta; la asamblea base de la persona,
con fondo amarillo; el grupo que se mira, con un recuadro rojo.

Lo calcula arboles_de() y lo pinta la plantilla «grupos/arboles.html» (y, para cada grupo,
«grupos/nodo_de_arbol.html»). Lo usan «Organizaciones y grupos → Mis grupos → Árboles» y la ficha de cada
grupo (grupos/views.py); servirá también para «Inicio → Mis datos».
"""

from dataclasses import dataclass, field

from django.db.models import Exists, OuterRef, Q

from permisos.models import Rol

from .acceso import grupos_que_administra
from .models import AdminDeOrganizacion, Contencion, Grupo, Pertenencia


@dataclass
class NodoDeArbol:
    """
    Un grupo dentro del árbol, con lo que hay que saber para pintarlo y sus subgrupos colgando.
    """

    # Número y nombre del grupo (el nombre lleva a su ficha).
    id: int
    nombre: str
    # Si la persona está directamente en este grupo.
    directo: bool = False
    # Si es su asamblea base (fondo amarillo).
    base: bool = False
    # Nombre visible de su rol en el grupo, si no es el normal («Admin de grupo»…); si no, vacío.
    rol: str = ""
    # Si contiene a uno de sus grupos: es miembro por herencia (en gris).
    heredado: bool = False
    # Si lo administra (él o uno de los que lo contienen).
    administra: bool = False
    # Si es el más alto de los que administra en su rama: solo ahí se pinta «administras», porque lo de
    # debajo se sobrentiende.
    administra_desde_aqui: bool = False
    # Si es el grupo que se está mirando (recuadro rojo).
    actual: bool = False
    # Los subgrupos que también salen en el árbol, en orden alfabético.
    hijos: list = field(default_factory=list)


@dataclass
class ArbolDeOrganizacion:
    """
    El árbol de una organización: la organización arriba y sus grupos debajo.
    """

    # La organización (objeto Organizacion).
    organizacion: object
    # Si quien mira es admin de la organización (entonces el nombre lleva a su ficha).
    admin: bool
    # Los grupos de arriba del todo de lo que se ve (normalmente, uno: el grupo general).
    raices: list


# Nombres visibles de los roles de grupo, por su código: {"usuario": "Usuario", …}. Una consulta.
def nombres_de_roles_de_grupo():
    return dict(Rol.objects.filter(nivel=Rol.GRUPO).order_by("nombre").values_list("codigo", "nombre"))


# Calcula los árboles de grupos de una persona, uno por organización, en orden alfabético. Cuesta de 2 a
# 5 consultas, sean cuantos sean los grupos (los permisos salen de la caché).
#   - usuario: quien mira.
#   - actual: número del grupo que se está mirando (sale con recuadro rojo y, si no estaba, se añade con
#     los que lo contienen), o None.
#   - organizacion: número de una organización, para sacar solo su árbol, o None para todas.
#   - administrados: ids de los grupos que administra, si ya se han calculado (Alcance.administrados), para
#     no repetir la consulta; None para calcularlos aquí.
#   - roles: los nombres de los roles de grupo, si ya se han leído (nombres_de_roles_de_grupo()); None para
#     leerlos aquí si hacen falta.
def arboles_de(usuario, actual=None, organizacion=None, administrados=None, roles=None):
    directas = {pertenencia.grupo_id: pertenencia for pertenencia in Pertenencia.objects.filter(usuario=usuario)}
    if administrados is None:
        administrados = set() if usuario.is_superuser else grupos_que_administra(usuario)
    semillas = set(directas) | ({actual} if actual else set())
    if not semillas and not administrados:
        return []
    contienen_uno_mio = Contencion.objects.filter(antecesor_id=OuterRef("pk"), descendiente_id__in=list(directas))
    contenidos = Q(pk__in=Contencion.objects.filter(descendiente_id__in=list(semillas)).values("antecesor_id"))
    consulta = (
        Grupo.objects.en_orden_de_arbol()
        .select_related("organizacion")
        .filter(contenidos | Q(pk__in=list(administrados)))
        .annotate(heredado=Exists(contienen_uno_mio))
    )
    if organizacion is not None:
        consulta = consulta.filter(organizacion_id=organizacion)
    grupos = list(consulta)
    if not grupos:
        return []
    con_rol = any(pertenencia.rol != Pertenencia.USUARIO for pertenencia in directas.values())
    if roles is None:
        roles = nombres_de_roles_de_grupo() if con_rol else {}
    admin_de = set(AdminDeOrganizacion.objects.filter(usuario=usuario).values_list("organizacion_id", flat=True))
    return _montar(grupos, directas, administrados, actual, roles, admin_de)


# Cuelga cada grupo de su padre y junta los grupos por organización. Sin consultas.
#   - grupos: los grupos que salen, en orden de árbol (cada uno después de su padre), con «heredado».
#   - directas: las pertenencias de la persona, por número de grupo.
#   - administrados: ids de los grupos que administra.
#   - actual: número del grupo que se mira, o None.
#   - roles: nombres visibles de los roles, por su código.
#   - admin_de: ids de las organizaciones que administra.
def _montar(grupos, directas, administrados, actual, roles, admin_de):
    arboles = {}
    nodos = {}
    for grupo in grupos:
        pertenencia = directas.get(grupo.pk)
        nodo = NodoDeArbol(
            id=grupo.pk,
            nombre=grupo.nombre,
            directo=pertenencia is not None,
            base=pertenencia is not None and pertenencia.es_base,
            rol=roles.get(pertenencia.rol, pertenencia.rol) if pertenencia and pertenencia.rol != Pertenencia.USUARIO else "",
            heredado=pertenencia is None and grupo.heredado,
            administra=grupo.pk in administrados,
            actual=grupo.pk == actual,
        )
        nodo.administra_desde_aqui = nodo.administra and grupo.padre_id not in administrados
        nodos[grupo.pk] = nodo
        arbol = arboles.get(grupo.organizacion_id)
        if arbol is None:
            arbol = arboles[grupo.organizacion_id] = ArbolDeOrganizacion(
                organizacion=grupo.organizacion, admin=grupo.organizacion_id in admin_de, raices=[]
            )
        padre = nodos.get(grupo.padre_id)
        (padre.hijos if padre else arbol.raices).append(nodo)
    return list(arboles.values())
