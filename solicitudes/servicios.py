"""
Operaciones del módulo «solicitudes» (ver docs/diseno.md, apartado 6): pedir, responder (apoyar o
rechazar), retirar la respuesta, dar el sí de la administración, cancelar, caducar y aceptar. Las
pantallas (solicitudes/views.py) llaman a estas funciones.

Reglas:
- Pueden responder los miembros del grupo (también los de sus subgrupos), menos quien la pide.
- Los apoyos se cuentan; los rechazos, solo como número, y no vetan.
- Si el tipo lo pide, hace falta además el sí de la administración (un admin con su permiso en el grupo).
- Si el tipo lo permite, el sí del superadmin basta por sí solo.
- Al tener todo lo necesario, se acepta y el módulo del tipo crea lo pedido. Si llega la fecha sin
  tenerlo, caduca.
"""

from datetime import timedelta

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.module_loading import import_string

from base.registro import registro
from eventos_sw.servicios import emitir
from grupos.servicios import grupos_de
from permisos.servicios import permisos_de, puede

from .models import AjusteDeSolicitud, Apoyo, Solicitud

# Cuánto se guarda en la caché el número de solicitudes pendientes de cada persona (un día).
DURACION_EN_CACHE = 60 * 60 * 24


# ── Ajustes ──────────────────────────────────────────────────────────────────────────────────────────


# Apoyos y días de un tipo de solicitud en una organización: los de la organización, si los ha
# ajustado; si no, los de la plataforma; si no, los del contrato. Devuelve (apoyos, días). Una consulta.
#   - tipo: el TipoDeSolicitud.
#   - organizacion_id: la organización del grupo.
def ajuste_para(tipo, organizacion_id):
    ajustes = {a.organizacion_id: a for a in AjusteDeSolicitud.objects.filter(tipo=tipo.codigo).filter(Q(organizacion_id=organizacion_id) | Q(organizacion__isnull=True))}
    ajuste = ajustes.get(organizacion_id) or ajustes.get(None)
    return (ajuste.apoyos, ajuste.dias) if ajuste else (tipo.apoyos, tipo.dias)


# Guarda los apoyos y días de un tipo de solicitud en una organización (o en la plataforma, con None).
@transaction.atomic
def ajustar(tipo, organizacion_id, apoyos, dias):
    AjusteDeSolicitud.objects.update_or_create(organizacion_id=organizacion_id, tipo=tipo, defaults={"apoyos": apoyos, "dias": dias})


# ── Pedir y responder ────────────────────────────────────────────────────────────────────────────────


# Pide algo a un grupo. Devuelve la solicitud. Avisa con «solicitudes.pedida».
#   - usuario: quien pide.
#   - codigo: código del tipo de solicitud.
#   - grupo: el grupo al que se pide.
#   - descripcion, justificacion: qué y por qué.
#   - datos: lo que necesita el módulo del tipo para crear lo pedido.
@transaction.atomic
def pedir(usuario, codigo, grupo, descripcion, justificacion="", datos=None):
    tipo = registro.solicitudes.get(codigo)
    if tipo is None:
        raise ValidationError(f"No existe el tipo de solicitud «{codigo}».")
    if tipo.solo_miembros and grupo.pk not in grupos_de(usuario):
        raise ValidationError(f"Solo los miembros de {grupo} pueden pedirle esto.")
    if tipo.comprobar:
        import_string(tipo.comprobar)(usuario, grupo)
    if Solicitud.objects.filter(tipo=codigo, grupo=grupo, solicitante=usuario, estado=Solicitud.PENDIENTE).exists():
        raise ValidationError(f"Ya tienes una solicitud pendiente de este tipo en {grupo}.")
    apoyos, dias = ajuste_para(tipo, grupo.organizacion_id)
    solicitud = Solicitud.objects.create(
        tipo=codigo, grupo=grupo, solicitante=usuario, descripcion=descripcion, justificacion=justificacion, datos=datos or {},
        apoyos_necesarios=apoyos, necesita_aprobacion=bool(tipo.aprobacion), caduca_el=timezone.localdate() + timedelta(days=dias),
    )
    emitir("solicitudes.pedida", solicitud_id=solicitud.pk)
    _invalidar()
    return solicitud


