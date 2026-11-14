"""
Configuración y contrato del módulo «etiquetas».
"""

from base.contrato import Ayuda, Capa, DatosDeEjemplo, EntradaDeMenu, ModuloConfig, Permiso, Vista


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
    # «Administrar → Mi organización → Etiquetas» (13 de noviembre de 2026), colocada dentro de «Configuración» en config/menu.py.
    menu = (
        EntradaDeMenu(
            codigo="etiquetas.etiquetas",
            nombre="Etiquetas",
            url="etiquetas:etiquetas",
            icono="#",
            color="#be185d",
            permiso="etiquetas.ordenar",
            vistas=(Vista("Lista", "etiquetas:etiquetas"),),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="etiquetas.etiquetas",
            titulo="Etiquetas",
            texto=(
                "Palabras sueltas o grupos de dos o tres palabras para encontrar información («Huelga», «Local "
                "nuevo»). Se crean solas cuando alguien las usa, y el selector propone las que ya hay para no "
                "repetirlas. Se guardan con la primera letra en mayúscula, el resto en minúsculas y sin tildes "
                "(la ñ se queda).\n\n"
                "Cada organización tiene las suyas, que no se ven en otras. El superadmin crea además etiquetas "
                "comunes, que sirven en todas.\n\n"
                "Aquí se ordenan: renombrar, poner palabras relacionadas (buscar cualquiera de ellas encuentra la "
                "etiqueta), fusionar las repetidas y borrar. «La llevan» dice cuántas cosas la tienen puesta."
            ),
        ),
    )
