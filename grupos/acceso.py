"""
Qué grupos ve cada persona en las pantallas de «Organizaciones y grupos», y qué puede ver de cada uno.

- Sus grupos: aquellos en los que está y los que los contienen (grupos_de, en servicios.py).
- Los que administra: los grupos donde tiene el permiso «grupos.ver_arbol» (de entrada, el admin del
  grupo y el admin de la organización) y todos sus subgrupos. Es lo que ve en «Árbol».
- La lista de miembros de un grupo la ven quienes lo administran y, si la organización lo permite
  (Organizacion.miembros_ven_miembros), quienes tienen ahí «grupos.ver_miembros» (de entrada, cualquier
  miembro).

El superadmin lo ve todo.

Lo usan las vistas de este módulo (grupos/views.py) y el contador del menú (grupos/contadores.py).
"""

from dataclasses import dataclass

from permisos.servicios import permisos_de, puede

from .models import Contencion, Grupo
from .servicios import grupos_de


@dataclass(frozen=True)
class Alcance:
    """
    Lo que una persona alcanza a ver de la estructura, calculado una vez por petición.
    """

    # Si es superadmin (entonces lo ve todo y los conjuntos de abajo no se miran).
    todo: bool
    # Ids de los grupos de los que es miembro (también los que contienen a los suyos).
    mios: frozenset
    # Ids de los grupos que administra, con todos sus subgrupos.
    administrados: frozenset

    # Dice si ve un grupo (su ficha).
    def ve(self, grupo_id):
        return self.todo or grupo_id in self.mios or grupo_id in self.administrados

    # Ids de todos los grupos que ve, o None si los ve todos.
    def visibles(self):
        return None if self.todo else self.mios | self.administrados


# Calcula el Alcance de una persona. Hace 2 consultas (ninguna si es superadmin); los permisos salen de
# la caché.
#   - usuario: quien mira.
def alcance_de(usuario):
    if usuario.is_superuser:
        return Alcance(todo=True, mios=frozenset(), administrados=frozenset())
    return Alcance(todo=False, mios=frozenset(grupos_de(usuario)), administrados=frozenset(grupos_que_administra(usuario)))


# Ids de los grupos que una persona administra (donde tiene «grupos.ver_arbol») y de todos sus
# subgrupos. Una consulta, o ninguna si no administra nada.
#   - usuario: quien mira (no superadmin).
def grupos_que_administra(usuario):
    raices = [grupo for grupo, codigos in permisos_de(usuario).grupos.items() if "grupos.ver_arbol" in codigos]
    if not raices:
        return set()
    return set(Contencion.objects.filter(antecesor_id__in=raices).values_list("descendiente_id", flat=True))


# Dice si una persona ve la lista de miembros de un grupo: el superadmin y quienes lo administran,
# siempre; los demás, si tienen ahí «grupos.ver_miembros» y la organización no lo ha cerrado. Sin
# consultas (el grupo debe venir con su organización cargada).
#   - usuario: quien mira.
#   - grupo: el grupo, con select_related("organizacion").
#   - alcance: su Alcance.
def ve_miembros(usuario, grupo, alcance):
    if alcance.todo or grupo.pk in alcance.administrados:
        return True
    return grupo.organizacion.miembros_ven_miembros and puede(usuario, "grupos.ver_miembros", grupo=grupo)


# Consulta de los grupos que una persona ve, en orden de árbol (con su camino y su organización).
#   - alcance: su Alcance.
#   - solo_administrados: si se quieren solo los que administra (para «Árbol»).
def grupos_visibles(alcance, solo_administrados=False):
    consulta = Grupo.objects.en_orden_de_arbol().select_related("organizacion")
    if alcance.todo:
        return consulta
    return consulta.filter(pk__in=alcance.administrados if solo_administrados else alcance.visibles())
