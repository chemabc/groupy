"""
Conexión con el editor colaborativo en tiempo real: un servicio aparte (carpeta editor/, en Node) que
cualquier aplicación puede usar. Ver docs/diseno.md, apartado 13.2, y editor/LEEME.md.

Cómo encaja:
- **La plataforma manda.** Decide quién entra en cada texto y con qué permiso (leer, comentar, escribir),
  preguntando al módulo que lo declara (TextoEditable en su contrato). El editor no ve la base de datos ni
  conoce a las personas: solo se fía de los pases.
- **El pase** es un JWT firmado (HS256) con el secreto que comparten la plataforma y el editor. Dice el
  alias, la sala («documentos.documento:12»), el permiso y hasta cuándo vale (pocos minutos). El navegador
  lo pide aquí (editor_pase) y lo lleva al editor.
- **De vuelta:** el editor pide el texto inicial de una sala y avisa de lo escrito cada pocos segundos
  (con quién ha escrito). Esas peticiones llegan firmadas a /editor/texto/ y /editor/guardado/ y van al
  módulo que declara el texto.
- **Cerrar una sala:** al aprobar un acta (o quitar un permiso), la plataforma pide al editor que eche a
  todo el mundo; al volver a entrar, cada persona trae un pase nuevo con su permiso de ahora.

- **La biblioteca** (plantillas, fragmentos, cabeceras y pies, e imágenes) vive en el editor. Para que
  sepa qué ve y qué cambia cada persona, el pase lleva además un número que la identifica sin decir quién
  es (id_para_editor) y sus «ámbitos»: toda la plataforma, sus organizaciones y sus grupos, con «cambiar»
  en los que administra. Los da el módulo que conoce los grupos (contrato: ambitos_del_editor).

Si no hay editor configurado (settings.EDITOR vacío), todo sigue funcionando con el formulario de siempre.
"""

import base64
import hashlib
import hmac
import json
import logging
import time
import urllib.request

from django.conf import settings
from django.utils.module_loading import import_string

from .registro import registro

# Minutos que dura un pase. Corto: si a alguien se le quita el permiso, como mucho entra hasta entonces.
MINUTOS_DE_PASE = 5
# Segundos de margen para la hora de una petición firmada que llega del editor.
MARGEN_DE_HORA = 5 * 60
# Nombre de la «sala» de los pases de la biblioteca (no es un texto: solo sirve para entrar en ella).
SALA_DE_BIBLIOTECA = "biblioteca"
# Colores de los cursores de cada persona (se elige uno por su alias, siempre el mismo).
COLORES = ("#7c3aed", "#0369a1", "#047857", "#b45309", "#be123c", "#4338ca", "#0f766e", "#a21caf")

registro_de_errores = logging.getLogger(__name__)


# Dice si hay editor en tiempo real configurado (settings.EDITOR).
def activo():
    return bool(getattr(settings, "EDITOR", None))


# Nombre de la sala de un texto, tal como lo ve la plataforma: «documentos.documento:12».
def sala(tipo, numero):
    return f"{tipo}:{numero}"


# Separa una sala en su tipo y su número. Devuelve (None, None) si no tiene esa forma.
def leer_sala(texto):
    tipo, _, numero = str(texto).rpartition(":")
    return (tipo, int(numero)) if tipo and numero.isdigit() else (None, None)


# El TextoEditable declarado para un tipo, o None.
def editable(tipo):
    return registro.textos_editables.get(tipo)


# Pasa bytes a base64url sin relleno (como piden los JWT).
def _base64url(datos):
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


# Firma un texto con el secreto del editor (HMAC-SHA256).
def _firma(texto):
    return hmac.new(settings.EDITOR["secreto"].encode(), texto.encode(), hashlib.sha256).digest()


# Fabrica un JWT HS256 con unos datos (función interna de pase()).
def _jwt(datos):
    cabecera = _base64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    cuerpo = _base64url(json.dumps(datos, separators=(",", ":")).encode())
    return f"{cabecera}.{cuerpo}.{_base64url(_firma(f'{cabecera}.{cuerpo}'))}"


# Número con el que el editor conoce a una persona (para la biblioteca: lo suyo y lo compartido con ella).
# Siempre el mismo para la misma persona, pero no deja saber quién es ni su número en la plataforma: es una
# firma HMAC de su número con el secreto del editor, recortada.
def id_para_editor(usuario):
    return _base64url(_firma(f"usuario:{usuario.pk}"))[:22]


# Lo que el pase lleva para la biblioteca: el número de la persona y sus ámbitos. Vacío si ningún módulo
# da los ámbitos (contrato: ambitos_del_editor).
def _biblioteca(usuario):
    if not registro.ambitos_del_editor:
        return {}
    return {"usuario": id_para_editor(usuario), "ambitos": import_string(registro.ambitos_del_editor)(usuario)}


