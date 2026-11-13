"""
Configuración y contrato del módulo «mantenimiento».
"""

from base.contrato import Ayuda, Capa, EntradaDeMenu, ModuloConfig, Permiso, Vista

from .documentos import DOCUMENTOS, GUIAS, nombre_de_ruta

# Función que abre las guías de desarrollo a todo el mundo mientras se desarrolla (ver documentos.py).
GUIAS_ABIERTAS = "mantenimiento.documentos.guias_abiertas"


class MantenimientoConfig(ModuloConfig):
    """
    Contrato del módulo «mantenimiento». Aporta la sección «Desarrollo y mantenimiento» del menú, que
    ve quien tiene el permiso «mantenimiento.ver» (de entrada, solo el superadmin), con cuatro
    subsecciones: las guías de desarrollo (comprobaciones pendientes y arquitectura, que en desarrollo ve
    todo el mundo), la documentación del proyecto, las herramientas de pruebas (importar grupos y
    usuarios) y la entrada a la trastienda.
    """

    name = "mantenimiento"
    verbose_name = "Desarrollo y mantenimiento"
    capa = Capa.FUNCIONAL
    descripcion = (
        "Herramientas para quien mantiene la plataforma: la documentación del proyecto, la importación "
        "masiva de grupos y usuarios para las pruebas y la entrada a la trastienda. Más adelante, la salud "
        "del sistema."
    )
    permisos = (
        # Sin roles por defecto: solo lo tiene el superadmin (que lo tiene todo).
        Permiso("mantenimiento.ver", "Ver la documentación técnica, importar datos de prueba y entrar en la trastienda"),
    )
    menu = (
        EntradaDeMenu(
            codigo="mantenimiento.desarrollo",
            nombre="Desarrollo y mantenimiento",
            url=f"mantenimiento:{nombre_de_ruta(GUIAS[0][0])}",
            icono="⚒",
            color="#ea580c",
            orden=950,
            permiso="mantenimiento.ver",
            tambien_si=GUIAS_ABIERTAS,
            subsecciones=(
                EntradaDeMenu(
                    codigo="mantenimiento.guias",
                    nombre="Guías de desarrollo",
                    url=f"mantenimiento:{nombre_de_ruta(GUIAS[0][0])}",
                    icono="⌬",
                    color="#7e22ce",
                    permiso="mantenimiento.ver",
                    tambien_si=GUIAS_ABIERTAS,
                    vistas=tuple(Vista(titulo, f"mantenimiento:{nombre_de_ruta(clave)}") for clave, _fichero, titulo in GUIAS),
                ),
                EntradaDeMenu(
                    codigo="mantenimiento.documentacion",
                    permiso="mantenimiento.ver",
                    nombre="Ayuda y documentación",
                    url=f"mantenimiento:{nombre_de_ruta(DOCUMENTOS[0][0])}",
                    # Arriba, una pestaña por documento.
                    icono="¶",
                    color="#ca8a04",
                    vistas=tuple(Vista(titulo, f"mantenimiento:{nombre_de_ruta(clave)}") for clave, _fichero, titulo in DOCUMENTOS),
                ),
                EntradaDeMenu(
                    codigo="mantenimiento.pruebas",
                    permiso="mantenimiento.ver",
                    nombre="Pruebas",
                    url="mantenimiento:importar_grupos",
                    icono="⚗",
                    color="#e11d48",
                    vistas=(
                        Vista("Importar grupos", "mantenimiento:importar_grupos"),
                        Vista("Importar usuarios", "mantenimiento:importar_usuarios"),
                        Vista("Datos de ejemplo", "mantenimiento:datos_de_ejemplo"),
                    ),
                ),
                EntradaDeMenu(
                    codigo="mantenimiento.trastienda",
                    permiso="mantenimiento.ver",
                    nombre="Trastienda",
                    url="mantenimiento:trastienda",
                    icono="⚠",
                    color="#dc2626",
                    vistas=(Vista("Trastienda", "mantenimiento:trastienda"),),
                ),
            ),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="mantenimiento.guias",
            titulo="Guías de desarrollo",
            texto=(
                "«Comprobaciones pendientes»: lo construido en cada pieza, paso a paso, con qué mirar en cada "
                "pantalla. Marca las casillas según lo compruebes (se recuerdan en tu navegador).\n\n"
                "«Arquitectura»: diagramas de todo el programa (Django, librerías, servicios, capas y módulos) y, "
                "después, de cada módulo con los que se relaciona. Acerca y aleja con los botones o con doble "
                "clic, y arrastra para moverte.\n\n"
                "Mientras se desarrolla las ve todo el mundo; en producción, solo el superadmin."
            ),
        ),
        Ayuda(
            seccion="mantenimiento.documentacion",
            titulo="Ayuda y documentación",
            texto=(
                "Los documentos del proyecto (docs/ en el repositorio), siempre al día. Arriba, una pestaña por "
                "documento: el diseño con todo lo decidido, cómo funcionan el registro y la validación, el "
                "tutorial con lo aprendido y cómo arrancar y probar. A la izquierda del texto, su índice."
            ),
        ),
        Ayuda(
            seccion="mantenimiento.pruebas",
            titulo="Pruebas",
            texto=(
                "Herramientas para preparar datos de prueba de forma masiva.\n\n"
                "«Importar grupos»: organizaciones y grupos (con sus grupos padre, a cualquier profundidad) a "
                "partir de una hoja de cálculo.\n\n"
                "«Importar usuarios»: alias con su contraseña, sus grupos, su rol y su asamblea base. Solo "
                "funciona si está activado «Permitir el alta masiva de usuarios», porque crea cuentas sin "
                "pasar por la bóveda.\n\n"
                "En los dos casos: descarga la plantilla (.ods de LibreOffice), rellénala, súbela, revisa la "
                "vista previa y confirma. No se crea nada hasta confirmar, y se crea todo o nada.\n\n"
                "«Datos de ejemplo»: crea o borra de un golpe los datos inventados de todos los módulos "
                "(organizaciones de ríos, grupos de afluentes, usuarios de animales y árboles…). Borrarlos no "
                "toca al superadmin. Solo funciona en desarrollo."
            ),
        ),
        Ayuda(
            seccion="mantenimiento.trastienda",
            titulo="Trastienda",
            texto="El panel técnico de Django, para emergencias. El trabajo diario se hace en la aplicación.",
        ),
    )
