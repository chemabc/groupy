"""
Qué puede hacer cada persona, calculado una vez y guardado en la caché (ver docs/diseno.md, apartado 3.5).

Reglas:
- El superadmin puede hacerlo todo.
- Quien está en un grupo tiene los permisos del rol «usuario» en ese grupo y en todos los que lo
  contienen (la pertenencia se hereda hacia arriba).
- Su rol en ese grupo (admin_grupo o uno personalizado) le da además los permisos de ese rol, solo en
  ese grupo (no se hereda).
- Admin de una organización: los permisos de «admin_org» en la organización y en todos sus grupos.
- Excepciones individuales: dan o quitan un permiso en un grupo concreto. Quitar gana a dar.
- Cometidos: dan permisos sobre aquello concreto en lo que se tienen (un debate, una reunión…).

Uso desde otros módulos:
    puede(usuario, "grupos.invitar", grupo=grupo)          → True o False
    exigir(usuario, "grupos.invitar", grupo=grupo)         → nada, o lanza SinPermiso con explicación
    tiene_cometido(usuario, "debates.facilitacion", "debates.debate", 7)
"""

from collections import defaultdict
from dataclasses import dataclass, field

from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from base.registro import registro
from grupos.models import AdminDeOrganizacion, Contencion, Grupo, Organizacion, Pertenencia

from .models import Cometido, ExcepcionDePermiso, PermisoConocido, PermisoDeRol, Rol

# Clave de la caché con el número de versión de todos los cálculos. Subirlo invalida a la vez el de
# todo el mundo (por ejemplo, cuando el superadmin cambia los permisos de un rol).
CLAVE_DE_VERSION = "permisos:version"
# Cuánto tiempo se guarda en la caché el cálculo de cada persona, en segundos (un día). Normalmente se
# invalida antes, al cambiar algo.
DURACION_EN_CACHE = 60 * 60 * 24


class SinPermiso(PermissionDenied):
    """
    Error de «no tienes permiso», con una explicación en lenguaje llano: qué permiso falta, qué roles lo
    tienen y a quién se le puede pedir. Django lo convierte en la pantalla 403 (base/templates/403.html).
    """


class PermisoNoDeclarado(LookupError):
    """Se ha preguntado por un permiso que ningún módulo declara (suele ser una errata en el código)."""


@dataclass(frozen=True)
class MapaDePermisos:
    """
    Lo que puede hacer una persona, ya calculado. Es lo que se guarda en la caché.
    """

    # Permisos en cada grupo: {id del grupo: conjunto de códigos}.
    grupos: dict = field(default_factory=dict)
    # Permisos en cada organización: {id de la organización: conjunto de códigos}.
    organizaciones: dict = field(default_factory=dict)
    # Cometidos que tiene: conjunto de (código del cometido, tipo de ancla, id).
    cometidos: frozenset = frozenset()
    # Permisos que le dan sus cometidos: conjunto de (código del permiso, tipo de ancla, id).
    por_cometido: frozenset = frozenset()
    # Si es superadmin (entonces puede todo y lo demás no se mira).
    es_superadmin: bool = False


# ── Caché ────────────────────────────────────────────────────────────────────────────────────────────


# Devuelve el número de versión actual de los cálculos (lo crea si no existe).
def _version():
    cache.add(CLAVE_DE_VERSION, 1, None)
    return cache.get(CLAVE_DE_VERSION, 1)


# Clave de la caché del cálculo de una persona, con la versión actual.
def _clave(usuario_id):
    return f"permisos:{usuario_id}:v{_version()}"


# Borra de la caché el cálculo de una persona, cuando termine bien la transacción en curso (si se
# borrara antes, otra petición podría volver a calcularlo con los datos viejos). Lo llaman las señales
# de permisos/senales.py al cambiar sus pertenencias, roles, excepciones o cometidos.
#   - usuario_id: de quién.
def invalidar_usuario(usuario_id):
    transaction.on_commit(lambda: cache.delete(_clave(usuario_id)))


# Invalida el cálculo de todo el mundo (al cambiar los permisos de un rol o la estructura de los
# grupos), subiendo la versión cuando termine bien la transacción en curso.
def invalidar_todos():
    transaction.on_commit(_subir_version)


