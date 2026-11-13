"""
Los documentos del proyecto (carpeta docs/, en Markdown) convertidos en HTML para las pantallas
«Desarrollo y mantenimiento → Ayuda y documentación» y «→ Guías de desarrollo». Los bloques «mermaid» se
dejan como código: los dibuja la isla «documento» de interfaz.js; las listas «- [ ]» llevan casillas.

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

# Carpeta de los documentos.
CARPETA = settings.BASE_DIR / "docs"

# Documentos que se muestran, en este orden: nombre en la dirección, fichero y título.
DOCUMENTOS = [
    ("diseno", "diseno.md", "Diseño y decisiones"),
    ("registro-y-validacion", "registro-y-validacion.md", "Registro y validación"),
    ("tutorial", "tutorial.md", "Tutorial"),
    ("arranque", "arranque.md", "Arranque y pruebas"),
]

# Guías de desarrollo, en «Desarrollo y mantenimiento → Guías de desarrollo»: en desarrollo las ve todo el
# mundo; en producción, solo el superadmin (ver guias_abiertas). Mismo formato que DOCUMENTOS.
GUIAS = [
    ("comprobaciones", "comprobaciones.md", "Comprobaciones pendientes"),
    ("arquitectura", "arquitectura.md", "Arquitectura"),
]


# Dice si las guías de desarrollo están abiertas a cualquier persona con sesión (en desarrollo; ver
# GUIAS_DE_DESARROLLO_PARA_TODOS en config/settings.py). La usa el menú (EntradaDeMenu.tambien_si) y la
# vista de las guías.
#   - usuario: quien mira (no se usa: depende solo del entorno).
def guias_abiertas(usuario=None):
    return settings.GUIAS_DE_DESARROLLO_PARA_TODOS



# Nombre de la ruta de la página de un documento («documento_registro_y_validacion») o de una guía
# («guia_arquitectura»). Cada uno tiene su propia ruta para que el menú superior marque la pestaña correcta.
#   - clave: el nombre del documento en la dirección («registro-y-validacion»).
def nombre_de_ruta(clave):
    prefijo = "guia" if clave in {clave_de_guia for clave_de_guia, _fichero, _titulo in GUIAS} else "documento"
    return f"{prefijo}_{clave.replace('-', '_')}"


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
#   - nombre: el nombre en la dirección («diseno»).
def documento(nombre):
    fichero = next((fichero for clave, fichero, _titulo in DOCUMENTOS + GUIAS if clave == nombre), None)
    if fichero is None:
        return None
    ruta = CARPETA / fichero
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
    nombre, ancla = coincidencia.group(1), coincidencia.group(2) or ""
    if nombre not in {clave for clave, _fichero, _titulo in DOCUMENTOS + GUIAS}:
        return coincidencia.group(0)
    return f'href="{reverse(f"mantenimiento:{nombre_de_ruta(nombre)}")}{ancla}"'
