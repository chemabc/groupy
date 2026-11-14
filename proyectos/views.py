"""
Pantallas de la sección «Proyectos»: los proyectos de mis grupos y los personales (en árbol, con sus
subproyectos), crear un proyecto o un subproyecto, la ficha (con su lugar en el árbol, subproyectos,
tareas y cometidos), editar, el kanban de un proyecto (con las tareas de sus subproyectos) y las tareas
(mis tareas en lista y en kanban, crear, ficha y mover en el kanban).
"""

import json

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from audiencias.cercania import cercania, ids_que_ven
from audiencias.selector import clave_de, opciones
from etiquetas.servicios import etiquetas_de
from base.registro import registro
from grupos.models import Grupo
from permisos.servicios import SinPermiso, explicar_falta, permisos_de, puede
from tipologias.models import Tipologia
from tipologias.servicios import a_json, arbol, campos_de, formulario_de, tareas_modelo_de

from . import servicios
from .arboles import arboles_de_proyectos
from .formularios import FormularioDeProyecto, FormularioDeRecurso, FormularioDeTarea
from .models import Proyecto, Recurso, Tarea

# Cuántos proyectos o tareas se muestran como mucho en cada lista.
MAXIMO = 300


# ── Listas de proyectos ──────────────────────────────────────────────────────────────────────────────


# Pantalla «Proyectos de mis grupos»: los proyectos de grupo que se ven, un árbol por proyecto principal
# en una rejilla de 3 columnas (proyectos/arboles.py), con sus subproyectos debajo y sus tareas plegadas.
# Los finalizados, en gris; los archivados (con todo su árbol), no: están en «Archivo». Cada uno con sus
# etiquetas, que se pulsan para ver solo los que la llevan. Unas 6 consultas.
#   - GET «etiqueta»: solo los proyectos con esa etiqueta (su nombre exacto).
def proyectos(request):
    etiqueta = request.GET.get("etiqueta", "").strip()
    consulta = servicios.visibles(request.user).filter(personal=False, raiz__archivado__isnull=True)
    if etiqueta:
        consulta = consulta.filter(pk__in=servicios.con_etiqueta(etiqueta))
    lista = list(consulta.select_related("grupo__organizacion", "tipologia")[:MAXIMO])
    etiquetas = servicios.etiquetas_de_varios(p.pk for p in lista)
    for proyecto in lista:
        proyecto.etiquetas = etiquetas.get(proyecto.pk, [])
    contexto = {"arboles": arboles_de_proyectos(request.user, lista), "personal": False, "etiqueta": etiqueta}
    return render(request, "proyectos/lista.html", contexto)


