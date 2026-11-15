"""
Decisiones y datos de ejemplo. «decisiones» no crea ejemplos propios (llegan solas del acta de ejemplo de
«documentos»), pero al borrar los ejemplos quita las de las organizaciones de ejemplo: si no, protegerían
sus grupos y no se podrían borrar.
"""

from grupos.ejemplos import organizaciones_de_ejemplo

from .models import Decision


# Borra las decisiones de los grupos de las organizaciones de ejemplo (primero las que sustituyen a otras).
def borrar():
    decisiones = Decision.objects.filter(grupo__organizacion__in=organizaciones_de_ejemplo())
    decisiones.update(sustituida_por=None)
    decisiones.delete()
