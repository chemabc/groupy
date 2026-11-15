"""
Anclas: cómo algo de un módulo cuelga de algo de otro sin importarlo (ver Ancla en base/contrato.py). Se
guarda como «tipo + número» («eventos.evento» y 12). Aquí, dos ayudas para los módulos que cuelgan cosas
(documentos, debates, consultas):

- leer_ancla("eventos.evento:12"): convierte el texto de la dirección («?ancla=…») en (tipo, número).
- buscar_ancla(tipo, numero): el elemento de verdad, buscado por el modelo que declara su módulo. Sirve,
  por ejemplo, para que un debate que cuelga de un evento tome su grupo y su audiencia.
"""

from django.apps import apps

from .registro import registro


# Convierte «tipo:número» en (tipo, número), o (None, None) si no es un ancla declarada.
#   - texto: lo que llega en la dirección («eventos.evento:12»).
def leer_ancla(texto):
    tipo, _, numero = (texto or "").rpartition(":")
    if tipo not in registro.anclas or not numero.isdigit():
        return None, None
    return tipo, int(numero)


# El elemento al que apunta un ancla, o None si ya no existe. Una consulta.
#   - tipo: el tipo de ancla («eventos.evento»).
#   - numero: su número.
def buscar_ancla(tipo, numero):
    ancla = registro.anclas.get(tipo)
    if ancla is None or numero is None:
        return None
    return apps.get_model(ancla.modelo).objects.filter(pk=numero).first()
