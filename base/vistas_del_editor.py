"""
Direcciones con las que hablan el navegador y el editor colaborativo en tiempo real (ver base/editor.py):
- /editor/pase/: el navegador pide un pase nuevo al reconectar (con su sesión, como cualquier pantalla).
- /editor/texto/, /editor/guardado/ y /editor/comentarios/: las llama el servidor del editor, sin sesión
  pero con su firma.
Cada una pasa la petición al módulo que declara el texto (TextoEditable), sin importarlo.
"""

import json

from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden, HttpResponseNotFound, JsonResponse
from django.utils.module_loading import import_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import editor


# Pase nuevo para entrar en la sala de un texto (lo pide el editor en el navegador al reconectar, porque
# los pases duran pocos minutos). Devuelve {"pase": "…"} o 403 si ya no puede entrar. Sin más consultas
# que las del permiso del módulo.
#   - GET «sala»: «documentos.documento:12».
@require_GET
def pase(request):
    tipo, numero = editor.leer_sala(request.GET.get("sala", ""))
    datos = editor.pase(request.user, tipo, numero) if tipo else None
    if datos is None:
        return HttpResponseForbidden("Ya no puedes entrar en este texto.")
    return JsonResponse({"pase": datos["pase"], "permiso": datos["permiso"]})


# El texto con el que empieza una sala (lo pide el editor cuando no la tiene o la tiene vieja). Devuelve
# {"texto", "version"}.
#   - GET «sala», firmada con el secreto del editor.
@login_not_required
@require_GET
def texto(request):
    nombre = request.GET.get("sala", "")
    if not editor.firma_valida(request, nombre):
        return HttpResponseForbidden("Firma no válida.")
    tipo, numero = editor.leer_sala(nombre)
    declarado = editor.editable(tipo) if tipo else None
    if declarado is None:
        return HttpResponseNotFound("No se conoce ese texto.")
    texto, version = import_string(declarado.texto)(numero)
    return JsonResponse({"texto": texto, "version": version})


# Lo escrito en una sala (lo envía el editor unos segundos después de cada cambio, con quién ha escrito).
# Devuelve {"version"} o 409 si ya no se aceptan cambios (el editor cierra entonces la sala).
#   - POST en JSON: «sala», «texto», «alias» (lista) y «version», firmado con el secreto del editor.
@login_not_required
@csrf_exempt
@require_POST
def guardado(request):
    cuerpo = request.body.decode()
    if not editor.firma_valida(request, cuerpo):
        return HttpResponseForbidden("Firma no válida.")
    datos = json.loads(cuerpo)
    tipo, numero = editor.leer_sala(datos.get("sala", ""))
    declarado = editor.editable(tipo) if tipo else None
    if declarado is None:
        return HttpResponseNotFound("No se conoce ese texto.")
    try:
        version = import_string(declarado.guardar)(numero, datos.get("texto", ""), list(datos.get("alias", [])), datos.get("version"))
    except ValidationError as error:
        return JsonResponse({"error": " ".join(error.messages)}, status=409)
    return JsonResponse({"version": version})


# Los comentarios hechos en el editor (los manda el editor cada vez que cambian, todos los de la sala).
# Responde 404 si el módulo no los guarda (el editor lo entiende y no insiste).
#   - POST en JSON: «sala» y «comentarios» (lista), firmado con el secreto del editor.
@login_not_required
@csrf_exempt
@require_POST
def comentarios(request):
    cuerpo = request.body.decode()
    if not editor.firma_valida(request, cuerpo):
        return HttpResponseForbidden("Firma no válida.")
    datos = json.loads(cuerpo)
    tipo, numero = editor.leer_sala(datos.get("sala", ""))
    declarado = editor.editable(tipo) if tipo else None
    if declarado is None or not declarado.comentarios:
        return HttpResponseNotFound("No se guardan comentarios de ese texto.")
    import_string(declarado.comentarios)(numero, list(datos.get("comentarios", [])))
    return JsonResponse({"guardados": len(datos.get("comentarios", []))})