# Sube en uno la versión de los cálculos. La usa invalidar_todos().
def _subir_version():
    try:
        cache.incr(CLAVE_DE_VERSION)
    except ValueError:  # La clave no existía (caché vacía): con crearla basta.
        cache.set(CLAVE_DE_VERSION, 2, None)


# ── Cálculo ──────────────────────────────────────────────────────────────────────────────────────────


# Devuelve {código del rol: conjunto de permisos} de todos los roles. Se guarda en la caché con la
# versión actual, porque es lo mismo para todo el mundo.
def permisos_de_los_roles():
    clave = f"permisos:roles:v{_version()}"
    roles = cache.get(clave)
    if roles is None:
        roles = defaultdict(set)
        for rol, permiso in PermisoDeRol.objects.values_list("rol_id", "permiso"):
            roles[rol].add(permiso)
        roles = dict(roles)
        cache.set(clave, roles, DURACION_EN_CACHE)
    return roles


# Devuelve el MapaDePermisos de una persona, de la caché o calculándolo (y guardándolo) si no está.
#   - usuario: el usuario (puede ser el anónimo, que no puede nada).
def permisos_de(usuario):
    if not getattr(usuario, "is_authenticated", False):
        return MapaDePermisos()
    if usuario.is_superuser:
        return MapaDePermisos(es_superadmin=True)
    clave = _clave(usuario.pk)
    mapa = cache.get(clave)
    if mapa is None:
        mapa = _calcular(usuario)
        cache.set(clave, mapa, DURACION_EN_CACHE)
    return mapa


# Calcula el mapa de permisos de una persona con las reglas del principio del fichero. Hace unas 6
# consultas, sea cual sea el número de grupos; por eso se guarda en la caché.
def _calcular(usuario):
    roles = permisos_de_los_roles()
    grupos = defaultdict(set)
    # Pertenencias directas: el rol «usuario» en cada grupo y en los que lo contienen, y su propio rol
    # (si no es «usuario») solo en ese grupo.
    directas = list(Pertenencia.objects.filter(usuario=usuario).values_list("grupo_id", "rol"))
    if directas:
        contenedores = Contencion.objects.filter(descendiente_id__in=[grupo for grupo, _rol in directas])
        for grupo in contenedores.values_list("antecesor_id", flat=True).distinct():
            grupos[grupo] |= roles.get(Pertenencia.USUARIO, set())
        for grupo, rol in directas:
            grupos[grupo] |= roles.get(rol, set())
    # Admin de organización: sus permisos en la organización y en todos sus grupos.
    organizaciones = list(AdminDeOrganizacion.objects.filter(usuario=usuario).values_list("organizacion_id", flat=True))
    de_admin_org = roles.get("admin_org", set())
    if organizaciones:
        for grupo in Grupo.objects.filter(organizacion_id__in=organizaciones).values_list("id", flat=True):
            grupos[grupo] |= de_admin_org
    # Excepciones individuales: primero se dan y después se quitan (quitar gana).
    excepciones = list(usuario.excepciones_de_permiso.values_list("grupo_id", "permiso", "concede"))
    for grupo, permiso, concede in excepciones:
        if concede:
            grupos[grupo].add(permiso)
    for grupo, permiso, concede in excepciones:
        if not concede:
            grupos[grupo].discard(permiso)
    # Cometidos y los permisos que dan sobre aquello en lo que se tienen.
    cometidos = frozenset(usuario.cometidos.values_list("codigo", "ancla_tipo", "ancla_id"))
    por_cometido = frozenset(
        (permiso, tipo, ancla_id)
        for codigo, tipo, ancla_id in cometidos
        if codigo in registro.cometidos
        for permiso in registro.cometidos[codigo].permisos
    )
    return MapaDePermisos(
        grupos={grupo: frozenset(codigos) for grupo, codigos in grupos.items()},
        organizaciones={organizacion: frozenset(de_admin_org) for organizacion in organizaciones},
        cometidos=cometidos,
        por_cometido=por_cometido,
    )


# ── Preguntar ────────────────────────────────────────────────────────────────────────────────────────


