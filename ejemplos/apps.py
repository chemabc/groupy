"""
Configuración y contrato del módulo «ejemplos».
"""

from base.contrato import Capa, ModuloConfig


class EjemplosConfig(ModuloConfig):
    """
    Contrato del módulo «ejemplos». No aporta pantallas: solo la orden «python manage.py ejemplos», que
    crea o borra los datos de ejemplo que declara cada módulo en su contrato (datos_de_ejemplo).
    """

    name = "ejemplos"
    verbose_name = "Datos de ejemplo"
    capa = Capa.BASE
    descripcion = (
        "Crea y borra los datos de ejemplo de todos los módulos, para probar y medir las pantallas en "
        "desarrollo."
    )
