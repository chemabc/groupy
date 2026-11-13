"""
Notificaciones del módulo «lugares» (las reparte «comunicaciones»; ver lugares/apps.py).
"""

from django.contrib.auth import get_user_model
from django.urls import reverse

from base.contrato import AvisoPreparado

from .models import LugarDePersona, PropuestaDeLugar


# «Nutria propone un lugar nuevo: IES Cervantes.» A los superadmins, si sigue pendiente.
def propuesta(propuesta_id, **resto):
    propuesta = PropuestaDeLugar.objects.select_related("propuesta_por", "lugar").filter(pk=propuesta_id).first()
    if propuesta is None or propuesta.estado != PropuestaDeLugar.PENDIENTE:
        return []
    superadmins = tuple(get_user_model().objects.filter(es_superadmin=True, activo=True).values_list("pk", flat=True))
    que = f"un cambio en {propuesta.lugar}" if propuesta.lugar_id else f"un lugar nuevo: {propuesta.nombre}"
    return [AvisoPreparado(superadmins, f"{propuesta.propuesta_por} propone {que}.", reverse("lugares:propuestas"))]


# «Se ha aceptado (o rechazado) tu propuesta…» A quien la propuso.
def propuesta_revisada(propuesta_id, **resto):
    propuesta = PropuestaDeLugar.objects.select_related("lugar").filter(pk=propuesta_id).first()
    if propuesta is None:
        return []
    que = f"de cambio en {propuesta.lugar}" if propuesta.lugar_id else f"del lugar «{propuesta.nombre}»"
    estado = "aceptado" if propuesta.estado == PropuestaDeLugar.ACEPTADA else "rechazado"
    texto = f"Se ha {estado} tu propuesta {que}." + (f" Respuesta: {propuesta.respuesta}" if propuesta.respuesta else "")
    return [AvisoPreparado((propuesta.propuesta_por_id,), texto, reverse("lugares:mi_lugar"))]


# «Aún no has elegido tu lugar de trabajo.» A todas las personas activas sin lugar.
def recordatorio(**resto):
    con_lugar = LugarDePersona.objects.values("usuario_id")
    personas = tuple(get_user_model().objects.filter(activo=True).exclude(pk__in=con_lugar).values_list("pk", flat=True))
    texto = "Aún no has elegido tu lugar de trabajo. Elígelo de la lista o propón uno nuevo."
    return [AvisoPreparado(personas, texto, reverse("lugares:mi_lugar"))]
