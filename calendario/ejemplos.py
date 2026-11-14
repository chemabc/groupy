"""
Calendario y datos de ejemplo. «calendario» no crea ejemplos propios, pero al borrar los de los demás
módulos («python manage.py ejemplos borrar») quita antes los recordatorios apuntados al probar en los
grupos de ejemplo o por personas de ejemplo: si no, protegerían a quién lo ven y no se podrían borrar.
"""

from django.db.models import Q

from grupos.ejemplos import organizaciones_de_ejemplo
from usuarios.ejemplos import usuarios_de_ejemplo

from .models import Recordatorio


# Borra los recordatorios de los grupos de las organizaciones de ejemplo y los de las personas de ejemplo.
def borrar():
    Recordatorio.objects.filter(Q(grupo__organizacion__in=organizaciones_de_ejemplo()) | Q(autor__in=usuarios_de_ejemplo())).delete()