# Pantalla «Personales»: mis proyectos personales (en árboles, como en «De mis grupos») y mis tareas
# personales sueltas, sin lo archivado.
def personales(request):
    lista = list(Proyecto.objects.filter(personal=True, creador=request.user, raiz__archivado__isnull=True).select_related("tipologia")[:MAXIMO])
    tareas = list(Tarea.objects.filter(personal=True, proyecto__isnull=True, creador=request.user, archivado__isnull=True).order_by("estado", "limite", "pk")[:MAXIMO])
    return render(request, "proyectos/lista.html", {"arboles": arboles_de_proyectos(request.user, lista), "personal": True, "tareas": tareas})


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
# GET que se envía solo; después, los datos, las etiquetas y si se crean las tareas modelo de su tipo.
# Con «padre», es un subproyecto: el grupo es el del padre.
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
        modelos = tareas_modelo_de(tipologia, {rama.tipologia.pk: rama.tipologia for rama in ramas})
        organizacion = None if personal else grupo.organizacion
        formulario = FormularioDeProyecto(datos, visibilidades=visibilidades, organizacion=organizacion, tareas_modelo=modelos, initial=inicial)
        propios = _propios(tipologia, datos)
        if request.method == "POST" and formulario.is_valid() and propios.is_valid():
            limpio = formulario.cleaned_data
            try:
                proyecto = servicios.crear_proyecto(
                    usuario, tipologia, formulario.datos_del_proyecto(), grupo=grupo, visibilidad=limpio.get("visibilidad", "privado"),
                    padre=padre, personal=personal, campos=a_json(propios.cleaned_data), etiquetas=limpio.get("etiquetas", ()),
                    tareas_modelo=modelos if limpio.get("con_tareas_modelo") else (),
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
# datos, su árbol entero arriba (con sus subproyectos y sus tareas plegadas) y sus cometidos. Quien lo gestiona cambia el estado,
# da cometidos, crea subproyectos, apunta recursos (y los pide con una petición de talentos) y lo borra
# desde aquí.
#   - POST «accion»: «estado» (con «estado»), «apuntar» o «desapuntar» (con «cometido» y, para otra
#     persona, «alias»), «recurso» (con los campos de FormularioDeRecurso), «conseguido», «pendiente»,
#     «quitar_recurso» o «pedir_recurso» (con «recurso»), o «borrar».
def proyecto(request, pk):
    usuario = request.user
    proyecto = get_object_or_404(Proyecto.objects.select_related("grupo__organizacion", "tipologia", "audiencia", "creador"), pk=pk)
    if not servicios.ve(usuario, proyecto):
        raise SinPermiso("Este proyecto no es para ti: solo lo ven las personas a las que llega.")
    entero = servicios.arbol_entero(proyecto)
    gestiona = servicios.puede_gestionar(usuario, proyecto, entero)
    accion = request.POST.get("accion") if request.method == "POST" else None
    error = ""
    nuevo_recurso = FormularioDeRecurso(request.POST if accion == "recurso" else None, prefix="recurso")
    try:
        if accion == "recurso":
            if not nuevo_recurso.is_valid():
                raise ValidationError(" ".join(" ".join(errores) for errores in nuevo_recurso.errors.values()))
            servicios.anadir_recurso(usuario, proyecto, nuevo_recurso.cleaned_data)
        elif accion in ("conseguido", "pendiente", "quitar_recurso", "pedir_recurso"):
            recurso = get_object_or_404(Recurso, pk=request.POST.get("recurso"), proyecto=proyecto)
            recurso.proyecto = proyecto
            if accion == "quitar_recurso":
                servicios.borrar_recurso(usuario, recurso)
            elif accion == "pedir_recurso":
                peticion = servicios.pedir_recurso(usuario, recurso)
                return redirect("talentos:peticion", peticion.pk)
            else:
                servicios.marcar_recurso(usuario, recurso, accion == "conseguido")
        elif accion == "estado":
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
    camino = [(p, p.pk in visibles_del_arbol) for p in servicios.antecesores(proyecto, entero)]
    recursos = list(proyecto.recursos.all())
    etiquetas = [] if proyecto.personal else etiquetas_de((servicios.ANCLA, proyecto.pk))
    de_cometidos = [] if proyecto.personal else servicios.cometidos(proyecto)
    del_arbol = [p for p in entero.values() if p.pk in visibles_del_arbol]
    contexto = {
        "proyecto": proyecto,
        # Todo su árbol (lo que se ve), con este proyecto en un recuadro rojo.
        "arboles": arboles_de_proyectos(usuario, del_arbol, actual=proyecto.pk),
        # Un proyecto se archiva con todo su árbol: lo dice su proyecto principal.
        "archivado": entero[proyecto.raiz_id].archivado if proyecto.raiz_id in entero else None,
        "camino": camino,
        "recursos": recursos,
        "etiquetas": etiquetas,
        "nuevo_recurso": nuevo_recurso,
        "pide_recursos": bool(recursos) and servicios.puede_pedir_recursos(usuario, proyecto, gestiona),
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
    inicial = {} if proyecto.personal else {"visibilidad": clave_de(proyecto.audiencia, proyecto.grupo), "etiquetas": etiquetas_de((servicios.ANCLA, proyecto.pk))}
    organizacion = None if proyecto.personal else proyecto.grupo.organizacion
    formulario = FormularioDeProyecto(datos, instance=proyecto, visibilidades=visibilidades, organizacion=organizacion, initial=inicial)
    propios = _propios(proyecto.tipologia, datos, proyecto.campos)
    if request.method == "POST" and formulario.is_valid() and propios.is_valid():
        try:
            servicios.editar_proyecto(
                usuario, proyecto, formulario.datos_del_proyecto(), visibilidad=formulario.cleaned_data.get("visibilidad"),
                campos=a_json(propios.cleaned_data), etiquetas=formulario.cleaned_data.get("etiquetas"),
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
# «Personales»), sin las archivadas ni las de proyectos archivados. Sin ejecutar.
def _mias(usuario):
    sin_archivar = Q(archivado__isnull=True, proyecto__raiz__archivado__isnull=True)
    return Tarea.objects.filter(sin_archivar, Q(responsable=usuario) | Q(colaboradores=usuario)).distinct().select_related("proyecto", "grupo", "responsable")


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
    candidatas = _candidatas(proyecto) if proyecto else None
    if personal:
        personas = None
    elif proyecto:
        personas = _personas(f"proyecto={proyecto.pk}", proyecto.grupo, audiencia=proyecto.audiencia)
    else:
        clave = (datos or {}).get("visibilidad", "grupo:0")
        clave = clave if clave in dict(visibilidades) else "grupo:0"
        personas = _personas(f"grupo={grupo.pk}", grupo, clave=clave, parametros=("visibilidad",))
    formulario = FormularioDeTarea(
        datos, visibilidades=visibilidades, personal=personal, candidatas=candidatas, personas=personas, initial={"visibilidad": "grupo:0"}
    )
    if request.method == "POST" and formulario.is_valid():
        try:
            tarea = servicios.crear_tarea(
                usuario, formulario.datos_de_la_tarea(usuario), colaboradores=formulario.cleaned_data.get("colaboradores", []),
                proyecto=proyecto, grupo=grupo, personal=personal, visibilidad=formulario.cleaned_data.get("visibilidad") or "grupo:0",
                espera_a=formulario.cleaned_data.get("espera_a") or (),
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("proyectos:proyecto", proyecto.pk) if proyecto else redirect("proyectos:tarea", tarea.pk)
    contexto = {"formulario": formulario, "proyecto": proyecto, "personal": personal, "grupos": grupos, "grupo": grupo}
    return render(request, "proyectos/nueva_tarea.html", contexto)


# Lo que necesita el selector de personas del formulario de una tarea: la dirección de la lista, la función
# con los ids de quienes se pueden elegir (solo se llama al guardar) y los campos de los que depende.
#   - consulta: lo que se añade a la dirección de la lista para saber de qué tarea se trata
#     («proyecto=7», «tarea=12», «grupo=3»).
#   - grupo: el grupo de referencia (de donde se mide la cercanía).
#   - audiencia, clave: quién ve la tarea (la audiencia del proyecto, o la opción de visibilidad).
#   - parametros: campos del formulario que cambian la lista (en una tarea suelta nueva, «visibilidad»).
def _personas(consulta, grupo, audiencia=None, clave=None, parametros=()):
    url = f"{reverse('proyectos:personas_para_tarea')}?{consulta}"
    return url, lambda: ids_que_ven(grupo, audiencia=audiencia, clave=clave), parametros


# Lista de personas para elegir responsable y colaboradoras de una tarea, en JSON, por cercanía (ver
# audiencias/cercania.py). La pide el selector de personas al abrirse. 6 consultas, haya las personas que haya.
#   - GET «proyecto»: una tarea nueva en ese proyecto (hay que verlo).
#   - GET «tarea»: una tarea que ya existe (hay que verla).
#   - GET «grupo» y «visibilidad»: una tarea suelta nueva en ese grupo (hay que poder crear allí).
def personas_para_tarea(request):
    usuario, parametros = request.user, request.GET
    if parametros.get("proyecto", "").isdigit():
        proyecto = get_object_or_404(Proyecto.objects.select_related("grupo__organizacion", "audiencia"), pk=parametros["proyecto"])
        if proyecto.personal or not servicios.ve(usuario, proyecto):
            raise Http404
        datos = cercania(usuario, proyecto.grupo, audiencia=proyecto.audiencia)
    elif parametros.get("tarea", "").isdigit():
        tarea = get_object_or_404(Tarea.objects.select_related("proyecto__audiencia", "grupo__organizacion"), pk=parametros["tarea"])
        if tarea.personal or not servicios.tareas_visibles(usuario).filter(pk=tarea.pk).exists():
            raise Http404
        if tarea.proyecto_id:
            datos = cercania(usuario, tarea.grupo, audiencia=tarea.proyecto.audiencia)
        else:
            datos = cercania(usuario, tarea.grupo, clave=tarea.visibilidad)
    elif parametros.get("grupo", "").isdigit():
        grupo = get_object_or_404(Grupo.objects.select_related("organizacion"), pk=parametros["grupo"])
        if not puede(usuario, "proyectos.crear", grupo=grupo):
            raise Http404
        clave = parametros.get("visibilidad", "grupo:0")
        datos = cercania(usuario, grupo, clave=clave if clave in dict(opciones(grupo)) else "grupo:0")
    else:
        raise Http404
    return JsonResponse(datos.como_datos())


# Tareas a las que puede esperar una tarea de un proyecto: las de todo su árbol (consulta), salvo ella.
#   - proyecto: el proyecto de la tarea.
#   - tarea: la tarea, si ya existe.
def _candidatas(proyecto, tarea=None):
    consulta = Tarea.objects.filter(proyecto__raiz_id=proyecto.raiz_id).select_related("proyecto").order_by("proyecto__titulo", "titulo")
    return consulta.exclude(pk=tarea.pk) if tarea else consulta


# Ficha de una tarea, con a qué espera y a quién desbloquea, su formulario para quien puede cambiarla y
# el botón de borrar.
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
    espera_a = list(tarea.espera_a.order_by("titulo"))
    if cambia:
        candidatas = _candidatas(tarea.proyecto, tarea) if tarea.proyecto_id else None
        if tarea.personal:
            personas = None
        elif tarea.proyecto_id:
            personas = _personas(f"tarea={tarea.pk}", tarea.grupo, audiencia=tarea.proyecto.audiencia)
        else:
            personas = _personas(f"tarea={tarea.pk}", tarea.grupo, clave=tarea.visibilidad)
        formulario = FormularioDeTarea(
            request.POST if accion == "guardar" else None, instance=tarea, personal=tarea.personal, candidatas=candidatas,
            personas=personas, initial={"espera_a": [otra.pk for otra in espera_a]},
        )
    if accion == "borrar":
        servicios.borrar_tarea(usuario, tarea)
        return redirect("proyectos:proyecto", tarea.proyecto_id) if tarea.proyecto_id else redirect("proyectos:tareas")
    if accion == "guardar" and formulario.is_valid():
        try:
            servicios.editar_tarea(
                usuario, tarea, formulario.datos_de_la_tarea(usuario),
                colaboradores=formulario.cleaned_data.get("colaboradores") if "colaboradores" in formulario.fields else None,
                espera_a=formulario.cleaned_data.get("espera_a") if "espera_a" in formulario.fields else None,
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("proyectos:tarea", tarea.pk)
    contexto = {
        "tarea": tarea,
        "camino": _camino_de_la_tarea(usuario, tarea),
        "cambia": cambia,
        "colaboradores": colaboradores,
        "espera_a": espera_a,
        "desbloquea": list(tarea.desbloquea.order_by("titulo")),
        "formulario": formulario,
        "abrir": accion == "guardar",
        "estados": Tarea.ESTADOS,
    }
    return render(request, "proyectos/tarea.html", contexto)


# Los proyectos de los que viene una tarea, del principal al suyo, para el camino de su ficha («Tareas ›
# Huerto › Riego › la tarea»): pares (proyecto, si quien mira lo ve). Vacío si la tarea no está en un
# proyecto. Dos consultas.
#   - usuario: quien mira.
#   - tarea: la tarea, con su proyecto cargado.
def _camino_de_la_tarea(usuario, tarea):
    if not tarea.proyecto_id:
        return []
    entero = servicios.arbol_entero(tarea.proyecto)
    visibles = set(servicios.visibles(usuario).filter(raiz_id=tarea.proyecto.raiz_id).values_list("pk", flat=True))
    proyectos = [*servicios.antecesores(tarea.proyecto, entero), entero.get(tarea.proyecto_id, tarea.proyecto)]
    return [(proyecto, proyecto.pk in visibles) for proyecto in proyectos]


# Datos de una tarea que se cambian sobre lo ya escrito, en su ficha (los demás, en el desplegable
# «Completar o cambiar», con el selector de personas o las dependencias).
CAMPOS_EN_SITIO = ("titulo", "descripcion", "limite", "estado")


# Cambia un solo dato de una tarea desde su ficha: se pulsa el dato, se escribe encima y se guarda. Lo
# pide htmx desde el fragmento «proyectos/_campo_de_tarea.html» y recibe el mismo fragmento, ya con el
# valor nuevo (o con el error, y abierto para corregirlo). Cuesta unas 8 consultas.
#   - pk: el número de la tarea.
#   - POST «campo»: uno de CAMPOS_EN_SITIO.
#   - POST «valor»: lo escrito.
@require_POST
def tarea_campo(request, pk):
    usuario = request.user
    tarea = get_object_or_404(Tarea.objects.select_related("proyecto"), pk=pk)
    if not servicios.tareas_visibles(usuario).filter(pk=tarea.pk).exists():
        raise SinPermiso("Esta tarea no es para ti.")
    if not servicios.puede_cambiar(usuario, tarea):
        raise SinPermiso("Solo quien se encarga de la tarea, quien colabora o quien gestiona el proyecto pueden cambiarla.")
    campo = request.POST.get("campo", "")
    if campo not in CAMPOS_EN_SITIO:
        raise Http404("Ese dato no se cambia desde aquí.")
    error = ""
    try:
        valor = FormularioDeTarea.base_fields[campo].clean(request.POST.get("valor", ""))
        servicios.editar_tarea(usuario, tarea, {campo: valor})
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
        tarea.refresh_from_db()
    return render(request, "proyectos/_campo_de_tarea.html", {"tarea": tarea, "campo": campo, "cambia": True, "error": error, "estados": Tarea.ESTADOS})


# Mueve una tarea en el kanban (lo llama la isla «kanban»). Recibe JSON {tarea, estado, orden} y responde
# {"ok": true} (con «otras»: cuántas tareas más han cambiado solas, si alguna) o un error 400 con
# {"error": "por qué"}.
@require_POST
def mover_tarea(request):
    try:
        datos = json.loads(request.body)
        tarea = Tarea.objects.select_related("proyecto").get(pk=int(datos["tarea"]))
        orden = [int(pk) for pk in datos.get("orden", [])]
        otras = servicios.mover_tarea(request.user, tarea, datos.get("estado", ""), orden)
    except (ValueError, KeyError, TypeError, Tarea.DoesNotExist):
        return JsonResponse({"error": "Datos no válidos."}, status=400)
    except ValidationError as error:
        return JsonResponse({"error": " ".join(error.messages)}, status=400)
    # Si otras tareas han cambiado de columna solas (esperaban a esta), la isla recarga el tablero.
    return JsonResponse({"ok": True, "otras": otras} if otras else {"ok": True})
