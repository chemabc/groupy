"""
Notificaciones del módulo «proyectos» (las reparte «comunicaciones»; ver proyectos/apps.py).
"""

from django.urls import reverse

from base.contrato import AvisoPreparado

from .models import Tarea


# «Lince te ha encargado «Pedir presupuesto» (Huerto del barrio).» A la persona responsable.
def tarea_asignada(tarea_id, **resto):
    tarea = Tarea.objects.select_related("creador", "proyecto").filter(pk=tarea_id).first()
    if tarea is None:
        return []
    donde = f" ({tarea.proyecto.titulo})" if tarea.proyecto else ""
    quien = tarea.creador.alias if tarea.creador else "Alguien"
    texto = f"{quien} te ha encargado «{tarea.titulo}»{donde}."
    return [AvisoPreparado((tarea.responsable_id,), texto, reverse("proyectos:tarea", args=[tarea.pk]))]
