"""
Eventos y datos de ejemplo. «eventos» no crea ejemplos propios, pero al borrar los de los demás módulos
(«python manage.py ejemplos borrar») quita antes los eventos y las series que se hayan convocado al probar
en las organizaciones de ejemplo: si no, protegerían sus tipologías y sus grupos y no se podrían borrar.
"""

from grupos.ejemplos import organizaciones_de_ejemplo

from .models import Evento, Serie


# Borra los eventos y las series de los grupos de las organizaciones de ejemplo (con sus respuestas a
# «¿Vas a ir?» y sus cometidos, que van con ellos).
def borrar():
    organizaciones = organizaciones_de_ejemplo()
    Evento.objects.filter(grupo__organizacion__in=organizaciones).delete()
    Serie.objects.filter(grupo__organizacion__in=organizaciones).delete()
