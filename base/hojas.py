"""
Leer y escribir hojas de cálculo sencillas: .ods (LibreOffice) y .csv.

Lo usan las importaciones masivas (Desarrollo y mantenimiento → Pruebas): para crear las plantillas que
se descargan y para leer lo que se sube.

Un .ods es un fichero zip con varios ficheros XML dentro; los datos están en «content.xml». Aquí se
escribe y se lee con la librería estándar de Python (zipfile y xml.etree), sin dependencias: solo hace
falta texto en celdas, una hoja de instrucciones, la primera fila en negrita y desplegables con las
opciones válidas de algunas columnas.
"""

import csv
import io
import zipfile
from dataclasses import dataclass, field
from xml.etree import ElementTree
from xml.sax.saxutils import escape, quoteattr

from .tablas import normalizar

# Espacios de nombres del formato OpenDocument (ODF 1.2), con el prefijo que usa cada uno.
ESPACIOS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "of": "urn:oasis:names:tc:opendocument:xmlns:of:1.2",
}
# Tipo de fichero de una hoja de cálculo de LibreOffice.
TIPO_ODS = "application/vnd.oasis.opendocument.spreadsheet"
# Filas vacías con desplegables que se dejan preparadas en la plantilla, debajo de los ejemplos.
FILAS_PREPARADAS = 500
# Máximo de filas y columnas que se leen (para que un fichero raro no llene la memoria).
MAXIMO_DE_FILAS = 5000
MAXIMO_DE_COLUMNAS = 30


class HojaIlegible(ValueError):
    """El fichero subido no se puede leer como hoja de cálculo (formato desconocido o dañado)."""


@dataclass
class Hoja:
    """Una hoja para escribir en un .ods."""

    # Nombre de la pestaña.
    nombre: str
    # Filas, cada una una lista de textos. La primera es la cabecera (en negrita) si «con_cabecera».
    filas: list
    # Si la primera fila es la cabecera (en negrita).
    con_cabecera: bool = True
    # Ancho de cada columna, en centímetros (si falta, 4 cm).
    anchos: list = field(default_factory=list)
    # Desplegables: {número de columna (desde 0): lista de opciones válidas}.
    desplegables: dict = field(default_factory=dict)


# ── Escribir ─────────────────────────────────────────────────────────────────────────────────────────


# Crea un fichero .ods con las hojas indicadas y devuelve sus bytes, listos para descargar.
#   - hojas: lista de Hoja.
def crear_ods(hojas):
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as zip_:
        # El tipo de fichero va el primero y sin comprimir: así lo exige el formato.
        zip_.writestr(zipfile.ZipInfo("mimetype"), TIPO_ODS, compress_type=zipfile.ZIP_STORED)
        zip_.writestr("META-INF/manifest.xml", _manifiesto(), compress_type=zipfile.ZIP_DEFLATED)
        zip_.writestr("content.xml", _contenido(hojas), compress_type=zipfile.ZIP_DEFLATED)
    return salida.getvalue()


# El índice del zip (manifest.xml): qué ficheros lleva y de qué tipo es el documento.
def _manifiesto():
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">'
        f'<manifest:file-entry manifest:full-path="/" manifest:version="1.2" manifest:media-type="{TIPO_ODS}"/>'
        '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
        "</manifest:manifest>"
    )


# El contenido (content.xml): estilos (negrita y anchos), los desplegables y las hojas con sus celdas.
def _contenido(hojas):
    espacios = " ".join(f'xmlns:{prefijo}="{direccion}"' for prefijo, direccion in ESPACIOS.items())
    anchos = sorted({ancho for hoja in hojas for ancho in _anchos(hoja)})
    estilos = "".join(
        f'<style:style style:name="col{numero}" style:family="table-column">'
        f'<style:table-column-properties style:column-width="{ancho}cm"/></style:style>'
        for numero, ancho in enumerate(anchos)
    )
    estilos += (
        '<style:style style:name="cabecera" style:family="table-cell">'
        '<style:text-properties fo:font-weight="bold" style:font-weight-asian="bold" style:font-weight-complex="bold"/>'
        "</style:style>"
    )
    validaciones = "".join(
        _validacion(hoja, columna, opciones) for hoja in hojas for columna, opciones in sorted(hoja.desplegables.items())
    )
    cuerpo = (f"<table:content-validations>{validaciones}</table:content-validations>" if validaciones else "") + "".join(
        _tabla(hoja, anchos) for hoja in hojas
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<office:document-content {espacios} office:version="1.2">'
        f"<office:automatic-styles>{estilos}</office:automatic-styles>"
        f"<office:body><office:spreadsheet>{cuerpo}</office:spreadsheet></office:body>"
        "</office:document-content>"
    )


