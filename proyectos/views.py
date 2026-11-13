"""
Pantallas de la sección «Proyectos»: los proyectos de mis grupos y los personales (en árbol, con sus
subproyectos), crear un proyecto o un subproyecto, la ficha (con su lugar en el árbol, subproyectos,
tareas y cometidos), editar, el kanban de un proyecto (con las tareas de sus subproyectos) y las tareas
(mis tareas en lista y en kanban, crear, ficha y mover en el kanban).
"""

import json

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from audiencias.selector import clave_de, opciones
from base.registro import registro
from grupos.models import Grupo
from permisos.servicios import SinPermiso, explicar_falta, permisos_de
from tipologias.models import Tipologia
from tipologias.servicios import a_json, arbol, campos_de, formulario_de

from . import servicios
from .formularios import FormularioDeProyecto, FormularioDeTarea
from .models import Proyecto, Tarea

# Cuántos proyectos o tareas se muestran como mucho en cada lista.
MAXIMO = 300


# ── Listas de proyectos ──────────────────────────────────────────────────────────────────────────────


# Pantalla «Proyectos de mis grupos»: los proyectos de grupo que se ven, en árbol (cada uno con sus
# subproyectos debajo). Los finalizados, al final de su rama y atenuados. Unas 3 consultas.
def proyectos(request):
    lista = list(servicios.visibles(request.user).filter(personal=False).select_related("grupo__organizacion", "tipologia")[:MAXIMO])
    return render(request, "proyectos/lista.html", {"ramas": servicios.en_arbol(lista), "personal": False})


# Pantalla «Personales»: mis proyectos personales (en árbol) y mis tareas personales sueltas.
def personales(request):
    lista = list(Proyecto.objects.filter(personal=True, creador=request.user).select_related("tipologia")[:MAXIMO])
    tareas = list(Tarea.objects.filter(personal=True, proyecto__isnull=True, creador=request.user).order_by("estado", "limite", "pk")[:MAXIMO])
    return render(request, "proyectos/lista.html", {"ramas": servicios.en_arbol(lista), "personal": True, "tareas": tareas})


# ── Crear, ficha y editar ────────────────────────────────────────────────────────────────────────────


# Grupos donde una persona puede crear proyectos y tareas (con «proyectos.crear»), en orden de árbol.
def _grupos_donde_crea(usuario):
    consulta = Grupo.objects.en_orden_de_arbol().select_related("organizacion")
    if usuario.is_superuser:
        return list(consulta)
    ids = [grupo for grupo, codigos in permisos_de(usuario).grupos.items() if "proyectos.crear" in codigos]
    return list(consulta.filter(pk__in=ids))


# Formulario con los campos propios de una tipología, con el prefijo «tipo».
def _propios(tipologia, datos, valores=None):
    formulario = formulario_de(tipologia, datos, valores)
    formulario.prefix = "tipo"
    return formulario


# Pantalla «Nuevo proyecto»: primero se elige el grupo (o que es personal) y el tipo, con un formulario
# GET que se envía solo; después, los datos. Con «padre», es un subproyecto: el grupo es el del padre.
#   - GET «grupo», «tipologia», «padre», «personal» (= 1).
def nuevo(request):
    usuario = request.user
    padre = None
    if request.GET.get("padre", "").isdigit():
        padre = get_object_or_404(Proyecto.objects.select_related("grupo__organizacion", "audiencia"), pk=request.GET["padre"])
        if not servicios.puede_gestionar(usuario, padre):
            raise SinPermiso("Solo quien gestiona el proyecto puede crearle subproyectos.")
    personal = padre.personal if padre else request.GET.get("personal") == "1"
    grupos = [] if personal or padre else _grupos_donde_crea(usuario)
    if not personal and not padre and not grupos:
        raise SinPermiso(explicar_falta("proyectos.crear"))
    grupo = padre.grupo if padre else next((g for g in grupos if str(g.pk) == request.GET.get("grupo", "")), grupos[0] if grupos else None)
    ramas = arbol(Tipologia.PROYECTO, [grupo.organizacion_id] if grupo else [])
    tipologia = next((r.tipologia for r in ramas if str(r.tipologia.pk) == request.GET.get("tipologia", "")), None)
    contexto = {"grupos": grupos, "grupo": grupo, "ramas": ramas, "tipologia": tipologia, "padre": padre, "personal": personal}
    if tipologia is not None:
        datos = request.POST if request.method == "POST" else None
        visibilidades = None if personal else opciones(grupo)
        inicial = {"visibilidad": padre.visibilidad} if padre and not personal else {}
        formulario = FormularioDeProyecto(datos, visibilidades=visibilidades, initial=inicial)
        propios = _propios(tipologia, datos)
        if request.method == "POST" and formulario.is_valid() and propios.is_valid():
            try:
                proyecto = servicios.crear_proyecto(
                    usuario, tipologia, formulario.datos_del_proyecto(), grupo=grupo, visibilidad=formulario.cleaned_data.get("visibilidad", "privado"),
                    padre=padre, personal=personal, campos=a_json(propios.cleaned_data),
                )
            except ValidationError as error:
                formulario.add_error(None, error)
            else:
                return redirect("proyectos:proyecto", proyecto.pk)
        contexto.update(formulario=formulario, propios=propios)
    return render(request, "proyectos/nuevo.html", contexto)


