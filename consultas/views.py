"""
Pantallas del módulo «consultas»: la lista, crear una y su ficha (preparar las preguntas mientras no se
abre, votar mientras está abierta y ver los resultados cuando toca).
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from audiencias.selector import opciones
from audiencias.servicios import puede_ver
from base.anclas import buscar_ancla, leer_ancla
from base.markdown import texto_a_html
from base.tablas import Columna, Filtro, FuenteDeLista, Tabla
from grupos.acceso import grupos_donde_puede
from permisos.servicios import SinPermiso, explicar_falta

from . import servicios
from .formularios import FormularioDeConsulta, FormularioDePregunta
from .models import Consulta, Participacion, Pregunta

# Máximo de consultas de la lista (se filtran en el navegador).
MAXIMO = 500


# Estado de una consulta en palabras, para la lista y la ficha.
def _estado(consulta, ahora):
    if consulta.estado != Consulta.ACEPTADA:
        return consulta.get_estado_display().split(" (")[0]
    if ahora < consulta.abre:
        return "En preparación"
    return "Abierta" if ahora < consulta.cierra and consulta.cerrada_el is None else "Cerrada"


# Pantalla «Participación → Consultas»: las que ve quien mira, con su estado y si ya ha votado. 3 consultas.
def lista(request):
    usuario, ahora = request.user, timezone.now()
    consultas = list(servicios.visibles(usuario).select_related("grupo")[:MAXIMO])
    votadas = set(Participacion.objects.filter(usuario=usuario, consulta__in=[c.pk for c in consultas]).values_list("consulta_id", flat=True))
    filas = [
        {
            "pk": c.pk, "titulo": c.titulo, "grupo": c.grupo.nombre, "estado": _estado(c, ahora),
            "cierra": timezone.localtime(c.cierra).strftime("%d/%m/%Y %H:%M"), "votado": "Sí" if c.pk in votadas else "",
        }
        for c in consultas
    ]
    tabla = Tabla(
        request,
        identificador="consultas",
        columnas=[Columna("titulo", "Consulta", enlace="consultas:consulta"), Columna("grupo", "Grupo"), Columna("estado", "Estado"), Columna("cierra", "Se cierra"), Columna("votado", "Has votado")],
        fuente=FuenteDeLista(filas, campos_de_busqueda=["titulo", "grupo"]),
        filtros=[Filtro("estado", "Estado", opciones=(("Propuesta", "Propuesta"), ("Esperando apoyos", "Esperando apoyos"), ("En preparación", "En preparación"), ("Abierta", "Abierta"), ("Cerrada", "Cerrada")))],
    )
    plantilla = tabla.plantilla_parcial()
    if plantilla:
        return render(request, plantilla, {"tabla": tabla})
    return render(request, "consultas/lista.html", {"tabla": tabla})


# Pantalla «Nueva consulta»: el grupo arriba y el formulario. Al crearla se va a su ficha para ponerle las
# preguntas. Quien administra el grupo la crea directamente; cualquier miembro la propone (y después pide
# apoyos desde su ficha).
#   - GET «grupo», «ancla».
#   - POST: los campos de FormularioDeConsulta.
def nueva(request):
    usuario = request.user
    grupos = grupos_donde_puede(usuario, "consultas.proponer")
    if not grupos:
        raise SinPermiso(explicar_falta("consultas.proponer"))
    ancla = leer_ancla(request.GET.get("ancla", ""))
    elemento = buscar_ancla(*ancla) if ancla[0] else None
    grupo_del_elemento = getattr(elemento, "grupo_id", None)
    elegido = request.GET.get("grupo", "") or str(grupo_del_elemento or "")
    grupo = next((g for g in grupos if str(g.pk) == elegido), grupos[0])
    ahora = timezone.localtime().replace(second=0, microsecond=0)
    formulario = FormularioDeConsulta(
        request.POST or None, visibilidades=opciones(grupo),
        initial={"abre": ahora + timedelta(days=1), "cierra": ahora + timedelta(days=8)},
    )
    if request.method == "POST" and formulario.is_valid():
        datos = {campo: formulario.cleaned_data[campo] for campo in FormularioDeConsulta.Meta.fields}
        try:
            consulta = servicios.crear(
                usuario, grupo, datos, formulario.cleaned_data["visibilidad"], formulario.cleaned_data["visibilidad_resultados"],
                ancla=ancla if elemento else (None, None),
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("consultas:consulta", consulta.pk)
    directa = grupo.pk in {g.pk for g in grupos_donde_puede(usuario, "consultas.crear")}
    return render(request, "consultas/nueva.html", {"formulario": formulario, "grupos": grupos, "grupo": grupo, "elemento": elemento, "directa": directa})


# Ficha de una consulta. Mientras se prepara, quien la creó le pone y quita preguntas. Abierta, quien vota ve
# el formulario (con el aviso de si se puede cambiar el voto). Cuando toca, los resultados en barras (y el
# desglose por grupos con 10 votos o más). Si su cierre ha pasado, se da por cerrada al abrirla. Unas 10
# consultas.
#   - POST «accion»: «pregunta» (FormularioDePregunta), «quitar» (con «pregunta»), «apoyos» (con
#     «justificacion»: pedir apoyos si la propuso un miembro) o «votar» (las respuestas, «p<número>»).
def consulta(request, pk):
    usuario = request.user
    consulta = get_object_or_404(Consulta.objects.select_related("grupo"), pk=pk)
    if not servicios.ve(usuario, consulta):
        raise SinPermiso("Esta consulta no es para ti.")
    if consulta.estado == Consulta.ACEPTADA and consulta.cerrada_el is None and timezone.now() >= consulta.cierra:
        servicios.cerrar(consulta)
        consulta.refresh_from_db()
    preguntas = list(consulta.preguntas.prefetch_related("respuestas"))
    accion = request.POST.get("accion") if request.method == "POST" else None
    nueva = FormularioDePregunta(request.POST if accion == "pregunta" else None)
    error = ""
    try:
        if accion == "pregunta" and nueva.is_valid():
            datos = nueva.cleaned_data
            servicios.anadir_pregunta(usuario, consulta, datos["texto"], datos["tipo"], datos["documentacion"], datos["respuestas"].splitlines())
            return redirect("consultas:consulta", consulta.pk)
        if accion == "quitar":
            servicios.quitar_pregunta(usuario, consulta, get_object_or_404(Pregunta, pk=request.POST.get("pregunta"), consulta=consulta))
            return redirect("consultas:consulta", consulta.pk)
        if accion == "apoyos":
            servicios.pedir_apoyos(usuario, consulta, request.POST.get("justificacion", ""))
            return redirect("consultas:consulta", consulta.pk)
        if accion == "votar":
            servicios.votar(usuario, consulta, servicios.leer_respuestas(preguntas, request.POST))
            return redirect(f"{request.path}?votado=1")
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
    for pregunta in preguntas:
        pregunta.documentacion_html = texto_a_html(pregunta.documentacion)
    ve_resultados = servicios.ve_resultados(usuario, consulta)
    contexto = {
        "consulta": consulta,
        "descripcion": texto_a_html(consulta.descripcion),
        "estado": _estado(consulta, timezone.now()),
        "preguntas": preguntas,
        "prepara": consulta.creador_id == usuario.pk and servicios.en_preparacion(consulta),
        "nueva": nueva,
        "vota": servicios.abierta(consulta) and puede_ver(usuario, consulta.audiencia_id),
        "ha_votado": servicios.ha_votado(usuario, consulta),
        "recien_votado": "votado" in request.GET,
        "resultados": servicios.resultados(consulta, preguntas) if ve_resultados else None,
        "ancla": buscar_ancla(consulta.ancla_tipo, consulta.ancla_id) if consulta.ancla_tipo else None,
        "error": error,
        "abrir": accion,
    }
    return render(request, "consultas/consulta.html", contexto)
