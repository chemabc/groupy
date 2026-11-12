"""
Creación y borrado de los datos de ejemplo de todos los módulos.

Cada módulo dice en su contrato (apartado datos_de_ejemplo) qué función crea sus datos y cuál los
borra. Aquí se llaman todas, en el orden de las capas: al crear, de abajo arriba (primero los usuarios,
después los grupos que los usan…); al borrar, al revés. Lo usa la orden «python manage.py ejemplos».
"""

from django.db import transaction
from django.utils.module_loading import import_string

from base.registro import registro


# Devuelve las etiquetas de los módulos que tienen datos de ejemplo, ordenadas de la capa más baja a la
# más alta (y, dentro de cada capa, por el orden de INSTALLED_APPS).
def modulos_con_ejemplos():
    orden = list(registro.modulos)
    return sorted(registro.datos_de_ejemplo, key=lambda etiqueta: (registro.modulos[etiqueta].capa, orden.index(etiqueta)))


# Crea los datos de ejemplo de todos los módulos, todo o nada (en una sola transacción). Devuelve las
# etiquetas de los módulos, en el orden en que se han creado.
def crear_todos():
    etiquetas = modulos_con_ejemplos()
    with transaction.atomic():
        for etiqueta in etiquetas:
            import_string(registro.datos_de_ejemplo[etiqueta].crear)()
    return etiquetas


# Borra los datos de ejemplo de todos los módulos, en orden inverso, todo o nada. Devuelve las etiquetas
# de los módulos, en el orden en que se han borrado.
def borrar_todos():
    etiquetas = list(reversed(modulos_con_ejemplos()))
    with transaction.atomic():
        for etiqueta in etiquetas:
            import_string(registro.datos_de_ejemplo[etiqueta].borrar)()
    return etiquetas
