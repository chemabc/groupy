"""
Pantalla «Administrar → Mi organización → Tipologías» (de eventos y de proyectos): el árbol a la izquierda y, a la
derecha, la tipología elegida con sus campos (los heredados y los suyos, que se ordenan arrastrando).
"""

import json

from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from permisos.servicios import SinPermiso, explicar_falta

from .formularios import FormularioDeCampo, FormularioDeEdicion, FormularioDeTareaModelo, FormularioDeTipologia
from .models import Tipologia
from .servicios import (
    PERMISO,
    arbol,
    borrar_tipologia,
    campos_de,
    crear_campo,
    crear_tarea_modelo,
    crear_tipologia,
    ordenar_campos,
    organizaciones_que_gestiona,
    puede_editar,
    tareas_modelo_de,
)

# Nombre de la ruta de cada familia.
RUTAS = {Tipologia.EVENTO: "tipologias:eventos", Tipologia.PROYECTO: "tipologias:proyectos"}


# Organizaciones que gestiona quien pide la pantalla; si no gestiona ninguna (ni es superadmin), lanza
# SinPermiso con la explicación.
def _organizaciones_o_error(request):
    organizaciones = organizaciones_que_gestiona(request.user)
    if not organizaciones and not request.user.is_superuser:
        raise SinPermiso(explicar_falta(PERMISO))
    return organizaciones


# Cuelga las ramas del árbol (que vienen en orden, cada una detrás de su padre) unas de otras, para pintarlas
# con el mismo aspecto que los árboles de grupos y de proyectos: en amarillo las que quien mira puede
# cambiar y en rojo la elegida. Sin consultas.
#   - ramas: las Rama de arbol(), en orden.
#   - usuario, organizaciones: quien mira y las organizaciones que gestiona (para saber qué puede cambiar).
#   - elegida: la tipología que se mira, o None.
def _en_nodos(ramas, usuario, organizaciones, elegida):
    raices, por_id = [], {}
    for rama in ramas:
        tipologia = rama.tipologia
        nodo = {
            "tipologia": tipologia,
            "editable": puede_editar(usuario, tipologia, organizaciones),
            "actual": elegida is not None and tipologia.pk == elegida.pk,
            "hijos": [],
        }
        por_id[tipologia.pk] = nodo
        padre = por_id.get(tipologia.padre_id)
        (padre["hijos"] if padre else raices).append(nodo)
    return raices