# Los cometidos de los proyectos (declarados en el contrato), cada uno con quién lo tiene y si quien mira
# está apuntado.
def _cometidos_para_pintar(de_cometidos, usuario):
    filas = []
    for codigo, cometido in registro.cometidos.items():
        if codigo.startswith("proyectos."):
            quienes = [c.usuario for c in de_cometidos if c.codigo == codigo]
            filas.append({"codigo": codigo, "nombre": cometido.nombre, "descripcion": cometido.descripcion, "quienes": quienes, "estoy": usuario in quienes})
    return filas


# Ficha de un proyecto: su lugar en el árbol (antecesores, con el nombre solo de los que se ven), sus
# datos, sus subproyectos (en árbol), sus tareas y sus cometidos. Quien lo gestiona cambia el estado,
# da cometidos, crea subproyectos y lo borra desde aquí.
#   - POST «accion»: «estado» (con «estado»), «apuntar» o «desapuntar» (con «cometido» y, para otra
#     persona, «alias»), o «borrar».
def proyecto(request, pk):
    usuario = request.user
    proyecto = get_object_or_404(Proyecto.objects.select_related("grupo__organizacion", "tipologia", "audiencia", "creador"), pk=pk)
    if not servicios.ve(usuario, proyecto):
        raise SinPermiso("Este proyecto no es para ti: solo lo ven las personas a las que llega.")
    entero = servicios.arbol_entero(proyecto)
    gestiona = servicios.puede_gestionar(usuario, proyecto, entero)
    accion = request.POST.get("accion") if request.method == "POST" else None
    error = ""
    try:
        if accion == "estado":
            servicios.editar_proyecto(usuario, proyecto, {"estado": request.POST.get("estado", "")})
        elif accion in ("apuntar", "desapuntar"):
            codigo = request.POST.get("cometido", "")
            if codigo not in registro.cometidos or not codigo.startswith("proyectos."):
                raise ValidationError("Cometido desconocido.")
            persona = usuario
            if request.POST.get("alias"):
                persona = type(usuario).objects.filter(alias__iexact=request.POST["alias"].strip()).first()
                if persona is None:
                    raise ValidationError("No hay nadie con ese alias.")
            (servicios.apuntar if accion == "apuntar" else servicios.desapuntar)(usuario, proyecto, persona, codigo)
        elif accion == "borrar":
            padre = proyecto.padre_id
            servicios.borrar_proyecto(usuario, proyecto)
            return redirect("proyectos:proyecto", padre) if padre else redirect("proyectos:personales" if proyecto.personal else "proyectos:proyectos")
        if accion:
            return redirect("proyectos:proyecto", proyecto.pk)
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
    visibles_del_arbol = set(servicios.visibles(usuario).filter(raiz_id=proyecto.raiz_id).values_list("pk", flat=True))
    debajo = servicios.subarbol(proyecto, entero) - {proyecto.pk}
    subproyectos = servicios.en_arbol([entero[pk] for pk in debajo if pk in visibles_del_arbol])
    camino = [(p, p.pk in visibles_del_arbol) for p in servicios.antecesores(proyecto, entero)]
    tareas = list(proyecto.tareas.select_related("responsable").order_by("estado", "orden", "pk"))
    de_cometidos = [] if proyecto.personal else servicios.cometidos(proyecto)
    contexto = {
        "proyecto": proyecto,
        "camino": camino,
        "subproyectos": subproyectos,
        "tareas": tareas,
        "gestiona": gestiona,
        "error": error,
        "estados": Proyecto.ESTADOS,
        "campos": [(c.nombre, proyecto.campos.get(c.clave)) for c in campos_de(proyecto.tipologia) if proyecto.campos.get(c.clave) not in (None, "")],
        "cometidos": _cometidos_para_pintar(de_cometidos, usuario),
        "coordinacion": servicios.COORDINACION,
    }
    return render(request, "proyectos/proyecto.html", contexto)


