"""
Operaciones del módulo «grupos». Las pantallas (y más adelante la API) llaman a estas funciones en lugar
de tocar las tablas directamente, para que siempre se compruebe lo mismo y se avise con eventos_sw.

Todas trabajan dentro de una transacción: o se hace todo, o nada.

Quién puede hacer cada cosa lo decidirá el módulo «permisos» (pieza siguiente). De momento, solo
responder a una invitación comprueba quién lo hace, porque está acordado: el admin del grupo invitado
(o el superadmin).
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from base.registro import registro
from eventos_sw.servicios import emitir

from .models import AdminDeOrganizacion, Contencion, Grupo, InvitacionDeGrupo, Organizacion, Pertenencia


# Crea una organización con su primer grupo, porque toda organización tiene al menos uno. Devuelve la
# organización y el grupo.
#   - nombre: nombre de la organización.
#   - nombre_del_primer_grupo: nombre de su primer grupo.
#   - descripcion: qué es la organización (opcional).
@transaction.atomic
def crear_organizacion(nombre, nombre_del_primer_grupo, descripcion=""):
    organizacion = Organizacion(nombre=nombre, descripcion=descripcion)
    organizacion.full_clean()
    organizacion.save()
    grupo = crear_grupo(organizacion, nombre_del_primer_grupo)
    return organizacion, grupo


# Crea un grupo, dentro de otro o como grupo principal de su organización. Devuelve el grupo.
#   - organizacion: la organización del grupo.
#   - nombre: nombre del grupo.
#   - padre: grupo que lo contiene (de la misma organización), o None.
#   - otros: más campos del grupo (descripcion, ambito).
@transaction.atomic
def crear_grupo(organizacion, nombre, padre=None, **otros):
    grupo = Grupo(organizacion=organizacion, nombre=nombre, padre=padre, **otros)
    grupo.full_clean()
    grupo.save()
    return grupo


# Mete a un usuario en un grupo. Devuelve su pertenencia.
#   - usuario: quién entra.
#   - grupo: en qué grupo.
#   - rol: Pertenencia.USUARIO o Pertenencia.ADMIN_GRUPO.
#   - es_base: si este grupo pasa a ser su asamblea base (solo si aún no tiene otra).
@transaction.atomic
def admitir(usuario, grupo, rol=Pertenencia.USUARIO, es_base=False):
    pertenencia = Pertenencia(usuario=usuario, grupo=grupo, rol=rol, es_base=es_base)
    pertenencia.full_clean()
    pertenencia.save()
    emitir("grupos.pertenencias_cambiadas", usuario_id=usuario.pk)
    return pertenencia


# Saca a un usuario de un grupo. Si con eso ya no está en ningún grupo de la organización, deja también
# de ser admin de ella (nadie pertenece a una organización sin estar en uno de sus grupos).
#   - usuario: quién sale.
#   - grupo: de qué grupo.
@transaction.atomic
def sacar(usuario, grupo):
    Pertenencia.objects.filter(usuario=usuario, grupo=grupo).delete()
    sigue_dentro = Pertenencia.objects.filter(usuario=usuario, grupo__organizacion_id=grupo.organizacion_id).exists()
    if not sigue_dentro:
        AdminDeOrganizacion.objects.filter(usuario=usuario, organizacion_id=grupo.organizacion_id).delete()
    emitir("grupos.pertenencias_cambiadas", usuario_id=usuario.pk)


# Cambia el rol de una persona en un grupo y apunta desde qué día lo tiene.
#   - pertenencia: la pertenencia que cambia.
#   - rol: el rol nuevo.
@transaction.atomic
def cambiar_rol(pertenencia, rol):
    pertenencia.rol = rol
    pertenencia.rol_desde = timezone.localdate()
    pertenencia.full_clean()
    pertenencia.save()
    emitir("grupos.pertenencias_cambiadas", usuario_id=pertenencia.usuario_id)


# Hace de un grupo la asamblea base de una persona (que ya debe estar en él), y la anterior deja de
# serlo.
#   - usuario: de quién.
#   - grupo: su nueva asamblea base.
@transaction.atomic
def cambiar_asamblea_base(usuario, grupo):
    pertenencia = Pertenencia.objects.filter(usuario=usuario, grupo=grupo).first()
    if pertenencia is None:
        raise ValidationError("Solo puede ser asamblea base un grupo en el que la persona ya está.")
    Pertenencia.objects.filter(usuario=usuario, es_base=True).update(es_base=False)
    pertenencia.es_base = True
    pertenencia.save(update_fields=["es_base"])
    emitir("grupos.pertenencias_cambiadas", usuario_id=usuario.pk)


# Nombra a una persona admin de una organización. Debe estar en alguno de sus grupos.
#   - usuario: a quién.
#   - organizacion: de qué organización.
@transaction.atomic
def nombrar_admin_de_organizacion(usuario, organizacion):
    nombramiento = AdminDeOrganizacion(usuario=usuario, organizacion=organizacion)
    nombramiento.full_clean()
    nombramiento.save()
    emitir("grupos.pertenencias_cambiadas", usuario_id=usuario.pk)
    return nombramiento


# Devuelve los ids de los grupos de los que una persona es miembro: aquellos en los que está y todos los
# que los contienen (la pertenencia se hereda hacia arriba). Una sola consulta. Lo usarán «permisos» y
# «audiencias».
#   - usuario: de quién.
def grupos_de(usuario):
    return set(
        Contencion.objects.filter(descendiente__pertenencias__usuario=usuario).values_list("antecesor_id", flat=True)
    )


# Invita a un grupo de otra organización a algo concreto (por ejemplo, un proyecto conjunto). Devuelve
# la invitación. Avisa con «grupos.invitacion_creada».
#   - ancla_tipo: tipo de lo invitado, declarado como ancla en algún contrato («proyectos.proyecto»).
#   - ancla_id: número de lo invitado.
#   - grupo_que_invita: grupo que invita; quien invita debe ser miembro de él.
#   - grupo_invitado: grupo de otra organización.
#   - invitada_por: el usuario que invita.
#   - mensaje: explicación para el grupo invitado.
@transaction.atomic
def invitar(ancla_tipo, ancla_id, grupo_que_invita, grupo_invitado, invitada_por, mensaje=""):
    if ancla_tipo not in registro.anclas:
        raise ValidationError(f"No se puede invitar a «{ancla_tipo}»: ningún módulo lo declara como ancla.")
    if grupo_que_invita.organizacion_id == grupo_invitado.organizacion_id:
        raise ValidationError(
            "Solo se invita a grupos de otra organización; dentro de la misma basta con elegir a quién llega."
        )
    if grupo_que_invita.pk not in grupos_de(invitada_por):
        raise ValidationError(f"Para invitar en nombre de «{grupo_que_invita}» hay que ser miembro de ese grupo.")
    invitacion = InvitacionDeGrupo(
        ancla_tipo=ancla_tipo,
        ancla_id=ancla_id,
        grupo_que_invita=grupo_que_invita,
        grupo_invitado=grupo_invitado,
        invitada_por=invitada_por,
        mensaje=mensaje,
    )
    invitacion.full_clean()
    invitacion.save()
    emitir("grupos.invitacion_creada", **invitacion.datos_del_aviso())
    return invitacion


# Acepta o rechaza una invitación pendiente. Solo puede hacerlo el admin del grupo invitado (o el
# superadmin). Avisa con «grupos.invitacion_aceptada» o «grupos.invitacion_rechazada»; quien lleve lo
# invitado (por ejemplo, «proyectos») escucha el aviso y abre el proyecto al grupo.
#   - invitacion: la invitación.
#   - usuario: quién responde.
#   - acepta: True para aceptar, False para rechazar.
@transaction.atomic
def responder_invitacion(invitacion, usuario, acepta):
    es_admin = Pertenencia.objects.filter(
        usuario=usuario, grupo_id=invitacion.grupo_invitado_id, rol=Pertenencia.ADMIN_GRUPO
    ).exists()
    if not (es_admin or usuario.is_superuser):
        raise ValidationError(
            f"Solo el admin de «{invitacion.grupo_invitado}» (o el superadmin) puede responder a esta invitación."
        )
    _cerrar(invitacion, usuario, InvitacionDeGrupo.ACEPTADA if acepta else InvitacionDeGrupo.RECHAZADA)
    emitir(f"grupos.invitacion_{invitacion.estado}", **invitacion.datos_del_aviso())


# Retira una invitación pendiente. Puede hacerlo cualquier miembro del grupo que invitó.
#   - invitacion: la invitación.
#   - usuario: quién la retira.
@transaction.atomic
def retirar_invitacion(invitacion, usuario):
    if invitacion.grupo_que_invita_id not in grupos_de(usuario):
        raise ValidationError(f"Solo los miembros de «{invitacion.grupo_que_invita}» pueden retirar la invitación.")
    _cerrar(invitacion, usuario, InvitacionDeGrupo.RETIRADA)
    emitir("grupos.invitacion_retirada", **invitacion.datos_del_aviso())


# Pasa una invitación pendiente a su estado final, apuntando quién y qué día. La usan
# responder_invitacion y retirar_invitacion.
def _cerrar(invitacion, usuario, estado):
    if invitacion.estado != InvitacionDeGrupo.PENDIENTE:
        raise ValidationError(f"La invitación ya está {invitacion.get_estado_display().lower()}.")
    invitacion.estado = estado
    invitacion.respondida_por = usuario
    invitacion.respondida_el = timezone.localdate()
    invitacion.save()
