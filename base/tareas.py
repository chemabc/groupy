"""
Tareas diarias: lo que los módulos declaran en su contrato (TareaDiaria) para hacerlo una vez al día,
como caducar las solicitudes vencidas o crear las siguientes veces de las series de eventos.

Las ejecuta el trabajador (eventos_sw/management/commands/procesar_bandeja.py), que en cada vuelta llama
a ejecutar_las_de_hoy(). Solo la primera vuelta de cada día hace algo: se apunta en la caché (Redis) con
cache.add, que solo funciona para quien llega primero, así que aunque haya dos trabajadores no se
ejecutan dos veces. Para lanzarlas a mano: «python manage.py tareas_diarias».
"""

import logging

from django.core.cache import cache
from django.utils import timezone
from django.utils.module_loading import import_string

from .registro import registro

# Mensajes al registro de la aplicación (se ven en la salida del trabajador).
registro_de_mensajes = logging.getLogger(__name__)


# Ejecuta todas las tareas diarias de todos los módulos. Si una falla, se apunta el error y se sigue con
# las demás. Devuelve una lista de (código, resultado o error).
def ejecutar_todas():
    resultados = []
    for codigo, tarea in registro.tareas_diarias.items():
        try:
            resultados.append((codigo, import_string(tarea.funcion)()))
        except Exception as error:  # noqa: BLE001 - una tarea rota no debe parar las demás.
            registro_de_mensajes.exception("La tarea diaria «%s» ha fallado.", codigo)
            resultados.append((codigo, error))
    return resultados


# Ejecuta las tareas diarias si hoy aún no se han ejecutado. Devuelve la lista de resultados, o None si
# ya se hicieron hoy. Cuesta una consulta a la caché.
def ejecutar_las_de_hoy():
    clave = f"tareas_diarias:{timezone.localdate().isoformat()}"
    if not cache.add(clave, True, 2 * 24 * 3600):
        return None
    return ejecutar_todas()
