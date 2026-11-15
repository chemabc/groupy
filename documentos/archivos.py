"""
Comprobar los archivos que se suben a «documentos» antes de guardarlos (ver docs/diseno.md, apartado 13.4):

1. El tipo: solo PDF, imágenes, formatos abiertos de oficina (odt, ods, odp, odg) y texto (txt, csv, md).
   Nunca formatos de Microsoft (docx, xlsx, pptx…): el aviso explica cómo guardarlo en un formato abierto.
2. El contenido: que de verdad sea lo que dice su extensión (cada formato empieza con su «firma»). Así no
   se cuela, por ejemplo, un programa con el nombre «informe.pdf».
3. El tamaño (20 MB) y el espacio que le queda a la organización.
4. El antivirus: ClamAV, un servicio aparte (en docker, «antivirus»). Se le habla por su protocolo
   («INSTREAM», por trozos), sin librerías. Si no hay antivirus configurado (desarrollo y pruebas), el
   archivo queda «sin revisar».

Lo usan los servicios de subir archivos (documentos/servicios.py).
"""

import io
import socket
import struct
import zipfile
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError

# Tamaño máximo de cada archivo: 20 MB.
TAMANO_MAXIMO = 20 * 1024 * 1024

# Tipos admitidos: extensión → (tipo de contenido para el navegador, si se ve en el navegador o se descarga).
ADMITIDOS = {
    "pdf": ("application/pdf", True),
    "png": ("image/png", True),
    "jpg": ("image/jpeg", True),
    "jpeg": ("image/jpeg", True),
    "webp": ("image/webp", True),
    "gif": ("image/gif", True),
    "odt": ("application/vnd.oasis.opendocument.text", False),
    "ods": ("application/vnd.oasis.opendocument.spreadsheet", False),
    "odp": ("application/vnd.oasis.opendocument.presentation", False),
    "odg": ("application/vnd.oasis.opendocument.graphics", False),
    "txt": ("text/plain; charset=utf-8", False),
    "csv": ("text/csv; charset=utf-8", False),
    "md": ("text/markdown; charset=utf-8", False),
}

# Extensiones de Microsoft que nunca se admiten (decisión de la persona usuaria en [A-60]).
DE_MICROSOFT = {
    "doc", "docx", "docm", "dot", "dotx", "dotm", "xls", "xlsx", "xlsm", "xlsb", "xlt", "xltx", "xltm",
    "ppt", "pptx", "pptm", "pps", "ppsx", "pot", "potx", "pub", "vsd", "vsdx", "one", "msg", "mpp", "accdb", "mdb",
}

# Aviso para los formatos de Microsoft.
AVISO_MICROSOFT = (
    "No se admiten formatos de Microsoft (docx, xlsx, pptx…). Guárdalo como PDF o en un formato abierto "
    "(en LibreOffice o en el propio Office: «Guardar como» → odt, ods u odp) y súbelo de nuevo."
)

# Tipo de contenido que llevan dentro los formatos abiertos de oficina (el fichero «mimetype» del zip).
TIPO_DE_ODF = {
    "odt": b"application/vnd.oasis.opendocument.text",
    "ods": b"application/vnd.oasis.opendocument.spreadsheet",
    "odp": b"application/vnd.oasis.opendocument.presentation",
    "odg": b"application/vnd.oasis.opendocument.graphics",
}


@dataclass(frozen=True)
class ArchivoComprobado:
    """Lo que se sabe de un archivo que ha pasado todas las comprobaciones."""

    # Su contenido.
    contenido: bytes
    # Su nombre original, sin carpetas.
    nombre: str
    # Su extensión, en minúsculas.
    extension: str
    # Tipo de contenido para el navegador.
    tipo_mime: str
    # Si lo revisó el antivirus («limpio») o no lo hay («sin_revisar»).
    revision: str