# Pantalla de las tipologías de una familia. Con «?t=<id>» se ve esa tipología a la derecha.
#   - familia: «evento» o «proyecto» (lo pone la dirección).
#   - POST «accion»: crear_tipologia, editar_tipologia, borrar_tipologia, crear_campo, borrar_campo,
#     crear_tarea_modelo o borrar_tarea_modelo (estas dos, solo en los tipos de proyecto).
def tipologias(request, familia):
    organizaciones = _organizaciones_o_error(request)
    ramas = arbol(familia, None if request.user.is_superuser else [pk for pk, _nombre in organizaciones])
    cargadas = {rama.tipologia.pk: rama.tipologia for rama in ramas}
    elegida_id = request.POST.get("t") or request.GET.get("t") or ""
    elegida = cargadas.get(int(elegida_id)) if elegida_id.isdigit() else None
    editable = elegida is not None and puede_editar(request.user, elegida, organizaciones)
    padres = [(rama.tipologia.pk, rama.camino) for rama in ramas if puede_editar(request.user, rama.tipologia, organizaciones) or rama.tipologia.organizacion_id is None]
    opciones = {"padres": padres, "organizaciones": organizaciones, "comun": request.user.is_superuser}
    datos = request.POST if request.method == "POST" else None
    accion = request.POST.get("accion") if datos else None
    nueva = FormularioDeTipologia(datos if accion == "crear_tipologia" else None, initial={"padre": getattr(elegida, "pk", None)}, **opciones)
    edicion = FormularioDeEdicion(datos if accion == "editar_tipologia" else None, initial={"nombre": getattr(elegida, "nombre", ""), "descripcion": getattr(elegida, "descripcion", "")})
    campo = FormularioDeCampo(datos if accion == "crear_campo" else None)
    tarea_modelo = FormularioDeTareaModelo(datos if accion == "crear_tarea_modelo" else None)
    error = ""
    try:
        if accion == "crear_tipologia" and nueva.is_valid():
            padre = cargadas.get(nueva.cleaned_data["padre"])
            # El desplegable ya solo ofrece sus organizaciones; vacío es «común».
            organizacion = nueva.cleaned_data["organizacion"]
            if padre is not None and padre.organizacion_id and not puede_editar(request.user, padre, organizaciones):
                raise ValidationError("No puedes añadir subtipos a un tipo de otra organización.")
            if organizacion is None and not request.user.is_superuser:
                raise ValidationError("Solo el superadmin crea tipos comunes: elige tu organización.")
            creada = crear_tipologia(familia, nueva.cleaned_data["nombre"], padre=padre, organizacion_id=organizacion, descripcion=nueva.cleaned_data["descripcion"])
            return redirect(f"{reverse(RUTAS[familia])}?t={creada.pk}")
        if accion in ("editar_tipologia", "borrar_tipologia", "crear_campo", "borrar_campo", "crear_tarea_modelo", "borrar_tarea_modelo") and not editable:
            raise ValidationError("Este tipo es común (o de otra organización): solo lo cambia el superadmin.")
        if accion == "editar_tipologia" and edicion.is_valid():
            elegida.nombre, elegida.descripcion = edicion.cleaned_data["nombre"], edicion.cleaned_data["descripcion"]
            elegida.full_clean()
            elegida.save()
            return redirect(f"{reverse(RUTAS[familia])}?t={elegida.pk}")
        if accion == "borrar_tipologia":
            borrar_tipologia(elegida)
            return redirect(reverse(RUTAS[familia]))
        if accion == "crear_campo" and campo.is_valid():
            crear_campo(elegida, **campo.cleaned_data)
            return redirect(f"{reverse(RUTAS[familia])}?t={elegida.pk}")
        if accion == "borrar_campo":
            elegida.campos.filter(pk=request.POST.get("campo")).delete()
            return redirect(f"{reverse(RUTAS[familia])}?t={elegida.pk}")
        if accion == "crear_tarea_modelo" and tarea_modelo.is_valid():
            crear_tarea_modelo(elegida, **tarea_modelo.cleaned_data)
            return redirect(f"{reverse(RUTAS[familia])}?t={elegida.pk}")
        if accion == "borrar_tarea_modelo":
            elegida.tareas_modelo.filter(pk=request.POST.get("tarea_modelo")).delete()
            return redirect(f"{reverse(RUTAS[familia])}?t={elegida.pk}")
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
    campos = campos_de(elegida, cargadas) if elegida else []
    tareas = tareas_modelo_de(elegida, cargadas) if elegida and familia == Tipologia.PROYECTO else []
    contexto = {
        "familia": familia,
        # Las tipologías colgadas en árbol (cada una con sus subtipos), para pintarlas como los demás árboles.
        "nodos": _en_nodos(ramas, request.user, organizaciones, elegida),
        "nombre_de_la_familia": dict(Tipologia.FAMILIAS)[familia],
        "elegida": elegida,
        "camino": next((rama.camino for rama in ramas if elegida and rama.tipologia.pk == elegida.pk), ""),
        "editable": editable,
        "heredados": [c for c in campos if elegida and c.tipologia_id != elegida.pk],
        "propios": [c for c in campos if elegida and c.tipologia_id == elegida.pk],
        "nueva": nueva,
        "edicion": edicion,
        "campo": campo,
        "tareas_heredadas": [t for t in tareas if t.tipologia_id != elegida.pk],
        "tareas_propias": [t for t in tareas if t.tipologia_id == elegida.pk],
        "tarea_modelo": tarea_modelo,
        "con_tareas": familia == Tipologia.PROYECTO,
        "error": error,
        "abrir": accion,
    }
    return render(request, "tipologias/tipologias.html", contexto)


# Guarda el nuevo orden de los campos de una tipología, después de arrastrarlos. La llama el componente
# «listaOrdenable» de interfaz.js. Responde sin contenido (204).
#   - cuerpo JSON: {"tipologia": id, "orden": [ids de los campos]}.
@require_POST
def ordenar(request):
    organizaciones = _organizaciones_o_error(request)
    try:
        datos = json.loads(request.body)
        tipologia = Tipologia.objects.select_related("organizacion").get(pk=int(datos["tipologia"]))
        ids = [int(pk) for pk in datos["orden"]]
    except (ValueError, KeyError, TypeError, Tipologia.DoesNotExist):
        return HttpResponseBadRequest("Datos no válidos.")
    if not puede_editar(request.user, tipologia, organizaciones):
        raise SinPermiso("Este tipo es común (o de otra organización): solo lo cambia el superadmin.")
    ordenar_campos(tipologia, ids)
    return HttpResponse(status=204)