# Dice si una persona tiene un permiso en un grupo, en una organización o sobre algo concreto (ancla).
# Sin consultas a la base si el cálculo ya está en la caché.
#   - usuario: quién.
#   - permiso: código del permiso, declarado en algún contrato.
#   - grupo, organizacion: dónde (un objeto o su id).
#   - ancla: (tipo, id) de algo concreto, para los permisos que dan los cometidos.
def puede(usuario, permiso, grupo=None, organizacion=None, ancla=None):
    if permiso not in registro.permisos:
        raise PermisoNoDeclarado(f"Ningún módulo declara el permiso «{permiso}».")
    mapa = permisos_de(usuario)
    if mapa.es_superadmin:
        return True
    if grupo is not None and permiso in mapa.grupos.get(_id(grupo), ()):
        return True
    if organizacion is not None and permiso in mapa.organizaciones.get(_id(organizacion), ()):
        return True
    return ancla is not None and (permiso, ancla[0], ancla[1]) in mapa.por_cometido


# Dice si una persona tiene un permiso en algún sitio (en algún grupo o en alguna organización), sin
# decir dónde. Sirve para decidir si se le muestra una sección del menú (ver base/registro.py,
# puede_ver_entrada). Para hacer algo concreto, se usa puede() con el grupo.
def puede_en_alguna_parte(usuario, permiso):
    if permiso not in registro.permisos:
        raise PermisoNoDeclarado(f"Ningún módulo declara el permiso «{permiso}».")
    mapa = permisos_de(usuario)
    lugares = (*mapa.grupos.values(), *mapa.organizaciones.values())
    return mapa.es_superadmin or any(permiso in codigos for codigos in lugares)


# Organizaciones donde una persona tiene un permiso de organización (todas, si es superadmin), en orden
# alfabético. Devuelve una consulta (no la ejecuta). Lo usan las pantallas de «Configuración» para
# saber qué organizaciones puede ajustar cada cual.
#   - usuario: quién.
#   - permiso: código del permiso (por ejemplo, «audiencias.configurar»).
def organizaciones_con(usuario, permiso):
    if permiso not in registro.permisos:
        raise PermisoNoDeclarado(f"Ningún módulo declara el permiso «{permiso}».")
    mapa = permisos_de(usuario)
    consulta = Organizacion.objects.order_by("nombre")
    if mapa.es_superadmin:
        return consulta
    return consulta.filter(pk__in=[pk for pk, codigos in mapa.organizaciones.items() if permiso in codigos])


# Como puede(), pero si no tiene el permiso lanza SinPermiso con una explicación para la persona. Lo
# usan los servicios antes de hacer algo y el decorador @requiere_permiso de las vistas.
def exigir(usuario, permiso, grupo=None, organizacion=None, ancla=None):
    if not puede(usuario, permiso, grupo=grupo, organizacion=organizacion, ancla=ancla):
        raise SinPermiso(explicar_falta(permiso, grupo=grupo, organizacion=organizacion))


# Texto que explica por qué falta un permiso y a quién pedirlo: «Para invitar a un grupo de otra
# organización en «GRU Henares» hace falta el permiso «grupos.invitar». Lo tienen: Usuario. Puedes
# pedírselo a: Lince (admin de GRU Henares)…». Solo se calcula cuando falta el permiso, así que sus
# consultas no cuentan en las pantallas normales.
def explicar_falta(permiso, grupo=None, organizacion=None):
    descripcion = registro.permisos[permiso].descripcion
    descripcion = descripcion[:1].lower() + descripcion[1:]
    if grupo is not None and not isinstance(grupo, Grupo):
        grupo = Grupo.objects.select_related("organizacion").get(pk=grupo)
    if grupo is not None:
        organizacion = grupo.organizacion
    lugar = f" en «{grupo}»" if grupo is not None else (f" en «{organizacion}»" if organizacion is not None else "")
    roles = [str(rol) for rol in Rol.objects.filter(permisos__permiso=permiso)]
    partes = [f"Para {descripcion}{lugar} hace falta el permiso «{permiso}»."]
    partes.append(f"Lo tienen estos roles: {', '.join(roles)}." if roles else "De momento solo lo tiene el superadmin.")
    a_quien = []
    if grupo is not None:
        admins = Pertenencia.objects.filter(grupo=grupo, rol=Pertenencia.ADMIN_GRUPO).select_related("usuario")
        a_quien += [f"{admin.usuario} (admin de {grupo})" for admin in admins]
    if organizacion is not None:
        admins = AdminDeOrganizacion.objects.filter(organizacion_id=_id(organizacion)).select_related("usuario", "organizacion")
        a_quien += [f"{admin.usuario} (admin de {admin.organizacion})" for admin in admins]
    a_quien.append("el superadmin")
    partes.append(f"Puedes pedírselo a: {', '.join(a_quien)}.")
    return " ".join(partes)


