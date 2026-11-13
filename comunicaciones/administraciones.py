"""
Las administraciones: a quién se escribe cuando se escribe «a la administración», y en nombre de quién
habla un admin. Hay tres clases:

- la de un grupo (sus admins y, por encima, los admins de su organización y el superadmin);
- la de una organización (sus admins y el superadmin);
- la de la plataforma (el superadmin).

Nunca se escribe al alias privado de un admin: se escribe a la administración, y quien responde firma
como «Admin de GRU Henares (Lince)». Las conversaciones con una administración las pueden leer quienes la
atienden (ver puede_atender), no las de entre personas.

Lo usan los servicios y las pantallas de avisos y conversaciones de este módulo.
"""

from dataclasses import dataclass

from grupos.models import AdminDeOrganizacion, Contencion, Grupo, Organizacion, Pertenencia
from grupos.servicios import grupos_de
from permisos.servicios import puede


@dataclass(frozen=True)
class Buzon:
    """Una administración concreta: la de un grupo, la de una organización o la de la plataforma."""

    # El grupo, si es la administración de un grupo.
    grupo: Grupo | None = None
    # La organización, si es la administración de una organización.
    organizacion: Organizacion | None = None

    # Clave para los formularios: «g5» (grupo 5), «o2» (organización 2) o «p» (plataforma).
    @property
    def clave(self):
        if self.grupo:
            return f"g{self.grupo.pk}"
        if self.organizacion:
            return f"o{self.organizacion.pk}"
        return "p"

    # Nombre visible: «Admin de GRU Henares (ORG Tajo)», «Admin de ORG Tajo» o «Superadmin».
    @property
    def nombre(self):
        if self.grupo:
            return f"Admin de {self.grupo.nombre} ({self.grupo.organizacion.nombre})"
        if self.organizacion:
            return f"Admin de {self.organizacion.nombre}"
        return "Superadmin"


# Las administraciones en nombre de las cuales puede avisar una persona: los grupos de los que es admin,
# las organizaciones de las que es admin y, si es superadmin, la plataforma. Siempre que tenga el
# permiso «comunicaciones.avisar» ahí. Unas 2 consultas.
#   - usuario: quién.
def administraciones_de(usuario):
    buzones = []
    if usuario.is_superuser:
        buzones.append(Buzon())
    for organizacion in Organizacion.objects.filter(admins__usuario=usuario).order_by("nombre"):
        if puede(usuario, "comunicaciones.avisar", organizacion=organizacion):
            buzones.append(Buzon(organizacion=organizacion))
    grupos = Grupo.objects.en_orden_de_arbol().select_related("organizacion").filter(
        pertenencias__usuario=usuario, pertenencias__rol=Pertenencia.ADMIN_GRUPO
    )
    buzones += [Buzon(grupo=grupo) for grupo in grupos if puede(usuario, "comunicaciones.avisar", grupo=grupo)]
    return buzones


# Las administraciones a las que puede escribir una persona: la de cada uno de sus grupos (también los
# que contienen a los suyos), la de cada una de sus organizaciones y el superadmin. Unas 2 consultas.
#   - usuario: quién.
def administraciones_para_escribir(usuario):
    grupos = list(Grupo.objects.en_orden_de_arbol().select_related("organizacion").filter(pk__in=grupos_de(usuario)))
    organizaciones = sorted({grupo.organizacion for grupo in grupos}, key=lambda organizacion: organizacion.nombre)
    return [Buzon(grupo=grupo) for grupo in grupos] + [Buzon(organizacion=o) for o in organizaciones] + [Buzon()]


# Busca una administración por su clave («g5», «o2», «p») entre una lista. Devuelve None si no está.
def buscar(buzones, clave):
    return next((buzon for buzon in buzones if buzon.clave == clave), None)


# Dice si una persona atiende (lee y responde) lo que llega a una administración: la de un grupo, sus
# admins y los admins de su organización; la de una organización, sus admins; y siempre el superadmin.
#   - usuario: quién.
#   - grupo_id, organizacion_id: la administración (los dos vacíos: la plataforma).
#   - organizacion_del_grupo: la organización del grupo (su id), si es la de un grupo.
def puede_atender(usuario, grupo_id, organizacion_id, organizacion_del_grupo=None):
    if usuario.is_superuser:
        return True
    if grupo_id:
        if Pertenencia.objects.filter(usuario=usuario, grupo_id=grupo_id, rol=Pertenencia.ADMIN_GRUPO).exists():
            return True
        organizacion_id = organizacion_del_grupo
    return bool(organizacion_id) and AdminDeOrganizacion.objects.filter(usuario=usuario, organizacion_id=organizacion_id).exists()


# Ids de los grupos que alcanza una administración al avisar: los del subárbol del grupo, todos los de la
# organización o, la plataforma, todos. Una consulta.
#   - buzon: la administración.
def grupos_que_alcanza(buzon):
    if buzon.grupo:
        return set(Contencion.objects.filter(antecesor=buzon.grupo).values_list("descendiente_id", flat=True))
    if buzon.organizacion:
        return set(Grupo.objects.filter(organizacion=buzon.organizacion).values_list("pk", flat=True))
    return set(Grupo.objects.values_list("pk", flat=True))


# Condición para filtrar lo que pertenece a las administraciones que atiende una persona (avisos,
# conversaciones): las de los grupos de los que es admin, y las de sus organizaciones y de todos sus
# grupos si es admin de la organización. Devuelve un Q de Django, None si es superadmin (todo) o un Q que
# no encaja con nada si no atiende ninguna. 2 consultas.
#   - usuario: quién.
def filtro_de_lo_que_atiende(usuario):
    from django.db.models import Q

    if usuario.is_superuser:
        return None
    grupos = list(Pertenencia.objects.filter(usuario=usuario, rol=Pertenencia.ADMIN_GRUPO).values_list("grupo_id", flat=True))
    organizaciones = list(AdminDeOrganizacion.objects.filter(usuario=usuario).values_list("organizacion_id", flat=True))
    return Q(grupo_id__in=grupos) | Q(grupo__organizacion_id__in=organizaciones) | Q(grupo__isnull=True, organizacion_id__in=organizaciones)