# Ancho de cada columna de una hoja (4 cm las que no lo dicen).
def _anchos(hoja):
    columnas = max((len(fila) for fila in hoja.filas), default=0)
    return [hoja.anchos[numero] if numero < len(hoja.anchos) else 4 for numero in range(columnas)]


# Nombre del desplegable de una columna de una hoja (los nombres deben ser únicos en el documento).
def _nombre_de_validacion(hoja, columna):
    return f"lista_{normalizar(hoja.nombre).replace(' ', '_')}_{columna}"


# Un desplegable: la lista de opciones válidas de una columna. Deja la celda vacía si se quiere.
def _validacion(hoja, columna, opciones):
    lista = ";".join(f'"{opcion}"' for opcion in opciones)
    condicion = quoteattr(f"of:cell-content-is-in-list({lista})")
    return (
        f'<table:content-validation table:name="{_nombre_de_validacion(hoja, columna)}" '
        f'table:condition={condicion} table:allow-empty-cell="true" table:display-list="unsorted" '
        f'table:base-cell-address={quoteattr(f"{hoja.nombre}.A1")}/>'
    )


# Una hoja: sus columnas (con su ancho), sus filas y, debajo, filas vacías con los desplegables.
def _tabla(hoja, anchos):
    columnas = "".join(
        f'<table:table-column table:style-name="col{anchos.index(ancho)}"/>' for ancho in _anchos(hoja)
    )
    total = len(_anchos(hoja))
    filas = []
    for numero, fila in enumerate(hoja.filas):
        estilo = ' table:style-name="cabecera"' if hoja.con_cabecera and numero == 0 else ""
        con_desplegable = not (hoja.con_cabecera and numero == 0)
        celdas = "".join(
            _celda(hoja, columna, fila[columna] if columna < len(fila) else "", estilo, con_desplegable)
            for columna in range(total)
        )
        filas.append(f"<table:table-row>{celdas}</table:table-row>")
    if hoja.desplegables:
        vacias = "".join(_celda(hoja, columna, "", "", True) for columna in range(total))
        filas.append(f'<table:table-row table:number-rows-repeated="{FILAS_PREPARADAS}">{vacias}</table:table-row>')
    return f"<table:table table:name={quoteattr(hoja.nombre)}>{columnas}{''.join(filas)}</table:table>"


# Una celda de texto (o vacía), con su estilo y, si la columna lo tiene, su desplegable.
def _celda(hoja, columna, texto, estilo, con_desplegable):
    desplegable = ""
    if con_desplegable and columna in hoja.desplegables:
        desplegable = f' table:content-validation-name="{_nombre_de_validacion(hoja, columna)}"'
    if texto == "":
        return f"<table:table-cell{estilo}{desplegable}/>"
    parrafos = "".join(f"<text:p>{escape(linea)}</text:p>" for linea in str(texto).split("\n"))
    return f'<table:table-cell{estilo}{desplegable} office:value-type="string">{parrafos}</table:table-cell>'


# ── Leer ─────────────────────────────────────────────────────────────────────────────────────────────


# Lee la primera hoja (o la llamada «Datos») de un .ods o un .csv subido y devuelve sus filas como
# listas de textos, sin las filas vacías del todo. Cada fila va con su número en la hoja (como lo ve
# la persona en LibreOffice), para poder decir «fila 7: …».
#   - fichero: el fichero subido (UploadedFile de Django o cualquier objeto con name y read()).
# Devuelve una lista de (número de fila, [textos]).
def leer_filas(fichero):
    nombre = (getattr(fichero, "name", "") or "").lower()
    contenido = fichero.read()
    if nombre.endswith(".ods"):
        filas = _leer_ods(contenido)
    elif nombre.endswith(".csv"):
        filas = _leer_csv(contenido)
    else:
        raise HojaIlegible("Sube un fichero .ods (LibreOffice) o .csv.")
    return [(numero, fila) for numero, fila in filas if any(celda.strip() for celda in fila)]


