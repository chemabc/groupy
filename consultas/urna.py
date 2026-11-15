"""
La urna de las consultas secretas: dónde esperan las papeletas antes de guardarse.

Si cada papeleta se guardara al votar, en la base de datos quedaría junto a la fila de «quién ha votado»
(se crean a la vez, en la misma operación), y quien tuviera la base podría emparejarlas por su orden. Por
eso la papeleta va primero a esta urna, en Redis, y se guarda en la base en **tandas de TANDA o más,
desordenadas**: el orden ya no dice nada y cada papeleta queda escondida entre las de su tanda. Al
cerrarse la consulta se vacía lo que quede (aunque sean menos).

Cada urna es una lista de Redis por consulta, con las papeletas en JSON (sin nombre: clave, asamblea base y
respuestas). El nombre lleva la base de datos, para que las pruebas (con su propia base) no se mezclen con
el desarrollo.
"""

import json
import random

import redis
from django.conf import settings
from django.db import connection

# Cuántas papeletas tienen que juntarse para guardarlas (cada una queda escondida entre, al menos, estas).
TANDA = 5


# Conexión con Redis (la misma que la caché; ver REDIS_URL en config/settings.py).
def _redis():
    return redis.Redis.from_url(settings.URNA_REDIS_URL)


# Nombre de la urna de una consulta en Redis.
def _nombre(consulta_id):
    return f"urna:{connection.settings_dict['NAME']}:{consulta_id}"


# Mete una papeleta en la urna. Devuelve cuántas hay ya.
#   - papeleta: {"clave", "grupo_id", "respuestas"}.
def meter(consulta_id, papeleta):
    return _redis().rpush(_nombre(consulta_id), json.dumps(papeleta))


# Las papeletas que esperan en la urna, sin sacarlas (para los resultados en tiempo real).
def mirar(consulta_id):
    return [json.loads(dato) for dato in _redis().lrange(_nombre(consulta_id), 0, -1)]


# Saca todas las papeletas de la urna (de una vez: nadie más puede sacarlas a la vez) y las devuelve
# desordenadas. Si una misma clave está dos veces (alguien cambió su voto), queda solo la última.
def sacar(consulta_id):
    tuberia = _redis().pipeline(transaction=True)
    tuberia.lrange(_nombre(consulta_id), 0, -1)
    tuberia.delete(_nombre(consulta_id))
    datos, _ = tuberia.execute()
    por_clave = {}
    for dato in datos:
        papeleta = json.loads(dato)
        por_clave[papeleta["clave"]] = papeleta
    papeletas = list(por_clave.values())
    random.SystemRandom().shuffle(papeletas)
    return papeletas


# Borra todas las urnas de esta base de datos (solo lo usan las pruebas, para empezar limpias).
def vaciar_todas():
    cliente = _redis()
    for nombre in cliente.scan_iter(f"urna:{connection.settings_dict['NAME']}:*"):
        cliente.delete(nombre)
