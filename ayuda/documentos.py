"""
Los documentos del proyecto (carpeta docs/, en Markdown) convertidos en HTML para la sección «Ayuda»:
«How to?», «Documentación de la plataforma» y «Guía de desarrollo». Los bloques «mermaid» se dejan como
código: los dibuja la isla «documento» de interfaz.js; las listas «- [ ]» llevan casillas.

Se leen del disco en cada visita, pero la conversión se guarda en memoria mientras el fichero no cambie
(se compara su fecha de modificación), así que verlos no cuesta casi nada y siempre están al día.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

import markdown
from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe

from base.contrato import Vista

# Carpeta de los documentos.
CARPETA = settings.BASE_DIR / "docs"


@dataclass(frozen=True)
class Documento:
    """
    Un documento de docs/ que se ve como pestaña (menú superior) de una subsección de «Ayuda».
    """

    # Nombre en la dirección: /ayuda/<clave>/. Ejemplo: «registro-y-validacion».
    clave: str
    # Fichero dentro de docs/. Ejemplo: «registro-y-validacion.md».
    fichero: str
    # Título de la pestaña. Ejemplo: «Registro y validación».
    titulo: str
    # Código de la subsección de «Ayuda» en la que sale como pestaña («ayuda.plataforma»). Quién puede
    # verlo lo decide esa subsección: la misma regla que la muestra u oculta en el menú.
    apartado: str


# Los documentos, en el orden de sus pestañas. Para cambiar uno de grupo basta con cambiar su apartado;
# para añadir un grupo nuevo, se declara su subsección en ayuda/apps.py y se coloca en config/menu.py.
DOCUMENTOS = (
    Documento("como-se-hace", "como-se-hace.md", "How to?", "ayuda.como_se_hace"),
    Documento("tutorial", "tutorial.md", "Tutorial", "ayuda.plataforma"),
    Documento("arquitectura", "arquitectura.md", "Arquitectura", "ayuda.plataforma"),
    Documento("arranque", "arranque.md", "Arranque y tests", "ayuda.plataforma"),
    Documento("registro-y-validacion", "registro-y-validacion.md", "Registro y validación", "ayuda.plataforma"),
    Documento("seguridad-y-privacidad", "seguridad-y-privacidad.md", "Seguridad y privacidad", "ayuda.plataforma"),
    Documento("comprobaciones", "comprobaciones.md", "Comprobaciones pendientes", "ayuda.guias"),
    Documento("diseno", "diseno.md", "Diseño y decisiones", "ayuda.guias"),
)

# Los mismos documentos, por su clave, para encontrarlos rápido.
POR_CLAVE = {documento.clave: documento for documento in DOCUMENTOS}


# Dice si la documentación de la plataforma y las guías de desarrollo están abiertas a cualquier persona
# con sesión (mientras se desarrolla; ver GUIAS_DE_DESARROLLO_PARA_TODOS en config/settings.py). La usa
# el menú (EntradaDeMenu.tambien_si) y, a través de él, la vista de los documentos.
#   - usuario: quien mira (no se usa: depende solo del entorno).
def guias_abiertas(usuario=None):
    return settings.GUIAS_DE_DESARROLLO_PARA_TODOS


# Nombre de la ruta de la página de un documento («registro_y_validacion»). Cada documento tiene su propia
# ruta para que el menú superior marque la pestaña correcta.
#   - clave: el nombre del documento en la dirección («registro-y-validacion»).
def nombre_de_ruta(clave):
    return clave.replace("-", "_")


# Las pestañas (vistas del menú superior) de una subsección de «Ayuda»: sus documentos, en orden. La usa
# el contrato del módulo (ayuda/apps.py).
#   - apartado: código de la subsección («ayuda.plataforma»).
def vistas_de(apartado):
    return tuple(Vista(documento.titulo, f"ayuda:{nombre_de_ruta(documento.clave)}") for documento in DOCUMENTOS if documento.apartado == apartado)


# Elementos de lista que empiezan por «[ ]» o «[x]» (listas de comprobaciones): se pintan con una casilla
# que la isla «documento» de interfaz.js deja marcar. Puede haber un <p> en medio si la lista es «suelta».
CASILLA = re.compile(r"<li>(\s*<p>)?\[( |x|X)\]\s*")

# Enlaces de un documento a otro («[texto](tutorial.md#seccion)»), para llevarlos a su página.
ENLACE_A_OTRO_DOCUMENTO = re.compile(r'href="([a-z0-9-]+)\.md(#[^"]*)?"')


@dataclass(frozen=True)
class DocumentoConvertido:
    """Un documento ya convertido: su HTML y su índice."""

    # El documento en HTML, listo para pintar.
    html: str
    # El índice (los títulos de sección como lista de enlaces), en HTML.
    indice: str


# Devuelve el documento convertido, o None si no está en la lista. Mira la fecha del fichero para no
# volver a convertirlo si no ha cambiado.
#   - clave: el nombre en la dirección («diseno»).
def convertido(clave):
    documento = POR_CLAVE.get(clave)
    if documento is None:
        return None
    ruta = CARPETA / documento.fichero
    return _convertir(str(ruta), ruta.stat().st_mtime)


# Convierte un fichero Markdown en HTML con índice. La fecha de modificación forma parte de la clave de
# la memoria (lru_cache): si el fichero cambia, se convierte de nuevo.
#   - ruta: dónde está el fichero.
#   - modificado: su fecha de modificación (solo sirve de clave).
@lru_cache(maxsize=16)
def _convertir(ruta, modificado):
    conversor = markdown.Markdown(
        extensions=["tables", "fenced_code", "sane_lists", "toc"],
        # toc: índice con los títulos de nivel 2 y 3, y un «ancla» en cada título para poder enlazarlo.
        extension_configs={"toc": {"toc_depth": "2-3"}},
    )
    # Sin HTML escrito a mano: si un documento menciona una etiqueta («<script>») fuera de un bloque de
    # código, se ve como texto y no se mete en la página como etiqueta de verdad (un <script> se
    # ejecutaría). Se quitan las dos piezas de Python-Markdown que dejan pasar el HTML: la de bloques
    # («html_block») y la de dentro de una línea («html»).
    conversor.preprocessors.deregister("html_block")
    conversor.inlinePatterns.deregister("html")
    with open(ruta, encoding="utf-8") as entrada:
        html = conversor.convert(entrada.read())
    html = ENLACE_A_OTRO_DOCUMENTO.sub(_enlace_a_su_pagina, html)
    html = CASILLA.sub(_casilla, html)
    return DocumentoConvertido(html=mark_safe(html), indice=mark_safe(conversor.toc))


# Cambia «<li>[ ] » por un elemento con su casilla (desactivada hasta que la active la isla). La usa
# _convertir.
def _casilla(coincidencia):
    parrafo = coincidencia.group(1) or ""
    marcada = " checked" if coincidencia.group(2) in "xX" else ""
    return f'<li class="tarea">{parrafo}<input type="checkbox" data-casilla disabled{marcada} aria-label="Hecho"> '


# Cambia un enlace «otro.md#seccion» por la dirección de su página en la aplicación. La usa _convertir.
def _enlace_a_su_pagina(coincidencia):
    clave, ancla = coincidencia.group(1), coincidencia.group(2) or ""
    if clave not in POR_CLAVE:
        return coincidencia.group(0)
    return f'href="{reverse(f"ayuda:{nombre_de_ruta(clave)}")}{ancla}"'