# Lo que necesita la pantalla de la biblioteca: dirección, cliente y un pase (sala «biblioteca», para
# leer). None si no hay editor o ningún módulo da ámbitos. Lo usan la pantalla de la biblioteca (en
# «documentos») y editor_pase, que lo renueva.
#   - usuario: quien entra.
def pase_de_biblioteca(usuario):
    biblioteca = _biblioteca(usuario) if activo() else {}
    if not biblioteca:
        return None
    datos = {
        "app": settings.EDITOR["app"], "sala": SALA_DE_BIBLIOTECA, "alias": str(usuario), "permiso": "leer",
        "exp": int(time.time()) + MINUTOS_DE_PASE * 60, **biblioteca,
    }
    return {"url": settings.EDITOR["url"], "cliente": settings.EDITOR["url"].replace("ws", "http", 1) + "/cliente.js", "pase": _jwt(datos)}


# Color fijo de una persona en el editor, sacado de su alias.
def color_de(alias):
    return COLORES[int(hashlib.sha256(alias.encode()).hexdigest(), 16) % len(COLORES)]


# Lo que necesita el navegador para entrar en la sala de un texto: dirección, sala, pase, alias, color,
# permiso, formato y si hay biblioteca (entonces el pase lleva el número de la persona y sus ámbitos). El pase lleva además lo que diga el módulo (TextoEditable.opciones): título y cuántas
# personas pueden escribir y comentar a la vez. None si no hay editor o si la persona no puede ni leerlo. Lo usan las pantallas que pintan el
# editor (con la plantilla base/_editor.html) y editor_pase, que renueva el pase al reconectar.
#   - usuario: quien va a entrar.
#   - tipo, numero: el texto (su tipo de ancla y su número).
def pase(usuario, tipo, numero):
    declarado = editable(tipo)
    if not activo() or declarado is None:
        return None
    permiso = import_string(declarado.permiso)(usuario, numero)
    if not permiso:
        return None
    alias = str(usuario)
    opciones = import_string(declarado.opciones)(numero) if declarado.opciones else {}
    biblioteca = _biblioteca(usuario)
    datos = {
        "app": settings.EDITOR["app"], "sala": sala(tipo, numero), "alias": alias, "permiso": permiso,
        "exp": int(time.time()) + MINUTOS_DE_PASE * 60, **{clave: valor for clave, valor in opciones.items() if valor is not None},
        **biblioteca,
    }
    return {
        "url": settings.EDITOR["url"], "cliente": settings.EDITOR["url"].replace("ws", "http", 1) + "/cliente.js", "sala": f"{settings.EDITOR['app']}/{sala(tipo, numero)}", "pase": _jwt(datos),
        "alias": alias, "color": color_de(alias), "permiso": permiso, "tipo": tipo, "numero": numero,
        "formato": opciones.get("formato", "markdown"), "biblioteca": bool(biblioteca),
    }


# Comprueba la firma de una petición que llega del editor (cabeceras X-Editor-Hora y X-Editor-Firma).
#   - firmado: lo que se firmó (el cuerpo en un POST, la sala en un GET).
def firma_valida(request, firmado):
    if not activo():
        return False
    hora = request.headers.get("X-Editor-Hora", "")
    if not hora.isdigit() or abs(time.time() - int(hora)) > MARGEN_DE_HORA:
        return False
    esperada = _base64url(_firma(f"{hora}.{firmado}"))
    return hmac.compare_digest(esperada, request.headers.get("X-Editor-Firma", ""))


# Pide al editor que eche a todo el mundo de la sala de un texto (al aprobar un acta, al quitar un
# permiso…). Si el editor no responde, no pasa nada grave: los pases caducan en pocos minutos. Se llama
# después de guardar (transaction.on_commit), nunca a mitad.
def cerrar_sala(tipo, numero):
    if not activo():
        return
    cuerpo = json.dumps({"sala": sala(tipo, numero)})
    hora = str(int(time.time()))
    peticion = urllib.request.Request(
        f"{settings.EDITOR['interna']}/salas/cerrar", data=cuerpo.encode(), method="POST",
        headers={
            "Content-Type": "application/json", "X-Editor-App": settings.EDITOR["app"], "X-Editor-Hora": hora,
            "X-Editor-Firma": _base64url(_firma(f"{hora}.{cuerpo}")),
        },
    )
    try:
        urllib.request.urlopen(peticion, timeout=2).close()
    except OSError as error:
        registro_de_errores.warning("No se ha podido cerrar la sala %s en el editor: %s", sala(tipo, numero), error)
