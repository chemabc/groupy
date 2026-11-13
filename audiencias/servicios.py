"""
Quién puede ver cada cosa (ver docs/diseno.md, apartado 3.4).

Para crear la audiencia de algo, los módulos usan audiencia_para() (con lo que eligió la persona:
privado, su grupo y los de arriba, unos grupos, toda la organización o público), o las funciones de más
abajo. Para listar solo lo que alguien puede ver: filtrar_visibles(consulta, usuario).

**Regla entre organizaciones** (13 de noviembre de 2026, a petición de la persona usuaria): una audiencia
nunca incluye grupos ni personas de otra organización, salvo que lo invitado (el ancla: un proyecto…)
tenga una invitación hecha por alguien con permiso del grupo que invita y aceptada por alguien con permiso
del grupo invitado (grupos/servicios.py, invitar y responder_invitacion). Se comprueba aquí siempre, la
pida quien la pida.

Qué ve cada persona se calcula una vez (2 consultas) y se guarda en la caché con versión, como los
permisos. Las señales de audiencias/senales.py la invalidan.
"""

from dataclasses import dataclass

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from grupos.models import Contencion, InvitacionDeGrupo, Pertenencia

from .models import Audiencia, ConfiguracionDeVisibilidad, GrupoDeAudiencia, PersonaDeAudiencia

# Clave de la caché con la versión de todos los cálculos (subirla invalida el de todo el mundo).
CLAVE_DE_VERSION = "audiencias:version"
# Cuánto se guarda en la caché el cálculo de cada persona, en segundos (un día).
DURACION_EN_CACHE = 60 * 60 * 24
# Por debajo de este número de personas no se dice cuántas son, para no dar pistas (apartado 8.2).
MINIMO_PARA_CONTAR = 5


# ── Regla entre organizaciones ───────────────────────────────────────────────────────────────────────


# Ids de los grupos de otras organizaciones que han aceptado una invitación de «organizacion» para algo
# concreto (el ancla). Solo cuentan las invitaciones aceptadas: las pendientes, rechazadas o retiradas no
# abren nada.
#   - organizacion: la organización dueña de lo que se ve.
#   - ancla: (tipo, id) de lo invitado, o None (entonces, ninguno).
def grupos_invitados(organizacion, ancla):
    if ancla is None:
        return set()
    invitaciones = InvitacionDeGrupo.objects.filter(
        ancla_tipo=ancla[0],
        ancla_id=ancla[1],
        estado=InvitacionDeGrupo.ACEPTADA,
        grupo_que_invita__organizacion=organizacion,
        respondida_por__isnull=False,
    )
    return set(invitaciones.values_list("grupo_invitado_id", flat=True))


# Comprueba que unos grupos pueden entrar en una audiencia de «organizacion»: los suyos, sí; los de otra
# organización, solo si son un grupo invitado (con invitación aceptada para el ancla) o un subgrupo suyo.
# Lanza ValidationError, con explicación, si alguno no puede. Devuelve si hay alguno de fuera.
def _comprobar_grupos(grupos, organizacion, ancla):
    ajenos = [grupo for grupo in grupos if grupo.organizacion_id != organizacion.pk]
    if not ajenos:
        return False
    invitados = grupos_invitados(organizacion, ancla)
    dentro_de_invitados = set(
        Contencion.objects.filter(descendiente__in=ajenos, antecesor_id__in=invitados).values_list("descendiente_id", flat=True)
    )
    for grupo in ajenos:
        if grupo.pk not in dentro_de_invitados:
            raise ValidationError(
                f"«{grupo}» es de otra organización y no ha aceptado ninguna invitación para esto: no puede verlo."
            )
    return True


# Comprueba que unas personas pueden entrar en una audiencia de «organizacion»: si están en algún grupo de
# ella, sí; si no, solo si están en un grupo invitado (o en un subgrupo suyo) para el ancla. Lanza
# ValidationError, con explicación, si alguna no puede.
def _comprobar_personas(usuarios, organizacion, ancla):
    ids = {usuario.pk for usuario in usuarios}
    de_la_organizacion = set(
        Pertenencia.objects.filter(usuario_id__in=ids, grupo__organizacion=organizacion).values_list("usuario_id", flat=True)
    )
    pendientes = ids - de_la_organizacion
    if not pendientes:
        return
    invitados = grupos_invitados(organizacion, ancla)
    por_invitacion = set(
        Pertenencia.objects.filter(usuario_id__in=pendientes, grupo__ascendencia__antecesor_id__in=invitados).values_list(
            "usuario_id", flat=True
        )
    )
    for usuario in usuarios:
        if usuario.pk in pendientes - por_invitacion:
            raise ValidationError(
                f"«{usuario}» no está en «{organizacion}» ni en un grupo invitado a esto: no puede verlo."
            )