# Comprueba un archivo subido y devuelve un ArchivoComprobado, o lanza ValidationError con una explicación
# en lenguaje llano. No mira el espacio de la organización (eso lo hace el servicio, que sabe de cuál es).
#   - subido: el archivo que llega del formulario (UploadedFile de Django).
def comprobar(subido):
    nombre = (subido.name or "archivo").replace("\\", "/").rsplit("/", 1)[-1][:255]
    extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    if extension in DE_MICROSOFT:
        raise ValidationError(AVISO_MICROSOFT)
    if extension not in ADMITIDOS:
        raise ValidationError(
            "Ese tipo de archivo no se admite. Se pueden subir PDF, imágenes (PNG, JPG, WebP, GIF), documentos "
            "abiertos (odt, ods, odp, odg) y texto (txt, csv, md)."
        )
    if subido.size > TAMANO_MAXIMO:
        raise ValidationError(f"El archivo ocupa {subido.size / 1024 / 1024:.1f} MB; como mucho, {TAMANO_MAXIMO // 1024 // 1024} MB.")
    contenido = subido.read()
    if not contenido:
        raise ValidationError("El archivo está vacío.")
    if not _firma_correcta(contenido, extension):
        raise ValidationError(f"El contenido no parece un archivo «{extension}». Comprueba que no se haya cambiado el nombre.")
    revision = revisar_con_el_antivirus(contenido)
    return ArchivoComprobado(contenido, nombre, extension, ADMITIDOS[extension][0], revision)


# Dice si un archivo se ve en el navegador (PDF e imágenes) o se descarga.
def se_ve_en_el_navegador(extension):
    return ADMITIDOS.get(extension, ("", False))[1]


# Dice si el contenido empieza como debe para su extensión (su «firma»).
#   - contenido: los bytes.
#   - extension: la extensión ya admitida.
def _firma_correcta(contenido, extension):
    if extension == "pdf":
        return contenido.startswith(b"%PDF-")
    if extension == "png":
        return contenido.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in ("jpg", "jpeg"):
        return contenido.startswith(b"\xff\xd8\xff")
    if extension == "gif":
        return contenido.startswith((b"GIF87a", b"GIF89a"))
    if extension == "webp":
        return contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP"
    if extension in TIPO_DE_ODF:
        # Un formato abierto es un zip cuyo primer fichero, «mimetype», dice qué es.
        try:
            with zipfile.ZipFile(io.BytesIO(contenido)) as zip_:
                return zip_.read("mimetype").strip() == TIPO_DE_ODF[extension]
        except (zipfile.BadZipFile, KeyError):
            return False
    # Texto: debe leerse como UTF-8 y no llevar bytes nulos (los programas los llevan).
    if b"\x00" in contenido:
        return False
    try:
        contenido.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


# ── Antivirus (ClamAV) ───────────────────────────────────────────────────────────────────────────────


# Tamaño de cada trozo que se manda al antivirus.
TROZO = 64 * 1024


# Pasa un contenido por el antivirus. Devuelve «limpio», o «sin_revisar» si no hay antivirus configurado
# (ajuste ANTIVIRUS vacío). Lanza ValidationError si encuentra un virus o si está configurado y no responde
# (entonces no se guarda nada: mejor esperar que guardar sin revisar).
#   - contenido: los bytes del archivo.
def revisar_con_el_antivirus(contenido):
    direccion = getattr(settings, "ANTIVIRUS", "")
    if not direccion:
        return "sin_revisar"
    servidor, _, puerto = direccion.rpartition(":")
    try:
        respuesta = _instream(servidor, int(puerto), contenido)
    except (OSError, ValueError) as error:
        raise ValidationError("El antivirus no responde y el archivo no se ha guardado. Prueba de nuevo en un rato.") from error
    if respuesta.endswith("OK"):
        return "limpio"
    if "FOUND" in respuesta:
        raise ValidationError("El antivirus ha encontrado un virus en el archivo y no se ha guardado.")
    raise ValidationError("El antivirus no ha podido revisar el archivo y no se ha guardado. Prueba de nuevo en un rato.")


# Manda el contenido a clamd con la orden INSTREAM: cada trozo, precedido de su tamaño en 4 bytes; al
# final, un trozo de tamaño cero. Devuelve la respuesta («stream: OK» o «stream: Eicar-Test FOUND»).
#   - servidor, puerto: dónde escucha clamd.
#   - contenido: los bytes.
def _instream(servidor, puerto, contenido):
    with socket.create_connection((servidor, puerto), timeout=30) as conexion:
        conexion.sendall(b"zINSTREAM\0")
        for inicio in range(0, len(contenido), TROZO):
            trozo = contenido[inicio : inicio + TROZO]
            conexion.sendall(struct.pack("!L", len(trozo)) + trozo)
        conexion.sendall(struct.pack("!L", 0))
        respuesta = b""
        while not respuesta.endswith(b"\0"):
            parte = conexion.recv(4096)
            if not parte:
                break
            respuesta += parte
    return respuesta.rstrip(b"\0").decode("utf-8", "replace").strip()
