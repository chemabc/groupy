"""
Etiqueta de plantilla {% colgantes %}: pinta en la ficha de un elemento (un evento, un proyecto…) el
recuadro «Cuelga de aquí» con lo que otros módulos han colgado de él (sus debates, sus actas, sus
consultas) y los enlaces para crear uno nuevo. Ver Colgante en base/contrato.py.

Se usa así, en la plantilla de la ficha:
    {% load colgantes %}
    {% colgantes "eventos.evento" evento.pk %}
La ficha no importa esos módulos: la etiqueta pregunta al registro qué colgantes aceptan ese tipo de ancla
y llama a su función. Cuesta las consultas de cada colgante (normalmente, una cada uno).
"""

from django import template
from django.urls import reverse
from django.utils.module_loading import import_string

from base.registro import registro

register = template.Library()


# Junta lo que cuelga de un elemento, por colgante, y lo pinta con «base/colgantes.html». No pinta nada si
# ningún módulo puede colgar de ese tipo de ancla.
#   - context: el de la plantilla (de él sale quien mira, request.user). Django exige este nombre.
#   - ancla_tipo: el tipo del elemento («eventos.evento»).
#   - ancla_id: su número.
@register.inclusion_tag("base/colgantes.html", takes_context=True)
def colgantes(context, ancla_tipo, ancla_id):
    usuario = context["request"].user
    grupos = []
    for colgante in registro.colgantes.values():
        if ancla_tipo not in colgante.anclas:
            continue
        filas = import_string(colgante.funcion)(usuario, ancla_tipo, ancla_id)
        crear = f"{reverse(colgante.crear)}?ancla={ancla_tipo}:{ancla_id}" if colgante.crear else ""
        grupos.append({"colgante": colgante, "filas": filas, "crear": crear})
    return {"grupos": grupos}