# ── Crear audiencias ─────────────────────────────────────────────────────────────────────────────────


# Configuración de visibilidad de una organización: la guardada o, si no tiene, la de por defecto (sin
# guardar), que es la más cerrada.
def configuracion_de(organizacion):
    try:
        return organizacion.configuracion_de_visibilidad
    except ConfiguracionDeVisibilidad.DoesNotExist:
        return ConfiguracionDeVisibilidad(organizacion=organizacion)


# Crea la audiencia de algo a partir de lo que eligió quien lo publica, comprobando lo que permite su
# organización. Es la función que usan los módulos. Devuelve la audiencia.
#   - nivel: «privado», «grupo» (su grupo y, con «altura», los de arriba), «grupos» (unos concretos),
#     «organizacion» o «publico».
#   - grupo: el grupo desde el que se publica (marca la organización y el punto de partida).
#   - altura: con «grupo», cuántos niveles se sube (0 su grupo, 1 el padre, 2 el abuelo…).
#   - grupos: con «grupos», los elegidos (de su organización o invitados).
#   - personas: con «privado», las personas implicadas.
#   - ancla: (tipo, id) de lo que se publica. Hace falta para incluir a grupos o personas invitados.
def audiencia_para(nivel, grupo, altura=0, grupos=(), personas=(), ancla=None):
    organizacion = grupo.organizacion
    configuracion = configuracion_de(organizacion)
    if nivel == "privado":
        return crear_privada(personas, organizacion=organizacion, ancla=ancla)
    if nivel == "grupo":
        if altura > configuracion.altura_maxima:
            raise ValidationError(
                f"«{organizacion}» permite subir como mucho {configuracion.altura_maxima} nivel(es) por encima del grupo."
            )
        arriba = Contencion.objects.filter(descendiente=grupo, distancia=altura).select_related("antecesor").first()
        if arriba is None:
            raise ValidationError(f"«{grupo}» no tiene un grupo {altura} nivel(es) por encima.")
        return audiencia_de_grupos([arriba.antecesor], organizacion)
    if nivel == "grupos":
        return audiencia_de_grupos(grupos, organizacion, ancla=ancla)
    if nivel == "organizacion":
        if not configuracion.permite_toda_la_organizacion:
            raise ValidationError(f"«{organizacion}» no permite publicar para toda la organización.")
        return audiencia_de_organizacion(organizacion)
    if nivel == "publico":
        if not configuracion.permite_publico:
            raise ValidationError(f"«{organizacion}» no permite publicar para cualquiera.")
        return audiencia_publica()
    raise ValidationError(f"Nivel de visibilidad desconocido: «{nivel}».")


# Crea una audiencia privada (de una sola cosa), con las personas implicadas. No se comparte con nada.
#   - personas: las personas que lo ven.
#   - organizacion: la organización dueña de lo que se ve (para la regla entre organizaciones).
#   - ancla: (tipo, id) de lo que se ve.
#   - personal: contenido personal privado (solo de una persona; ni el superadmin lo ve).
@transaction.atomic
def crear_privada(personas, organizacion=None, ancla=None, personal=False):
    personas = list(personas)
    if personal and len(personas) != 1:
        raise ValidationError("Lo personal es de una sola persona.")
    if not personal and organizacion is None:
        raise ValidationError("Una audiencia privada necesita la organización dueña de lo que se ve.")
    if organizacion is not None:
        _comprobar_personas(personas, organizacion, ancla)
    audiencia = Audiencia.objects.create(
        tipo=Audiencia.PRIVADA,
        organizacion=organizacion,
        ancla_tipo=ancla[0] if ancla else "",
        ancla_id=ancla[1] if ancla else None,
        personal=personal,
    )
    for usuario in personas:
        PersonaDeAudiencia.objects.create(audiencia=audiencia, usuario=usuario)
    return audiencia


# Añade personas a una audiencia privada (por ejemplo, quien se inscribe o recibe un cometido),
# comprobando la regla entre organizaciones.
@transaction.atomic
def anadir_personas(audiencia, personas):
    if audiencia.tipo != Audiencia.PRIVADA or audiencia.personal:
        raise ValidationError("Solo se añaden personas a una audiencia privada que no sea personal.")
    ancla = (audiencia.ancla_tipo, audiencia.ancla_id) if audiencia.ancla_tipo else None
    _comprobar_personas(personas, audiencia.organizacion, ancla)
    for usuario in personas:
        PersonaDeAudiencia.objects.get_or_create(audiencia=audiencia, usuario=usuario)


