"""
Configuración y contrato del módulo «etiquetas».
"""

from base.contrato import Capa, DatosDeEjemplo, ModuloConfig, Permiso


class EtiquetasConfig(ModuloConfig):
    """
    Contrato del módulo «etiquetas»: palabras cortas para encontrar las cosas, de cada organización (y
    comunes), con palabras relacionadas. Está en la capa de organización porque cada organización tiene
    las suyas.
    """

    name = "etiquetas"
    verbose_name = "Etiquetas"
    capa = Capa.ORGANIZACION
    descripcion = (
        "Etiquetas de una a tres palabras para clasificar y encontrar cualquier cosa, con sus palabras "
        "relacionadas (sinónimos). Cada organización tiene las suyas, y hay etiquetas comunes del superadmin."
    )
    permisos = (
        Permiso(
            "etiquetas.ordenar",
            "Ordenar las etiquetas de la organización: fusionar repetidas, renombrarlas y poner palabras relacionadas",
            roles=("admin_org",),
        ),
    )
    datos_de_ejemplo = DatosDeEjemplo(crear="etiquetas.ejemplos.crear", borrar="etiquetas.ejemplos.borrar")