# Lee las filas de un .ods. Devuelve (número de fila, [textos]).
def _leer_ods(contenido):
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as zip_:
            raiz = ElementTree.fromstring(zip_.read("content.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise HojaIlegible("El fichero no es una hoja de LibreOffice (.ods) válida.") from error
    tablas = raiz.findall(f".//{{{ESPACIOS['table']}}}table")
    if not tablas:
        raise HojaIlegible("El fichero no tiene ninguna hoja.")
    nombre = f"{{{ESPACIOS['table']}}}name"
    tabla = next((tabla for tabla in tablas if tabla.get(nombre) == "Datos"), tablas[0])
    filas, numero = [], 0
    for fila in tabla.iter(f"{{{ESPACIOS['table']}}}table-row"):
        repeticiones = int(fila.get(f"{{{ESPACIOS['table']}}}number-rows-repeated", "1"))
        celdas = _celdas_de(fila)
        if any(celdas):
            for _ in range(min(repeticiones, MAXIMO_DE_FILAS)):
                numero += 1
                filas.append((numero, celdas))
        else:
            numero += repeticiones
        if len(filas) >= MAXIMO_DE_FILAS:
            break
    return filas


# Los textos de las celdas de una fila de un .ods, teniendo en cuenta las celdas repetidas.
def _celdas_de(fila):
    textos = []
    for celda in fila:
        if celda.tag not in (f"{{{ESPACIOS['table']}}}table-cell", f"{{{ESPACIOS['table']}}}covered-table-cell"):
            continue
        repeticiones = int(celda.get(f"{{{ESPACIOS['table']}}}number-columns-repeated", "1"))
        texto = _texto_de(celda)
        textos.extend([texto] * min(repeticiones, MAXIMO_DE_COLUMNAS))
        if len(textos) >= MAXIMO_DE_COLUMNAS:
            break
    while textos and not textos[-1]:
        textos.pop()
    return textos


# El texto de una celda de un .ods tal como se ve: para los números, su valor; para el texto, sus
# párrafos (unidos con saltos de línea) con los espacios repetidos que el formato guarda aparte.
def _texto_de(celda):
    tipo = celda.get(f"{{{ESPACIOS['office']}}}value-type")
    if tipo in ("float", "percentage", "currency"):
        valor = celda.get(f"{{{ESPACIOS['office']}}}value", "")
        return valor[:-2] if valor.endswith(".0") else valor
    parrafos = []
    for parrafo in celda.findall(f"{{{ESPACIOS['text']}}}p"):
        parrafos.append(_texto_de_parrafo(parrafo))
    return "\n".join(parrafos).strip()


# El texto de un párrafo de un .ods, con sus partes (negritas, enlaces…) y los espacios repetidos
# (<text:s text:c="3"/> son tres espacios).
def _texto_de_parrafo(elemento):
    partes = [elemento.text or ""]
    for hijo in elemento:
        if hijo.tag == f"{{{ESPACIOS['text']}}}s":
            partes.append(" " * int(hijo.get(f"{{{ESPACIOS['text']}}}c", "1")))
        elif hijo.tag == f"{{{ESPACIOS['text']}}}tab":
            partes.append("\t")
        else:
            partes.append(_texto_de_parrafo(hijo))
        partes.append(hijo.tail or "")
    return "".join(partes)


# Lee las filas de un .csv, adivinando el separador (coma, punto y coma o tabulador) y la codificación
# (UTF-8, con o sin marca, o Latin-1, la de las hojas antiguas de Windows).
def _leer_csv(contenido):
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = contenido.decode("latin-1")
    try:
        dialecto = csv.Sniffer().sniff(texto[:4096], delimiters=",;\t")
    except csv.Error:
        dialecto = csv.excel
    filas = []
    for numero, fila in enumerate(csv.reader(io.StringIO(texto), dialecto), start=1):
        filas.append((numero, [celda.strip() for celda in fila[:MAXIMO_DE_COLUMNAS]]))
        if numero >= MAXIMO_DE_FILAS:
            break
    return filas


# Convierte las filas leídas en diccionarios por columna, usando la primera fila como cabecera. Cada
# columna esperada se reconoce por cualquiera de sus nombres, sin importar mayúsculas ni tildes
# («Organización», «organizacion»…). Devuelve (filas como diccionarios con «fila», columnas que faltan).
#   - filas: lo que devuelve leer_filas().
#   - columnas: {clave: [nombres posibles]}; la primera de cada lista es el nombre de la plantilla.
#   - obligatorias: claves que deben estar en la cabecera.
def filas_por_columna(filas, columnas, obligatorias):
    if not filas:
        return [], list(obligatorias)
    _numero, cabecera = filas[0]
    posiciones = {}
    for posicion, titulo in enumerate(cabecera):
        titulo = normalizar(titulo.strip())
        for clave, nombres in columnas.items():
            if titulo in {normalizar(nombre) for nombre in nombres} and clave not in posiciones:
                posiciones[clave] = posicion
    faltan = [clave for clave in obligatorias if clave not in posiciones]
    resultado = []
    for numero, fila in filas[1:]:
        datos = {clave: (fila[posicion].strip() if posicion < len(fila) else "") for clave, posicion in posiciones.items()}
        datos.update({clave: "" for clave in columnas if clave not in datos})
        resultado.append({"fila": numero, **datos})
    return resultado, faltan