# Quita personas de una audiencia privada.
@transaction.atomic
def quitar_personas(audiencia, personas):
    for fila in PersonaDeAudiencia.objects.filter(audiencia=audiencia, usuario__in=personas):
        fila.delete()


# Devuelve la audiencia «estos grupos y sus subgrupos», creándola si no existe. Si todos son de la
# organización, se comparte con cualquier otra cosa que elija lo mismo. Si hay grupos invitados, es solo
# de lo invitado (el ancla), porque la invitación vale para eso y nada más.
#   - grupos: los grupos.
#   - organizacion: la organización dueña de lo que se ve.
#   - ancla: (tipo, id) de lo que se ve; hace falta si hay grupos de otra organización.
@transaction.atomic
def audiencia_de_grupos(grupos, organizacion, ancla=None):
    grupos = list(grupos)
    if not grupos:
        raise ValidationError("Hay que elegir al menos un grupo.")
    hay_invitados = _comprobar_grupos(grupos, organizacion, ancla)
    huella = "grupos:" + ",".join(str(pk) for pk in sorted({grupo.pk for grupo in grupos}))
    if hay_invitados:
        huella += f"@{ancla[0]}:{ancla[1]}"
    audiencia, creada = Audiencia.objects.get_or_create(
        huella=huella,
        defaults={
            "tipo": Audiencia.GRUPOS,
            "organizacion": organizacion,
            "ancla_tipo": ancla[0] if hay_invitados else "",
            "ancla_id": ancla[1] if hay_invitados else None,
        },
    )
    if creada:
        for grupo in {grupo.pk: grupo for grupo in grupos}.values():
            GrupoDeAudiencia.objects.create(audiencia=audiencia, grupo=grupo)
    return audiencia


# Devuelve la audiencia «toda la organización», creándola si no existe.
@transaction.atomic
def audiencia_de_organizacion(organizacion):
    audiencia, _creada = Audiencia.objects.get_or_create(
        huella=f"organizacion:{organizacion.pk}",
        defaults={"tipo": Audiencia.ORGANIZACION, "organizacion": organizacion},
    )
    return audiencia


# Devuelve la audiencia pública (una sola para todo), creándola si no existe.
@transaction.atomic
def audiencia_publica():
    audiencia, _creada = Audiencia.objects.get_or_create(huella="publica", defaults={"tipo": Audiencia.PUBLICA})
    return audiencia


# ── Qué ve cada persona ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Visibles:
    """
    Las audiencias que ve una persona, ya calculadas. Es lo que se guarda en la caché.
    """

    # Ids de las audiencias que ve.
    ids: frozenset = frozenset()
    # Si lo ve todo salvo lo personal de otras personas (el superadmin).
    todo_menos_lo_personal: bool = False


# Versión actual de los cálculos (la crea si no existe).
def _version():
    cache.add(CLAVE_DE_VERSION, 1, None)
    return cache.get(CLAVE_DE_VERSION, 1)


# Clave de la caché del cálculo de una persona.
def _clave(usuario_id):
    return f"audiencias:{usuario_id}:v{_version()}"


# Borra el cálculo de una persona cuando termine bien la transacción. La llaman las señales.
def invalidar_usuario(usuario_id):
    transaction.on_commit(lambda: cache.delete(_clave(usuario_id)))


# Invalida el cálculo de todo el mundo cuando termine bien la transacción. La llaman las señales.
def invalidar_todos():
    transaction.on_commit(_subir_version)


# Sube en uno la versión de los cálculos.
def _subir_version():
    try:
        cache.incr(CLAVE_DE_VERSION)
    except ValueError:  # La clave no existía: con crearla basta.
        cache.set(CLAVE_DE_VERSION, 2, None)


# Devuelve qué audiencias ve una persona, de la caché o calculándolo. Sin sesión, solo la pública.
def visibles_para(usuario):
    if not getattr(usuario, "is_authenticated", False):
        return Visibles(ids=frozenset(Audiencia.objects.filter(tipo=Audiencia.PUBLICA).values_list("id", flat=True)))
    clave = _clave(usuario.pk)
    visibles = cache.get(clave)
    if visibles is None:
        visibles = _calcular(usuario)
        cache.set(clave, visibles, DURACION_EN_CACHE)
    return visibles