# Id de un objeto o el propio número si ya lo es.
def _id(objeto):
    return getattr(objeto, "pk", objeto)


# ── Cometidos ────────────────────────────────────────────────────────────────────────────────────────


# Dice si una persona tiene un cometido en algo concreto. Sin consultas si el cálculo está en la caché.
#   - usuario: quién.
#   - codigo: código del cometido («debates.facilitacion»).
#   - ancla_tipo, ancla_id: aquello en lo que se tiene.
def tiene_cometido(usuario, codigo, ancla_tipo, ancla_id):
    return (codigo, ancla_tipo, ancla_id) in permisos_de(usuario).cometidos


# Da un cometido a una persona en algo concreto. Devuelve el cometido.
#   - usuario: a quién.
#   - codigo: código del cometido, declarado en algún contrato.
#   - ancla_tipo, ancla_id: aquello en lo que se tiene, de un tipo declarado como ancla.
#   - grupo: grupo donde vive aquello (sus miembros verán el cometido), o None.
@transaction.atomic
def asignar_cometido(usuario, codigo, ancla_tipo, ancla_id, grupo=None):
    if codigo not in registro.cometidos:
        raise ValidationError(f"Ningún módulo declara el cometido «{codigo}».")
    if ancla_tipo not in registro.anclas:
        raise ValidationError(f"Ningún módulo declara «{ancla_tipo}» como ancla.")
    cometido = Cometido(usuario=usuario, codigo=codigo, ancla_tipo=ancla_tipo, ancla_id=ancla_id, grupo=grupo)
    cometido.full_clean()
    cometido.save()
    return cometido


# Quita un cometido a una persona.
@transaction.atomic
def quitar_cometido(usuario, codigo, ancla_tipo, ancla_id):
    Cometido.objects.filter(usuario=usuario, codigo=codigo, ancla_tipo=ancla_tipo, ancla_id=ancla_id).delete()


# Cometidos de la gente de un grupo y de sus subgrupos, para que sus miembros vean quién hace qué.
# Devuelve una consulta (con el usuario cargado). Cuando exista «audiencias», se filtrará además por lo
# que cada cual puede ver.
#   - grupo: el grupo.
def cometidos_en_grupo(grupo):
    return Cometido.objects.filter(grupo__ascendencia__antecesor=grupo).select_related("usuario", "grupo")


# ── Roles y excepciones (pantalla «Usuarios → Roles y permisos») ─────────────────────────────────────


# Crea un rol personalizado de grupo (por ejemplo, «Tesorería»), sin permisos. Devuelve el rol.
#   - codigo: nombre interno, en minúsculas y sin tildes («tesoreria»).
#   - nombre: nombre visible.
#   - descripcion: para qué sirve.
@transaction.atomic
def crear_rol(codigo, nombre, descripcion=""):
    if Rol.objects.filter(codigo=codigo).exists():
        raise ValidationError({"codigo": f"Ya existe un rol con el código «{codigo}»."})
    rol = Rol(codigo=codigo, nombre=nombre, descripcion=descripcion, nivel=Rol.GRUPO)
    rol.full_clean()
    rol.save()
    return rol


