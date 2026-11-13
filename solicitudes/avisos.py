"""
Notificaciones del módulo «solicitudes» (las reparte «comunicaciones»; ver su contrato en
solicitudes/apps.py). Se preparan unos segundos después del cambio, así que releen la solicitud.
"""

from django.urls import reverse

from base.contrato import AvisoPreparado
from base.registro import registro
from grupos.models import AdminDeOrganizacion, Pertenencia

from .models import Solicitud


# La solicitud con su grupo y su organización, o None si ya no existe.
def _solicitud(solicitud_id):
    return Solicitud.objects.select_related("grupo__organizacion", "solicitante").filter(pk=solicitud_id).first()


# Nombre del tipo de una solicitud («Entrar en un grupo»).
def _nombre(solicitud):
    tipo = registro.solicitudes.get(solicitud.tipo)
    return tipo.nombre if tipo else solicitud.tipo


# «Lince pide: Entrar en un grupo (GRU Henares). Necesita el sí de la administración.» A los admins del
# grupo y de su organización, si el tipo necesita su sí.
def pedida(solicitud_id, **resto):
    solicitud = _solicitud(solicitud_id)
    if solicitud is None or not solicitud.necesita_aprobacion or solicitud.estado != Solicitud.PENDIENTE:
        return []
    admins = set(Pertenencia.objects.filter(grupo=solicitud.grupo, rol=Pertenencia.ADMIN_GRUPO).values_list("usuario_id", flat=True))
    admins |= set(AdminDeOrganizacion.objects.filter(organizacion_id=solicitud.grupo.organizacion_id).values_list("usuario_id", flat=True))
    admins.discard(solicitud.solicitante_id)
    texto = f"{solicitud.solicitante} pide: {_nombre(solicitud)} ({solicitud.grupo}). Necesita el sí de la administración."
    return [AvisoPreparado(tuple(sorted(admins)), texto, reverse("solicitudes:solicitud", args=[solicitud.pk]))]


# «Tu solicitud «Entrar en un grupo» a GRU Henares se ha aceptado.» A quien la pidió.
def aceptada(solicitud_id, **resto):
    solicitud = _solicitud(solicitud_id)
    if solicitud is None:
        return []
    texto = f"Se ha aceptado tu solicitud «{_nombre(solicitud)}» a {solicitud.grupo} ({solicitud.grupo.organizacion})."
    return [AvisoPreparado((solicitud.solicitante_id,), texto, reverse("solicitudes:solicitud", args=[solicitud.pk]))]


# «Tu solicitud … ha caducado sin los apoyos necesarios.» A quien la pidió.
def caducada(solicitud_id, **resto):
    solicitud = _solicitud(solicitud_id)
    if solicitud is None:
        return []
    texto = (
        f"Ha caducado tu solicitud «{_nombre(solicitud)}» a {solicitud.grupo}: tenía {solicitud.apoyos} de "
        f"{solicitud.apoyos_necesarios} apoyos."
    )
    return [AvisoPreparado((solicitud.solicitante_id,), texto, reverse("solicitudes:solicitud", args=[solicitud.pk]))]