# Calcula qué audiencias ve una persona, con 2 consultas: sus grupos (y los que los contienen) con sus
# organizaciones, y las audiencias que le llegan por ellos, por estar en la lista de personas o por ser
# públicas. El superadmin, además, todo lo que no es personal (se resuelve al filtrar).
def _calcular(usuario):
    filas = list(
        Contencion.objects.filter(descendiente__pertenencias__usuario=usuario).values_list(
            "antecesor_id", "antecesor__organizacion_id"
        )
    )
    grupos = {grupo for grupo, _organizacion in filas}
    organizaciones = {organizacion for _grupo, organizacion in filas}
    ids = Audiencia.objects.filter(
        Q(tipo=Audiencia.PUBLICA)
        | Q(tipo=Audiencia.ORGANIZACION, organizacion_id__in=organizaciones)
        | Q(id__in=GrupoDeAudiencia.objects.filter(grupo_id__in=grupos).values("audiencia_id"))
        | Q(id__in=PersonaDeAudiencia.objects.filter(usuario=usuario).values("audiencia_id"))
    ).values_list("id", flat=True)
    return Visibles(ids=frozenset(ids), todo_menos_lo_personal=usuario.is_superuser)


# Filtra una consulta (de proyectos, eventos…) para dejar solo lo que una persona puede ver. Sin
# consultas extra si el cálculo está en la caché.
#   - consulta: el QuerySet.
#   - usuario: quien mira.
#   - campo: nombre del campo que apunta a la audiencia (por defecto, «audiencia»). Vacío si la consulta
#     es de audiencias (para las pantallas de soporte y las pruebas).
def filtrar_visibles(consulta, usuario, campo="audiencia"):
    visibles = visibles_para(usuario)
    propias = Q(**{f"{campo}_id__in" if campo else "id__in": visibles.ids})
    if visibles.todo_menos_lo_personal:
        return consulta.filter(propias | Q(**{f"{campo}__personal" if campo else "personal": False}))
    return consulta.filter(propias)


# Dice si una persona puede ver algo con una audiencia concreta. Sin consultas para quien no es
# superadmin si el cálculo está en la caché.
#   - audiencia: la audiencia (objeto) o su id.
def puede_ver(usuario, audiencia):
    visibles = visibles_para(usuario)
    audiencia_id = getattr(audiencia, "pk", audiencia)
    if audiencia_id in visibles.ids:
        return True
    if not visibles.todo_menos_lo_personal:
        return False
    personal = audiencia.personal if isinstance(audiencia, Audiencia) else Audiencia.objects.get(pk=audiencia_id).personal
    return not personal


# ── Explicar ─────────────────────────────────────────────────────────────────────────────────────────


# Cuántas personas ven una audiencia (sin contar al superadmin). Una consulta. Para las públicas, None.
def cuantas_personas(audiencia):
    if audiencia.tipo == Audiencia.PUBLICA:
        return None
    if audiencia.tipo == Audiencia.PRIVADA:
        return audiencia.personas.count()
    if audiencia.tipo == Audiencia.ORGANIZACION:
        filtro = Q(grupo__organizacion_id=audiencia.organizacion_id)
    else:
        filtro = Q(grupo__ascendencia__antecesor__in=audiencia.grupos.values("grupo_id"))
    return Pertenencia.objects.filter(filtro).values("usuario_id").distinct().count()


# Frase que explica a quién llega una audiencia, para la pantalla en la que se elige: «Lo ven las
# personas de GRU Jarama y de sus subgrupos (12 personas)». El número solo se dice si son 5 o más.
def describir(audiencia):
    if audiencia.tipo == Audiencia.PUBLICA:
        return "Lo ve cualquiera, también sin cuenta (nunca se muestran los alias)."
    if audiencia.tipo == Audiencia.PRIVADA:
        if audiencia.personal:
            return "Solo lo ves tú."
        texto = "Solo lo ven las personas implicadas"
    elif audiencia.tipo == Audiencia.ORGANIZACION:
        texto = f"Lo ven todas las personas de {audiencia.organizacion}"
    else:
        nombres = [str(fila.grupo) for fila in audiencia.grupos.select_related("grupo")]
        lista = nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]
        texto = f"Lo ven las personas de {lista} y de sus subgrupos"
    cuantas = cuantas_personas(audiencia)
    return f"{texto} ({cuantas} personas)." if cuantas >= MINIMO_PARA_CONTAR else f"{texto} (menos de {MINIMO_PARA_CONTAR} personas)."