# Deja a un rol exactamente con los permisos indicados: añade los que faltan y quita los demás. Las
# señales (permisos/senales.py) invalidan el cálculo de todo el mundo. Devuelve (añadidos, quitados).
#   - rol: el rol.
#   - codigos: los códigos de los permisos que debe tener (todos declarados en algún contrato).
@transaction.atomic
def poner_permisos_de_rol(rol, codigos):
    desconocidos = set(codigos) - set(registro.permisos)
    if desconocidos:
        raise ValidationError(f"Ningún módulo declara estos permisos: {', '.join(sorted(desconocidos))}.")
    actuales = set(rol.permisos.values_list("permiso", flat=True))
    nuevos, sobran = set(codigos) - actuales, actuales - set(codigos)
    PermisoDeRol.objects.bulk_create([PermisoDeRol(rol=rol, permiso=codigo) for codigo in sorted(nuevos)])
    rol.permisos.filter(permiso__in=sobran).delete()
    # bulk_create y delete en bloque no lanzan las señales de cada fila: se invalida a mano.
    invalidar_todos()
    return sorted(nuevos), sorted(sobran)


# Borra un rol personalizado. Los del sistema no se pueden borrar, ni uno que alguien tenga todavía.
#   - rol: el rol.
@transaction.atomic
def borrar_rol(rol):
    if rol.del_sistema:
        raise ValidationError(f"«{rol}» es un rol del sistema: no se puede borrar.")
    personas = Pertenencia.objects.filter(rol=rol.codigo).count()
    if personas:
        raise ValidationError(
            f"{personas} persona{'s tienen' if personas != 1 else ' tiene'} el rol «{rol}»: cámbiales antes el rol en la ficha de su grupo."
        )
    rol.delete()


# Da o quita un permiso suelto a una persona en un grupo (excepción individual). Si ya había una
# excepción para ese permiso, persona y grupo, la sustituye. Devuelve la excepción.
#   - usuario: a quién.
#   - grupo: en qué grupo.
#   - permiso: código del permiso.
#   - concede: True para dar, False para quitar.
#   - motivo: por qué (queda a la vista del grupo).
@transaction.atomic
def poner_excepcion(usuario, grupo, permiso, concede, motivo):
    if permiso not in registro.permisos:
        raise ValidationError(f"Ningún módulo declara el permiso «{permiso}».")
    excepcion, _nueva = ExcepcionDePermiso.objects.update_or_create(
        usuario=usuario, grupo=grupo, permiso=permiso, defaults={"concede": concede, "motivo": motivo}
    )
    return excepcion


@dataclass(frozen=True)
class Explicacion:
    """
    El razonamiento de si una persona tiene un permiso en un grupo, paso a paso, para la pantalla de
    soporte «Explicar un permiso». Debe decidir siempre igual que puede() (hay una prueba que lo comprueba).
    """

    # Si lo tiene.
    tiene: bool
    # Pasos, en lenguaje llano, en el orden en que se aplican las reglas.
    pasos: tuple