# Pantalla «Editar» de un proyecto: los mismos datos que al crearlo, ya rellenos.
def editar(request, pk):
    usuario = request.user
    proyecto = get_object_or_404(Proyecto.objects.select_related("grupo__organizacion", "tipologia", "audiencia", "creador"), pk=pk)
    if not servicios.puede_gestionar(usuario, proyecto):
        raise SinPermiso("Solo quien gestiona el proyecto puede cambiarlo.")
    datos = request.POST if request.method == "POST" else None
    visibilidades = None if proyecto.personal else opciones(proyecto.grupo)
    inicial = {} if proyecto.personal else {"visibilidad": clave_de(proyecto.audiencia, proyecto.grupo)}
    formulario = FormularioDeProyecto(datos, instance=proyecto, visibilidades=visibilidades, initial=inicial)
    propios = _propios(proyecto.tipologia, datos, proyecto.campos)
    if request.method == "POST" and formulario.is_valid() and propios.is_valid():
        try:
            servicios.editar_proyecto(
                usuario, proyecto, formulario.datos_del_proyecto(), visibilidad=formulario.cleaned_data.get("visibilidad"), campos=a_json(propios.cleaned_data)
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("proyectos:proyecto", proyecto.pk)
    return render(request, "proyectos/editar.html", {"proyecto": proyecto, "formulario": formulario, "propios": propios})


# ── Kanban ───────────────────────────────────────────────────────────────────────────────────────────


# Las tareas repartidas en las columnas del kanban (una por estado), en su orden. Las que esa persona
# puede mover llevan «movible».
#   - tareas: lista de tareas (con proyecto y responsable cargados).
#   - movibles: ids de las que se pueden mover.
def _columnas(tareas, movibles):
    columnas = []
    for codigo, nombre in Tarea.ESTADOS:
        de_esta = sorted((t for t in tareas if t.estado == codigo), key=lambda t: (t.orden, t.pk))
        for tarea in de_esta:
            tarea.movible = tarea.pk in movibles
        columnas.append({"codigo": codigo, "nombre": nombre, "tareas": de_esta})
    return columnas


# Ids de las tareas (de una lista) que una persona puede mover, sin una consulta por tarea: las suyas
# (responsable, colaboradora, creadora) y, si gestiona el proyecto, todas las de ese proyecto.
#   - colaboro: ids de las tareas en las que colabora.
#   - proyectos_que_gestiono: ids de proyectos que gestiona.
def _movibles(usuario, tareas, colaboro, proyectos_que_gestiono):
    return {
        t.pk for t in tareas
        if usuario.pk in (t.responsable_id, t.creador_id) or t.pk in colaboro or t.proyecto_id in proyectos_que_gestiono
        or (usuario.is_superuser and not t.personal)
    }


# Pantalla «Kanban» de un proyecto: sus tareas y las de todos sus subproyectos (las que se ven), en
# columnas por estado. Se arrastran de una columna a otra (isla «kanban» de interfaz.js).
def kanban(request, pk):
    usuario = request.user
    proyecto = get_object_or_404(Proyecto.objects.select_related("grupo__organizacion", "audiencia"), pk=pk)
    if not servicios.ve(usuario, proyecto):
        raise SinPermiso("Este proyecto no es para ti.")
    entero = servicios.arbol_entero(proyecto)
    debajo = servicios.subarbol(proyecto, entero)
    visibles_del_arbol = set(servicios.visibles(usuario).filter(pk__in=debajo).values_list("pk", flat=True))
    tareas = list(Tarea.objects.filter(proyecto_id__in=visibles_del_arbol).select_related("proyecto", "responsable"))
    colaboro = set(Tarea.colaboradores.through.objects.filter(usuario_id=usuario.pk, tarea__in=tareas).values_list("tarea_id", flat=True))
    gestiono = visibles_del_arbol if servicios.puede_gestionar(usuario, proyecto, entero) else set()
    contexto = {"proyecto": proyecto, "columnas": _columnas(tareas, _movibles(usuario, tareas, colaboro, gestiono)), "con_proyecto": len(visibles_del_arbol) > 1}
    return render(request, "proyectos/kanban.html", contexto)


# ── Tareas ───────────────────────────────────────────────────────────────────────────────────────────


# Mis tareas: de las que soy responsable o colaboro (sin las personales sueltas, que están en
# «Personales»). Sin ejecutar.
def _mias(usuario):
    return Tarea.objects.filter(Q(responsable=usuario) | Q(colaboradores=usuario)).distinct().select_related("proyecto", "grupo", "responsable")


# Pantalla «Mis tareas»: las pendientes primero, por fecha límite. Unas 3 consultas.
def tareas(request):
    lista = sorted(_mias(request.user)[:MAXIMO], key=lambda t: (t.estado == Tarea.HECHA, t.limite is None, t.limite, t.pk))
    return render(request, "proyectos/tareas.html", {"tareas": lista})


# Pantalla «Kanban» de mis tareas.
def tareas_kanban(request):
    usuario = request.user
    lista = list(_mias(usuario)[:MAXIMO])
    colaboro = {t.pk for t in lista if t.responsable_id != usuario.pk}
    contexto = {"proyecto": None, "columnas": _columnas(lista, _movibles(usuario, lista, colaboro, set())), "con_proyecto": True}
    return render(request, "proyectos/kanban.html", contexto)


# Pantalla «Nueva tarea»: en un proyecto (?proyecto=), suelta en un grupo (se elige) o personal
# (?personal=1).
def nueva_tarea(request):
    usuario = request.user
    proyecto = None
    if request.GET.get("proyecto", "").isdigit():
        proyecto = get_object_or_404(Proyecto.objects.select_related("grupo__organizacion", "audiencia"), pk=request.GET["proyecto"])
        if not servicios.ve(usuario, proyecto):
            raise SinPermiso("No ves ese proyecto.")
    personal = proyecto.personal if proyecto else request.GET.get("personal") == "1"
    grupos = [] if proyecto or personal else _grupos_donde_crea(usuario)
    if not proyecto and not personal and not grupos:
        raise SinPermiso(explicar_falta("proyectos.crear"))
    grupo = next((g for g in grupos if str(g.pk) == request.GET.get("grupo", "")), grupos[0] if grupos else None)
    visibilidades = opciones(grupo) if grupo else None
    datos = request.POST if request.method == "POST" else None
    formulario = FormularioDeTarea(datos, visibilidades=visibilidades, personal=personal, initial={"visibilidad": "grupo:0"})
    if request.method == "POST" and formulario.is_valid():
        try:
            tarea = servicios.crear_tarea(
                usuario, formulario.datos_de_la_tarea(usuario), colaboradores=formulario.cleaned_data.get("colaboradores", []),
                proyecto=proyecto, grupo=grupo, personal=personal, visibilidad=formulario.cleaned_data.get("visibilidad") or "grupo:0",
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("proyectos:proyecto", proyecto.pk) if proyecto else redirect("proyectos:tarea", tarea.pk)
    contexto = {"formulario": formulario, "proyecto": proyecto, "personal": personal, "grupos": grupos, "grupo": grupo}
    return render(request, "proyectos/nueva_tarea.html", contexto)


# Ficha de una tarea, con su formulario para quien puede cambiarla y el botón de borrar.
#   - POST «accion»: «guardar» o «borrar».
def tarea(request, pk):
    usuario = request.user
    tarea = get_object_or_404(Tarea.objects.select_related("proyecto__audiencia", "grupo__organizacion", "responsable", "creador"), pk=pk)
    if not servicios.tareas_visibles(usuario).filter(pk=tarea.pk).exists():
        raise SinPermiso("Esta tarea no es para ti.")
    colaboradores = list(tarea.colaboradores.all())
    cambia = servicios.puede_cambiar(usuario, tarea, {p.pk for p in colaboradores})
    accion = request.POST.get("accion") if request.method == "POST" else None
    if accion and not cambia:
        raise SinPermiso("Solo quien se encarga de la tarea, quien colabora o quien gestiona el proyecto pueden cambiarla.")
    formulario = None
    if cambia:
        formulario = FormularioDeTarea(request.POST if accion == "guardar" else None, instance=tarea, personal=tarea.personal)
    if accion == "borrar":
        servicios.borrar_tarea(usuario, tarea)
        return redirect("proyectos:proyecto", tarea.proyecto_id) if tarea.proyecto_id else redirect("proyectos:tareas")
    if accion == "guardar" and formulario.is_valid():
        try:
            servicios.editar_tarea(
                usuario, tarea, formulario.datos_de_la_tarea(usuario),
                colaboradores=formulario.cleaned_data.get("colaboradores") if "colaboradores" in formulario.fields else None,
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("proyectos:tarea", tarea.pk)
    contexto = {"tarea": tarea, "colaboradores": colaboradores, "formulario": formulario, "abrir": accion == "guardar"}
    return render(request, "proyectos/tarea.html", contexto)


# Mueve una tarea en el kanban (lo llama la isla «kanban»). Recibe JSON {tarea, estado, orden} y responde
# {"ok": true} o un error 400 con {"error": "por qué"}.
@require_POST
def mover_tarea(request):
    try:
        datos = json.loads(request.body)
        tarea = Tarea.objects.select_related("proyecto").get(pk=int(datos["tarea"]))
        orden = [int(pk) for pk in datos.get("orden", [])]
        servicios.mover_tarea(request.user, tarea, datos.get("estado", ""), orden)
    except (ValueError, KeyError, TypeError, Tarea.DoesNotExist):
        return JsonResponse({"error": "Datos no válidos."}, status=400)
    except ValidationError as error:
        return JsonResponse({"error": " ".join(error.messages)}, status=400)
    return JsonResponse({"ok": True})
