"""
Operaciones del módulo «decisiones»: registrar las que llegan de otros módulos, ver las que tocan a cada
persona y marcar una como sustituida por otra.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.dateparse import parse_datetime

from audiencias.servicios import filtrar_visibles
from permisos.servicios import puede

from .models import Decision


# Registra una decisión. La llaman los eventos_sw «documentos.acuerdo_tomado», «debates.cerrado» y
# «consultas.cerrada» (ver decisiones/apps.py), que traen todos estos datos. Si ya existía una decisión
# con el mismo origen y el mismo texto, no la repite. Devuelve la decisión.
#   - texto, forma, detalle: qué, cómo (Decision.FORMAS) y su recuento.
#   - grupo_id, audiencia_id: el grupo que decide y quién puede verla (la audiencia de su origen).
#   - origen_tipo, origen_id, enlace: de dónde sale y la dirección para verlo.
#   - tomada: cuándo, como texto ISO (opcional; si no, ahora).
def registrar(texto, forma, grupo_id, audiencia_id, origen_tipo, origen_id, enlace="", detalle="", tomada=None, **_otros):
    existente = Decision.objects.filter(origen_tipo=origen_tipo, origen_id=origen_id, texto=texto).first()
    if existente:
        return existente
    datos = dict(
        texto=texto, forma=forma, detalle=detalle[:200], grupo_id=grupo_id, audiencia_id=audiencia_id,
        origen_tipo=origen_tipo, origen_id=origen_id, enlace=enlace,
    )
    if tomada:
        datos["tomada"] = parse_datetime(tomada)
    return Decision.objects.create(**datos)


# Consulta (sin ejecutar) de las decisiones que ve una persona: las de las audiencias en las que está
# (quien podía participar en su origen).
#   - vigentes: si solo las que no se han sustituido.
def visibles(usuario, vigentes=True):
    consulta = filtrar_visibles(Decision.objects.all(), usuario)
    return consulta.filter(sustituida_por__isnull=True) if vigentes else consulta


# Marca una decisión como sustituida por otra más nueva del mismo grupo (o la vuelve a dejar vigente,
# con «nueva» vacía). Hace falta «decisiones.sustituir» en su grupo.
#   - usuario: quien lo hace.
#   - decision: la antigua.
#   - nueva: la que la sustituye, o None.
@transaction.atomic
def sustituir(usuario, decision, nueva):
    if not puede(usuario, "decisiones.sustituir", grupo=decision.grupo_id):
        raise ValidationError("Solo la administración del grupo puede marcar una decisión como sustituida.")
    if nueva is not None and (nueva.pk == decision.pk or nueva.grupo_id != decision.grupo_id or nueva.tomada < decision.tomada):
        raise ValidationError("Solo la sustituye una decisión más nueva del mismo grupo.")
    decision.sustituida_por = nueva
    decision.save(update_fields=["sustituida_por"])