# Explica paso a paso si una persona tiene un permiso en un grupo, siguiendo las mismas reglas que
# _calcular() (ver el principio del fichero). Mira la base de datos directamente, sin la caché: es
# para soporte, no para las pantallas normales.
#   - usuario: de quién.
#   - permiso: código del permiso.
#   - grupo: el grupo (con su organización).
def explicar_permiso(usuario, permiso, grupo):
    if permiso not in registro.permisos:
        raise PermisoNoDeclarado(f"Ningún módulo declara el permiso «{permiso}».")
    if usuario.is_superuser:
        return Explicacion(True, ("Es superadmin: puede hacerlo todo, sin mirar nada más.",))
    roles = permisos_de_los_roles()
    nombres = dict(Rol.objects.values_list("codigo", "nombre"))
    pasos, tiene = [], False

    # Función interna: dice si un rol tiene el permiso, en palabras.
    def con_o_sin(rol):
        return "que lo tiene" if permiso in roles.get(rol, ()) else "que no lo tiene"

    directas = list(Pertenencia.objects.filter(usuario=usuario).select_related("grupo"))
    en_el_grupo = next((p for p in directas if p.grupo_id == grupo.pk), None)
    rama = set(Contencion.objects.filter(antecesor=grupo).values_list("descendiente_id", flat=True))
    debajo = [p for p in directas if p.grupo_id in rama]
    if debajo:
        lugares = ", ".join(f"«{p.grupo}»" for p in debajo)
        pasos.append(f"Es miembro de «{grupo}» (está en {lugares}): tiene el rol «{nombres['usuario']}», {con_o_sin('usuario')}.")
        tiene = permiso in roles.get("usuario", ())
    else:
        pasos.append(f"No está en «{grupo}» ni en ninguno de sus subgrupos: no tiene ahí el rol «{nombres['usuario']}».")
    if en_el_grupo is not None and en_el_grupo.rol != Pertenencia.USUARIO:
        rol = en_el_grupo.rol
        pasos.append(f"En «{grupo}» tiene además el rol «{nombres.get(rol, rol)}» (solo vale en ese grupo), {con_o_sin(rol)}.")
        tiene = tiene or permiso in roles.get(rol, ())
    if AdminDeOrganizacion.objects.filter(usuario=usuario, organizacion_id=grupo.organizacion_id).exists():
        pasos.append(f"Es admin de «{grupo.organizacion}»: tiene el rol «{nombres['admin_org']}» en todos sus grupos, {con_o_sin('admin_org')}.")
        tiene = tiene or permiso in roles.get("admin_org", ())
    excepcion = ExcepcionDePermiso.objects.filter(usuario=usuario, grupo=grupo, permiso=permiso).first()
    if excepcion is not None:
        verbo = "se le da" if excepcion.concede else "se le quita (quitar gana a cualquier rol)"
        pasos.append(f"Tiene una excepción en «{grupo}»: {verbo}. Motivo: {excepcion.motivo}")
        tiene = excepcion.concede
    pasos.append("Resultado: lo tiene." if tiene else "Resultado: no lo tiene.")
    return Explicacion(tiene, tuple(pasos))


# ── Permisos por defecto ─────────────────────────────────────────────────────────────────────────────


# Roles que deben existir siempre: código, nombre visible, descripción y nivel. Los crea la migración
# 0002 y, si faltan (por ejemplo, tras vaciar la base en las pruebas), sincronizar_permisos().
ROLES_DEL_SISTEMA = [
    ("usuario", "Usuario", "Cualquier miembro de un grupo. Sus permisos valen en su grupo y en todos los que lo contienen.", Rol.GRUPO),
    ("admin_grupo", "Admin del grupo", "Cuida la estructura del grupo; no filtra. Sus permisos valen solo en ese grupo.", Rol.GRUPO),
    ("admin_org", "Admin de la organización", "Administra una organización. Sus permisos valen en ella y en todos sus grupos.", Rol.ORGANIZACION),
]


# Crea los roles del sistema que falten y da a cada permiso nuevo (que no se había visto nunca) los roles
# que dice su contrato, y lo apunta como conocido. Los permisos ya conocidos no se tocan: si el
# superadmin se lo quitó a un rol, sigue quitado. Se ejecuta sola después de cada «migrate» (y cuando
# las pruebas vacían la base; ver permisos/apps.py) y con la orden «sincronizar_permisos». Devuelve los
# códigos de los permisos nuevos.
@transaction.atomic
def sincronizar_permisos():
    Rol.objects.bulk_create(
        [
            Rol(codigo=codigo, nombre=nombre, descripcion=descripcion, nivel=nivel, del_sistema=True)
            for codigo, nombre, descripcion, nivel in ROLES_DEL_SISTEMA
        ],
        ignore_conflicts=True,
    )
    conocidos = set(PermisoConocido.objects.values_list("codigo", flat=True))
    nuevos = [permiso for codigo, permiso in registro.permisos.items() if codigo not in conocidos]
    if not nuevos:
        return []
    existentes = set(Rol.objects.values_list("codigo", flat=True))
    PermisoDeRol.objects.bulk_create(
        [PermisoDeRol(rol_id=rol, permiso=permiso.codigo) for permiso in nuevos for rol in permiso.roles if rol in existentes],
        ignore_conflicts=True,
    )
    PermisoConocido.objects.bulk_create([PermisoConocido(codigo=permiso.codigo) for permiso in nuevos], ignore_conflicts=True)
    invalidar_todos()
    return [permiso.codigo for permiso in nuevos]