# Dice si una persona puede apoyar o rechazar una solicitud: es miembro del grupo (también si lo es de
# un subgrupo) y no la ha pedido ella. Sin consultas si se le pasan sus grupos.
#   - mios: los ids de sus grupos (grupos_de), para no volver a calcularlos.
def puede_responder(usuario, solicitud, mios=None):
    mios = grupos_de(usuario) if mios is None else mios
    return solicitud.solicitante_id != usuario.pk and solicitud.grupo_id in mios


# Dice si una persona puede dar el sí de la administración: el tipo lo pide y tiene el permiso en el
# grupo (o es superadmin).
def puede_aprobar(usuario, solicitud):
    tipo = registro.solicitudes.get(solicitud.tipo)
    return bool(tipo and tipo.aprobacion) and puede(usuario, tipo.aprobacion, grupo=solicitud.grupo_id)


# Apoya o rechaza una solicitud pendiente (o cambia la respuesta). Si con eso tiene todo lo necesario,
# se acepta.
#   - acepta: True para apoyarla, False para rechazarla.
@transaction.atomic
def responder(solicitud, usuario, acepta):
    solicitud = _bloquear(solicitud)
    if not puede_responder(usuario, solicitud):
        raise ValidationError(f"Solo responden los miembros de {solicitud.grupo}, y no quien la pide.")
    Apoyo.objects.update_or_create(solicitud=solicitud, usuario=usuario, defaults={"acepta": acepta, "creado": timezone.now()})
    _recontar(solicitud)
    _aceptar_si_completa(solicitud)
    _invalidar()


# Retira la respuesta de una persona a una solicitud pendiente.
@transaction.atomic
def retirar_respuesta(solicitud, usuario):
    solicitud = _bloquear(solicitud)
    Apoyo.objects.filter(solicitud=solicitud, usuario=usuario).delete()
    _recontar(solicitud)
    _invalidar()


# Da el sí de la administración. Si es el superadmin y el tipo lo permite, se acepta en el acto; si no,
# se acepta cuando además tenga los apoyos.
@transaction.atomic
def aprobar(solicitud, usuario):
    solicitud = _bloquear(solicitud)
    tipo = registro.solicitudes[solicitud.tipo]
    if usuario.is_superuser and tipo.basta_el_superadmin:
        solicitud.aprobada_por = usuario
        solicitud.por_el_superadmin = True
        _aceptar(solicitud)
    elif puede_aprobar(usuario, solicitud):
        solicitud.aprobada_por = usuario
        solicitud.save(update_fields=["aprobada_por"])
        _aceptar_si_completa(solicitud)
    else:
        raise ValidationError("No puedes dar el sí de la administración a esta solicitud.")
    _invalidar()


# Cancela una solicitud pendiente. Solo quien la pidió.
@transaction.atomic
def cancelar(solicitud, usuario):
    solicitud = _bloquear(solicitud)
    if solicitud.solicitante_id != usuario.pk:
        raise ValidationError("Solo quien la pidió puede cancelarla.")
    _cerrar(solicitud, Solicitud.CANCELADA)
    _invalidar()


# Caduca las solicitudes pendientes cuya fecha ya ha pasado sin tener lo necesario. Lo llaman las
# pantallas de solicitudes y la orden «caducar_solicitudes». Devuelve cuántas.
@transaction.atomic
def caducar_vencidas():
    vencidas = list(Solicitud.objects.select_for_update(skip_locked=True).filter(estado=Solicitud.PENDIENTE, caduca_el__lt=timezone.localdate()))
    for solicitud in vencidas:
        _cerrar(solicitud, Solicitud.CADUCADA)
        emitir("solicitudes.caducada", solicitud_id=solicitud.pk)
    if vencidas:
        _invalidar()
    return len(vencidas)


# ── Por dentro ───────────────────────────────────────────────────────────────────────────────────────


# Vuelve a leer la solicitud bloqueando su fila (para que dos respuestas a la vez no se pisen) y
# comprueba que sigue pendiente.
def _bloquear(solicitud):
    solicitud = Solicitud.objects.select_for_update().select_related("grupo__organizacion").get(pk=solicitud.pk)
    if solicitud.estado != Solicitud.PENDIENTE:
        raise ValidationError(f"La solicitud ya está {solicitud.get_estado_display().lower()}.")
    return solicitud


