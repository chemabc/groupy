"""
Configuración y contrato del módulo «ayuda».
"""

from base.contrato import Ayuda, Capa, EntradaDeMenu, ModuloConfig, Permiso

from .documentos import DOCUMENTOS, nombre_de_ruta, vistas_de

# Función que abre la documentación de la plataforma y la guía de desarrollo a todo el mundo mientras se
# desarrolla (ver documentos.py).
GUIAS_ABIERTAS = "ayuda.documentos.guias_abiertas"


# Nombre de la ruta del primer documento de una subsección, a la que lleva su entrada del menú.
#   - apartado: código de la subsección («ayuda.plataforma»).
def _primera(apartado):
    return f"ayuda:{nombre_de_ruta(next(documento.clave for documento in DOCUMENTOS if documento.apartado == apartado))}"


class AyudaConfig(ModuloConfig):
    """
    Contrato del módulo «ayuda». Aporta la sección «Ayuda» del menú, con tres subsecciones: «How to?»
    (para todo el mundo), «Documentación de la plataforma» y «Guía de desarrollo» (en desarrollo, para
    todo el mundo; en producción, solo para quien tiene «ayuda.ver_documentacion», el superadmin). Cada
    documento de docs/ es una pestaña de su subsección (ver documentos.py).

    La sección lleva «panel_de_ayuda»: sus subsecciones salen también en el botón «?» rojo de la cabecera,
    que las abre en el panel de la derecha sin dejar la pantalla en la que se está.
    """

    name = "ayuda"
    verbose_name = "Ayuda"
    capa = Capa.FUNCIONAL
    descripcion = (
        "La ayuda de la plataforma: cómo hacer cada cosa, la documentación técnica y las guías de "
        "desarrollo, todo a partir de los documentos Markdown de docs/. Se puede ver en la zona principal o "
        "en el panel de ayuda de la derecha, mientras se trabaja."
    )
    permisos = (
        # Sin roles por defecto: solo lo tiene el superadmin (que lo tiene todo). En desarrollo da igual,
        # porque se abre a todo el mundo (GUIAS_DE_DESARROLLO_PARA_TODOS).
        Permiso(
            "ayuda.ver_documentacion",
            "Ver la documentación de la plataforma y las guías de desarrollo (diseño, arquitectura, comprobaciones…)",
        ),
    )
    menu = (
        EntradaDeMenu(
            codigo="ayuda.ayuda",
            nombre="Ayuda",
            url=_primera("ayuda.como_se_hace"),
            icono="?",
            color="#ef4444",
            panel_de_ayuda=True,
            subsecciones=(
                EntradaDeMenu(
                    codigo="ayuda.como_se_hace",
                    nombre="How to?",
                    url=_primera("ayuda.como_se_hace"),
                    icono="¿",
                    color="#f97316",
                    vistas=vistas_de("ayuda.como_se_hace"),
                ),
                EntradaDeMenu(
                    codigo="ayuda.plataforma",
                    nombre="Documentación de la plataforma",
                    url=_primera("ayuda.plataforma"),
                    icono="¶",
                    color="#ca8a04",
                    permiso="ayuda.ver_documentacion",
                    tambien_si=GUIAS_ABIERTAS,
                    vistas=vistas_de("ayuda.plataforma"),
                ),
                EntradaDeMenu(
                    codigo="ayuda.guias",
                    nombre="Guía de desarrollo",
                    url=_primera("ayuda.guias"),
                    icono="⌬",
                    color="#7e22ce",
                    permiso="ayuda.ver_documentacion",
                    tambien_si=GUIAS_ABIERTAS,
                    vistas=vistas_de("ayuda.guias"),
                ),
            ),
        ),
    )
    ayuda = (
        Ayuda(
            seccion="ayuda.como_se_hace",
            titulo="How to?",
            texto=(
                "Cómo hacer cada cosa en la plataforma, paso a paso.\n\n"
                "Puedes leerlo aquí o en el panel de la derecha: pulsa el «?» rojo de arriba a la derecha y "
                "sigue trabajando con el menú de la izquierda mientras lo lees. La línea que separa el panel "
                "se puede arrastrar, y los botones − y + cambian el tamaño de su letra."
            ),
            ejemplo=(
                "No sabes cómo convocar una reunión: pulsa el ? rojo, elige «How to?» y, con los pasos de "
                "«Convocar un evento» a la derecha, ve a «Eventos → Mis eventos» y rellena el formulario."
            ),
        ),
        Ayuda(
            seccion="ayuda.plataforma",
            titulo="Documentación de la plataforma",
            texto=(
                "Los documentos técnicos del proyecto (docs/ en el repositorio), siempre al día: el tutorial con "
                "lo aprendido, la arquitectura con sus diagramas, cómo arrancar y probar, y cómo funcionan el "
                "registro y la validación. Arriba, una pestaña por documento; a la izquierda del texto, su "
                "índice, que se pliega con su botón.\n\n"
                "Mientras se desarrolla la ve todo el mundo; en producción, solo el superadmin."
            ),
        ),
        Ayuda(
            seccion="ayuda.guias",
            titulo="Guía de desarrollo",
            texto=(
                "«Comprobaciones pendientes»: lo construido en cada pieza, paso a paso, con qué mirar en cada "
                "pantalla. Marca las casillas según lo compruebes (se recuerdan en tu navegador).\n\n"
                "«Diseño y decisiones»: el documento único con las premisas, el glosario y todo lo decidido.\n\n"
                "Mientras se desarrolla la ve todo el mundo; en producción, solo el superadmin."
            ),
        ),
    )
