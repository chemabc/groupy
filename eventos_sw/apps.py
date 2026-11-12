"""
Configuración y contrato del módulo «eventos_sw».
"""

from base.contrato import Capa, ModuloConfig


class EventosSwConfig(ModuloConfig):
    """
    Contrato del módulo «eventos_sw». No emite ni escucha avisos propios: es el que los reparte.
    """

    name = "eventos_sw"
    verbose_name = "Avisos internos (eventos_sw)"
    capa = Capa.BASE
    descripcion = (
        "Avisos internos entre módulos: cuando en un módulo pasa algo, los módulos que lo escuchan "
        "reaccionan, al momento o un poco después, sin depender unos de otros."
    )