# Cuenta los apoyos y los rechazos y los guarda en la solicitud. Una consulta y una escritura.
def _recontar(solicitud):
    cuentas = solicitud.respuestas.aggregate(apoyos=Count("pk", filter=Q(acepta=True)), rechazos=Count("pk", filter=Q(acepta=False)))
    solicitud.apoyos, solicitud.rechazos = cuentas["apoyos"], cuentas["rechazos"]
    solicitud.save(update_fields=["apoyos", "rechazos"])


# Acepta la solicitud si ya tiene todo lo necesario.
def _aceptar_si_completa(solicitud):
    if solicitud.completa:
        _aceptar(solicitud)


# Acepta la solicitud: el módulo del tipo crea lo pedido (y se guarda qué creó) y se avisa.
def _aceptar(solicitud):
    tipo = registro.solicitudes[solicitud.tipo]
    ancla = import_string(tipo.resolver)(solicitud)
    if ancla:
        solicitud.ancla_tipo, solicitud.ancla_id = ancla
    _cerrar(solicitud, Solicitud.ACEPTADA)
    emitir("solicitudes.aceptada", solicitud_id=solicitud.pk)


# Pasa la solicitud a un estado final, con la hora.
def _cerrar(solicitud, estado):
    solicitud.estado = estado
    solicitud.resuelta_el = timezone.now()
    solicitud.save()


# ── Número del menú ──────────────────────────────────────────────────────────────────────────────────


# Consulta de las solicitudes que una persona puede ver: las de sus grupos (también los que contienen a
# los suyos), las de los grupos donde puede dar el sí de la administración y las suyas. El superadmin,
# todas. Sin ejecutar.
#   - usuario: quién.
#   - mios: sus grupos (grupos_de), si ya se han calculado.
def visibles_para(usuario, mios=None):
    consulta = Solicitud.objects.all()
    if usuario.is_superuser:
        return consulta
    mios = grupos_de(usuario) if mios is None else mios
    return consulta.filter(Q(grupo_id__in=mios) | Q(grupo_id__in=grupos_donde_aprueba(usuario)) | Q(solicitante=usuario))


# Ids de los grupos donde una persona puede dar el sí de la administración a algún tipo de solicitud,
# sacados de su cálculo de permisos (sin consultas si está en la caché).
def grupos_donde_aprueba(usuario):
    permisos = {tipo.aprobacion for tipo in registro.solicitudes.values() if tipo.aprobacion}
    return {grupo for grupo, codigos in permisos_de(usuario).grupos.items() if codigos & permisos}


# «Solicitudes (N)»: las pendientes a las que la persona aún no ha respondido y puede responder, más las
# que esperan su sí de la administración (el superadmin: todas las que esperan el sí). Sin consultas si
# está en la caché.
#   - usuario: quién.
def pendientes_para(usuario):
    clave = f"solicitudes:pendientes:v{_version()}:{usuario.pk}"
    numero = cache.get(clave)
    if numero is None:
        respondidas = Apoyo.objects.filter(usuario=usuario).values("solicitud_id")
        pendientes = Solicitud.objects.filter(estado=Solicitud.PENDIENTE).exclude(solicitante=usuario)
        responder = Q(grupo_id__in=grupos_de(usuario)) & ~Q(pk__in=respondidas)
        if usuario.is_superuser:
            aprobar = Q(necesita_aprobacion=True, aprobada_por__isnull=True)
        else:
            aprobar = Q(necesita_aprobacion=True, aprobada_por__isnull=True, grupo_id__in=grupos_donde_aprueba(usuario))
        numero = pendientes.filter(responder | aprobar).count()
        cache.set(clave, numero, DURACION_EN_CACHE)
    return numero


# Versión de los números del menú (sube con cualquier cambio en las solicitudes).
def _version():
    cache.add("solicitudes:version", 1, None)
    return cache.get("solicitudes:version", 1)


# Sube la versión cuando termine bien la transacción en curso.
def _invalidar():
    # Función interna: sube el número (o lo crea si la caché estaba vacía).
    def subir():
        try:
            cache.incr("solicitudes:version")
        except ValueError:
            cache.set("solicitudes:version", 2, None)

    transaction.on_commit(subir)
