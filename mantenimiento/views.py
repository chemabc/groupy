"""
Pantallas del módulo «mantenimiento»: la documentación del proyecto, la importación masiva de grupos y
usuarios y la entrada a la trastienda. Solo para quien tiene el permiso «mantenimiento.ver» (de entrada,
el superadmin).
"""

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from base.hojas import TIPO_ODS, HojaIlegible, crear_ods, leer_filas
from permisos.decoradores import requiere_permiso

from .documentos import documento
from .importacion import (
    COLUMNAS_DE_GRUPOS,
    COLUMNAS_DE_USUARIOS,
    aplicar_grupos,
    aplicar_usuarios,
    plantilla_de_grupos,
    plantilla_de_usuarios,
    revisar_grupos,
    revisar_usuarios,
)
from .models import AjustesDeMantenimiento


# Pantalla «Ayuda y documentación»: un documento de docs/ convertido en página, con su índice a la
# izquierda. Cada documento es una pestaña del menú superior.
#   - nombre: el documento («diseno», «tutorial»…), que pone la dirección.
@requiere_permiso("mantenimiento.ver")
def documentacion(request, nombre):
    convertido = documento(nombre)
    if convertido is None:
        raise Http404("No existe ese documento.")
    return render(request, "mantenimiento/documentacion.html", {"documento": convertido})


# Pantalla «Trastienda»: explica qué es y lleva a ella con un botón.
@requiere_permiso("mantenimiento.ver")
def trastienda(request):
    return render(request, "mantenimiento/trastienda.html")


# ── Importar ─────────────────────────────────────────────────────────────────────────────────────────

# Lo que cambia entre las dos importaciones: textos, columnas, funciones y plantilla.
IMPORTACIONES = {
    "grupos": {
        "que": "organizaciones y grupos",
        "columnas": COLUMNAS_DE_GRUPOS,
        "revisar": revisar_grupos,
        "aplicar": aplicar_grupos,
        "plantilla": "mantenimiento:plantilla_grupos",
        "direccion": "mantenimiento:importar_grupos",
    },
    "usuarios": {
        "que": "usuarios",
        "columnas": COLUMNAS_DE_USUARIOS,
        "revisar": revisar_usuarios,
        "aplicar": aplicar_usuarios,
        "plantilla": "mantenimiento:plantilla_usuarios",
        "direccion": "mantenimiento:importar_usuarios",
    },
}


# Pantalla «Pruebas → Importar grupos».
@requiere_permiso("mantenimiento.ver")
def importar_grupos(request):
    return _importar(request, "grupos", permitido=True)


# Pantalla «Pruebas → Importar usuarios». Solo importa si está permitido el alta masiva.
@requiere_permiso("mantenimiento.ver")
def importar_usuarios(request):
    ajustes = AjustesDeMantenimiento.actuales()
    return _importar(request, "usuarios", permitido=ajustes.alta_masiva_de_usuarios, ajustes=ajustes)


# Lo común de las dos importaciones. Sin datos, muestra la explicación, la plantilla y el formulario.
# Con un POST, según el botón pulsado («accion»):
#   - revisar: lee el fichero subido, lo revisa y muestra la vista previa; si no hay errores, guarda
#     el plan en la sesión para confirmarlo después;
#   - confirmar: aplica el plan guardado (todo o nada) y muestra el resultado;
#   - cancelar: olvida el plan.
#   - tipo: «grupos» o «usuarios».
#   - permitido: si se puede importar (en usuarios, depende del interruptor).
#   - ajustes: los ajustes de mantenimiento, para pintar el interruptor (solo en usuarios).
def _importar(request, tipo, permitido, ajustes=None):
    importacion = IMPORTACIONES[tipo]
    clave_de_sesion = f"mantenimiento.importar.{tipo}"
    contexto = {
        "tipo": tipo,
        "importacion": importacion,
        "columnas": [(clave, nombres[0]) for clave, nombres in importacion["columnas"].items()],
        "permitido": permitido,
        "ajustes": ajustes,
    }
    accion = request.POST.get("accion") if request.method == "POST" else None
    if accion and not permitido:
        contexto["error"] = "El alta masiva de usuarios está desactivada."
    elif accion == "revisar":
        fichero = request.FILES.get("fichero")
        request.session.pop(clave_de_sesion, None)
        if fichero is None:
            contexto["error"] = "Elige un fichero (.ods o .csv) antes de pulsar «Revisar»."
        else:
            try:
                revision = importacion["revisar"](leer_filas(fichero))
            except HojaIlegible as error:
                contexto["error"] = str(error)
            else:
                # Las celdas de cada fila, en el orden de las columnas, para que la plantilla solo pinte.
                for fila in revision.filas:
                    fila.celdas = [fila.datos.get(clave, "") for clave, _titulo in contexto["columnas"]]
                contexto["revision"] = revision
                contexto["nombre_del_fichero"] = fichero.name
                if not revision.hay_errores:
                    request.session[clave_de_sesion] = revision.plan
    elif accion == "confirmar":
        plan = request.session.pop(clave_de_sesion, None)
        if plan is None:
            contexto["error"] = "No hay ninguna importación pendiente de confirmar. Sube el fichero otra vez."
        else:
            try:
                contexto["resultado"] = importacion["aplicar"](plan)
            except (ValidationError, IntegrityError, ObjectDoesNotExist) as error:
                detalle = " ".join(error.messages) if isinstance(error, ValidationError) else str(error)
                contexto["error"] = (
                    "No se ha importado nada: algo ha cambiado desde la vista previa. Sube el fichero otra vez. "
                    f"({detalle})"
                )
    elif accion == "cancelar":
        request.session.pop(clave_de_sesion, None)
    return render(request, "mantenimiento/importar.html", contexto)


# Descarga la plantilla de grupos (.ods).
@requiere_permiso("mantenimiento.ver")
def plantilla_grupos(request):
    return _descargar(crear_ods(plantilla_de_grupos()), "plantilla-grupos.ods")


# Descarga la plantilla de usuarios (.ods), con los roles que existen en el desplegable.
@requiere_permiso("mantenimiento.ver")
def plantilla_usuarios(request):
    return _descargar(crear_ods(plantilla_de_usuarios()), "plantilla-usuarios.ods")


# Respuesta que el navegador guarda como fichero.
def _descargar(contenido, nombre):
    respuesta = HttpResponse(contenido, content_type=TIPO_ODS)
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta


# Activa o desactiva el alta masiva de usuarios (el interruptor de «Importar usuarios»).
@require_POST
@requiere_permiso("mantenimiento.ver")
def permitir_alta_masiva(request):
    ajustes = AjustesDeMantenimiento.actuales()
    ajustes.alta_masiva_de_usuarios = not ajustes.alta_masiva_de_usuarios
    ajustes.save(update_fields=["alta_masiva_de_usuarios"])
    return redirect("mantenimiento:importar_usuarios")
