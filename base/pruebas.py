"""
Ayudas para las pruebas de cualquier módulo.

- modulo_falso: crea un módulo de mentira con el contrato que se quiera, sin carpeta ni apps.py.
- contratos_de_prueba: añade módulos de mentira al registro real mientras dura un bloque «with» y
  después lo deja como estaba. Sirve para probar eventos_sw, el menú o los permisos con declaraciones
  inventadas, sin tocar los contratos de los módulos de verdad.
"""

from contextlib import contextmanager

from django.apps import apps

from .contrato import Capa, ModuloConfig
from .registro import registro


# Crea la configuración de un módulo de mentira con la etiqueta y los apartados indicados.
#   - etiqueta: nombre del módulo (p. ej. «alfa»).
#   - apartados: los atributos del contrato que se quieren rellenar (permisos=…, menu=…). Si no se
#     indica la capa, es funcional.
def modulo_falso(etiqueta, **apartados):
    # Clase creada al vuelo que hereda de ModuloConfig. «path» se fija a mano porque el módulo no existe
    # en disco y Django lo pediría.
    clase = type(f"{etiqueta}Config", (ModuloConfig,), {"capa": Capa.FUNCIONAL, "path": "/tmp", **apartados})
    return clase(etiqueta, None)


# Bloque «with» que recarga el registro con los módulos reales más los de mentira y, al salir, devuelve
# el registro a su estado anterior aunque la prueba falle. Ejemplo:
#     with contratos_de_prueba(modulo_falso("alfa", emite=(Emision("alfa.creado", "…"),))):
#         emitir("alfa.creado", id=1)
@contextmanager
def contratos_de_prueba(*modulos_falsos):
    # Copia de todo lo que contiene el registro, para restaurarlo al final.
    copia = dict(registro.__dict__)
    registro.cargar([*apps.get_app_configs(), *modulos_falsos])
    try:
        yield registro
    finally:
        registro.__dict__.clear()
        registro.__dict__.update(copia)
