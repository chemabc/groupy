"""
Notificaciones del módulo «grupos»: a quién se avisa y qué se le dice cuando pasa algo. Cada función
recibe los datos de un eventos_sw y devuelve una lista de AvisoPreparado. Las declara el contrato
(grupos/apps.py, «avisos») y las llama el repartidor de «comunicaciones», desde la bandeja de eventos_sw,
así que se ejecutan unos segundos después del cambio: por eso vuelven a leer de la base lo que necesitan
(si ya no existe, no se avisa).
"""

from django.urls import reverse

from base.contrato import AvisoPreparado
from base.registro import registro

from .models import AdminDeOrganizacion, Grupo, InvitacionDeGrupo, Organizacion, Pertenencia


# Nombres de los roles por su código, sin importar «permisos» (que importa este módulo).
def _nombre_del_rol(codigo):
    from permisos.models import Rol

    return Rol.objects.filter(codigo=codigo).values_list("nombre", flat=True).first() or codigo


# «Te han admitido en GRU Henares (ORG Tajo).» A la persona admitida.
def admitido(usuario_id, grupo_id, rol, **resto):
    grupo = Grupo.objects.select_related("organizacion").filter(pk=grupo_id).first()
    if grupo is None:
        return []
    como = "" if rol == Pertenencia.USUARIO else f" como «{_nombre_del_rol(rol)}»"
    texto = f"Te han admitido en {grupo} ({grupo.organizacion}){como}."
    return [AvisoPreparado((usuario_id,), texto, reverse("grupos:grupo", args=[grupo.pk]))]


# «Ahora eres «Admin del grupo» en GRU Henares.» A la persona cuyo rol cambia.
def rol_cambiado(usuario_id, grupo_id, rol, **resto):
    grupo = Grupo.objects.select_related("organizacion").filter(pk=grupo_id).first()
    if grupo is None:
        return []
    texto = f"Ahora tu rol en {grupo} ({grupo.organizacion}) es «{_nombre_del_rol(rol)}»."
    return [AvisoPreparado((usuario_id,), texto, reverse("grupos:grupo", args=[grupo.pk]))]


# «Te han nombrado admin de ORG Tajo.» A la persona nombrada.
def admin_de_organizacion(usuario_id, organizacion_id, **resto):
    organizacion = Organizacion.objects.filter(pk=organizacion_id).first()
    if organizacion is None:
        return []
    texto = f"Te han nombrado admin de {organizacion}."
    return [AvisoPreparado((usuario_id,), texto, reverse("grupos:organizacion", args=[organizacion.pk]))]


# «GRU Henares (ORG Tajo) invita a GRU Segre a Un proyecto n.º 7.» A los admins del grupo invitado y de
# su organización (quienes pueden responder), solo si sigue pendiente.
def invitacion_recibida(invitacion_id, **resto):
    invitacion = _invitacion(invitacion_id)
    if invitacion is None or invitacion.estado != InvitacionDeGrupo.PENDIENTE:
        return []
    invitado = invitacion.grupo_invitado
    admins = set(Pertenencia.objects.filter(grupo=invitado, rol=Pertenencia.ADMIN_GRUPO).values_list("usuario_id", flat=True))
    admins |= set(AdminDeOrganizacion.objects.filter(organizacion_id=invitado.organizacion_id).values_list("usuario_id", flat=True))
    texto = (
        f"{invitacion.grupo_que_invita} ({invitacion.grupo_que_invita.organizacion}) invita a {invitado} a "
        f"{_que(invitacion)}. Puedes aceptarla o rechazarla."
    )
    return [AvisoPreparado(tuple(sorted(admins)), texto, reverse("grupos:invitaciones"))]


# «GRU Segre (ORG Ebro) ha aceptado la invitación de GRU Henares a…» A quien invitó y a los admins del
# grupo que invitó.
def invitacion_respondida(invitacion_id, **resto):
    invitacion = _invitacion(invitacion_id)
    if invitacion is None or invitacion.estado not in (InvitacionDeGrupo.ACEPTADA, InvitacionDeGrupo.RECHAZADA):
        return []
    que_invita = invitacion.grupo_que_invita
    personas = set(Pertenencia.objects.filter(grupo=que_invita, rol=Pertenencia.ADMIN_GRUPO).values_list("usuario_id", flat=True))
    if invitacion.invitada_por_id:
        personas.add(invitacion.invitada_por_id)
    verbo = "ha aceptado" if invitacion.estado == InvitacionDeGrupo.ACEPTADA else "ha rechazado"
    texto = (
        f"{invitacion.grupo_invitado} ({invitacion.grupo_invitado.organizacion}) {verbo} la invitación de "
        f"{que_invita} a {_que(invitacion)}."
    )
    return [AvisoPreparado(tuple(sorted(personas)), texto, reverse("grupos:invitaciones"))]


# La invitación con sus grupos y organizaciones, o None si ya no existe.
def _invitacion(invitacion_id):
    return (
        InvitacionDeGrupo.objects.select_related("grupo_que_invita__organizacion", "grupo_invitado__organizacion")
        .filter(pk=invitacion_id)
        .first()
    )


# Qué se comparte, en palabras: «Un proyecto de mentira n.º 7».
def _que(invitacion):
    ancla = registro.anclas.get(invitacion.ancla_tipo)
    return f"{ancla.descripcion.lower() if ancla else invitacion.ancla_tipo} n.º {invitacion.ancla_id}"
