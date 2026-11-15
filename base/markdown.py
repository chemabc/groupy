"""
Texto con formato (Markdown) convertido en HTML seguro, para los textos que escriben las personas: órdenes
del día y actas (documentos), argumentos (debates), descripciones de consultas…

Seguro quiere decir que no deja pasar HTML escrito a mano: un «<script>» se ve como texto y no se ejecuta.
Usa Python-Markdown (la misma librería que la ayuda, ayuda/documentos.py).
"""

import html as entidades
import re

import markdown
from django.utils.safestring import mark_safe

# Atributos con una dirección (enlaces e imágenes), para revisarlos uno a uno.
DIRECCION = re.compile(r'(href|src)="([^"]*)"', re.IGNORECASE)
# Esquemas que ejecutarían código al pulsar el enlace o cargar la imagen.
ESQUEMAS_PELIGROSOS = ("javascript:", "data:", "vbscript:")


# Cambia por «#» una dirección que ejecutaría código, aunque venga disimulada con entidades
# («&#106;avascript:»), espacios o mayúsculas. La usa texto_a_html.
def _sin_peligro(coincidencia):
    direccion = "".join(entidades.unescape(coincidencia.group(2)).split()).lower()
    if direccion.startswith(ESQUEMAS_PELIGROSOS):
        return f'{coincidencia.group(1)}="#"'
    return coincidencia.group(0)


# Convierte un texto Markdown en HTML listo para pintar. Admite títulos, listas, tablas, negritas,
# enlaces y bloques de código; no admite HTML.
#   - texto: lo escrito.
def texto_a_html(texto):
    conversor = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
    # Se quitan las dos piezas que dejan pasar HTML: la de bloques y la de dentro de una línea.
    conversor.preprocessors.deregister("html_block")
    conversor.inlinePatterns.deregister("html")
    html = conversor.convert(texto or "")
    return mark_safe(DIRECCION.sub(_sin_peligro, html))
