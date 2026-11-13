"""
Pantallas de la sección «Calendario»: el calendario (la isla de FullCalendar, con las fechas en JSON y
mover arrastrando), los recordatorios (lista, apuntar uno, ficha con editar y borrar) y la suscripción
.ics (la dirección secreta, cambiarla y el propio fichero .ics, que se pide sin sesión).
"""

from datetime import datetime, time, timedelta

from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_POST

from permisos.servicios import SinPermiso, puede

from . import ics as formato_ics
from . import servicios
from .formularios import FormularioDeRecordatorio
from .models import ClaveDeCalendario, Recordatorio

# Lo más largo que se puede pedir de una vez al calendario (un año y algo: la vista de lista anual).
MAXIMO_DE_DIAS = 400
# Cuántos recordatorios se muestran como mucho en la lista.
MAXIMO = 100


# ── Fechas ───────────────────────────────────────────────────────────────────────────────────────────


# Convierte el texto de una fecha que manda FullCalendar en una fecha con hora y zona horaria. Entiende
# «2026-11-20» (día entero: a las 00:00 de aquí) y «2026-11-20T18:00:00+01:00». None si no se entiende.
def _momento(texto):
    if not texto:
        return None
    momento = parse_datetime(texto)
    if momento is None:
        dia = parse_date(texto[:10])
        if dia is None:
            return None
        momento = datetime.combine(dia, time())
    return momento if timezone.is_aware(momento) else timezone.make_aware(momento)


# Día (a las 00:00 de aquí) de un momento, en texto ISO: «2026-11-20».
def _dia(momento):
    return timezone.localtime(momento).date().isoformat()


# Una fecha de calendario en el formato que entiende FullCalendar (un diccionario que se manda en JSON).
# En lo de día entero, FullCalendar quiere como final el día siguiente al último.
#   - fuente: la FuenteDeCalendario de la que sale.
#   - fecha: la FechaDeCalendario.
def _para_fullcalendar(fuente, fecha):
    if fecha.todo_el_dia:
        inicio, fin = _dia(fecha.inicio), _dia((fecha.fin or fecha.inicio) + timedelta(days=1))
    else:
        inicio = timezone.localtime(fecha.inicio).isoformat()
        fin = timezone.localtime(fecha.fin).isoformat() if fecha.fin else None
    return {
        "id": f"{fuente.codigo}:{fecha.id}",
        "fuente": fuente.codigo,
        "numero": fecha.id,
        "title": fecha.titulo,
        "start": inicio,
        "end": fin,
        "allDay": fecha.todo_el_dia,
        "url": fecha.enlace or None,
        "color": fecha.color or fuente.color,
        "categoria": fecha.categoria or fuente.nombre,
        "editable": fecha.se_puede_mover and bool(fuente.mover),
    }


# ── Calendario ───────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Calendario»: la isla de FullCalendar. Las fechas las pide ella sola a «datos». Sin consultas
# propias (solo las de la página: sesión, usuario, menú).
def calendario(request):
    return render(request, "calendario/calendario.html")


# Fechas del trozo de calendario que se ve, en JSON, para la isla. Las aporta cada módulo con su
# FuenteDeCalendario.
#   - GET «start», «end»: el trozo (los pone FullCalendar).
def datos(request):
    desde, hasta = _momento(request.GET.get("start")), _momento(request.GET.get("end"))
    if desde is None or hasta is None or hasta <= desde or hasta - desde > timedelta(days=MAXIMO_DE_DIAS):
        return JsonResponse({"error": "Fechas no válidas."}, status=400)
    fechas = [_para_fullcalendar(fuente, fecha) for fuente, fecha in servicios.fechas(request.user, desde, hasta)]
    return JsonResponse({"fechas": fechas})


# Guarda la fecha nueva de algo que se ha arrastrado en el calendario. Responde {"ok": true} o, si no se
# puede, un error 400 con {"error": "por qué"}.
#   - POST «fuente», «id», «todo_el_dia» («1» o «0»), «inicio» y «fin» (como los da FullCalendar).
@require_POST
def mover(request):
    inicio, fin = _momento(request.POST.get("inicio")), _momento(request.POST.get("fin"))
    if inicio is None or not request.POST.get("id", "").isdigit():
        return JsonResponse({"error": "Datos no válidos."}, status=400)
    if request.POST.get("todo_el_dia") == "1" and fin is not None:
        # FullCalendar da como final el día siguiente al último; aquí se guarda el último.
        fin = fin - timedelta(days=1)
        if fin <= inicio:
            fin = None
    try:
        servicios.mover(request.user, request.POST.get("fuente", ""), int(request.POST["id"]), inicio, fin)
    except ValidationError as error:
        return JsonResponse({"error": " ".join(error.messages)}, status=400)
    return JsonResponse({"ok": True})


# ── Recordatorios ────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Recordatorios»: los que ve la persona, desde ayer en adelante. Unas 4 consultas.
def recordatorios(request):
    desde = timezone.now() - timedelta(days=1)
    lista = list(
        servicios.recordatorios_visibles(request.user).filter(inicio__gte=desde, archivado__isnull=True).select_related("grupo__organizacion", "autor").order_by("inicio")[:MAXIMO]
    )
    return render(request, "calendario/recordatorios.html", {"recordatorios": lista})


# Formulario de un recordatorio, con las opciones de visibilidad que le tocan a esa persona.
#   - grupos: donde puede apuntarlo.
def _formulario(request, grupos, **kwargs):
    con_padres = any(puede(request.user, servicios.AMPLIAR, grupo=grupo) for grupo in grupos)
    datos = request.POST if request.method == "POST" else None
    return FormularioDeRecordatorio(datos, grupos=grupos, con_padres=con_padres, **kwargs)


# Pantalla «Apuntar un recordatorio». Al pulsar un hueco del calendario llega con la fecha.
#   - GET «inicio»: fecha («2026-11-20») o fecha y hora con la que empieza.
def nuevo(request):
    grupos = servicios.grupos_para_recordar(request.user)
    inicial = {}
    momento = _momento(request.GET.get("inicio"))
    if momento is not None:
        inicial = {"inicio": timezone.localtime(momento), "todo_el_dia": "T" not in request.GET["inicio"]}
    formulario = _formulario(request, grupos, initial=inicial)
    if request.method == "POST" and formulario.is_valid():
        grupo = next(grupo for grupo in grupos if grupo.pk == formulario.cleaned_data["grupo"])
        try:
            recordatorio = servicios.crear_recordatorio(
                request.user, grupo, formulario.datos_del_recordatorio(), formulario.cleaned_data["visibilidad"]
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("calendario:recordatorio", recordatorio.pk)
    return render(request, "calendario/nuevo.html", {"formulario": formulario, "sin_grupos": not grupos})


# Ficha de un recordatorio. Quien puede gestionarlo lo cambia o lo borra desde aquí.
#   - POST «accion»: «guardar» (con los datos del formulario) o «borrar».
def recordatorio(request, pk):
    usuario = request.user
    recordatorio = get_object_or_404(Recordatorio.objects.select_related("grupo__organizacion", "autor"), pk=pk)
    if not servicios.ve(usuario, recordatorio):
        raise SinPermiso("Este recordatorio no es para ti.")
    gestiona = servicios.puede_gestionar(usuario, recordatorio, ya_lo_ve=True)
    formulario = None
    if gestiona:
        formulario = _formulario(
            request, [recordatorio.grupo], instance=recordatorio,
            initial={"grupo": recordatorio.grupo_id, "visibilidad": recordatorio.visibilidad},
        )
        formulario.fields["grupo"].disabled = True
    accion = request.POST.get("accion") if request.method == "POST" else None
    if accion and not gestiona:
        raise SinPermiso("Solo quien lo apuntó o la administración del grupo pueden cambiarlo.")
    if accion == "borrar":
        servicios.borrar_recordatorio(usuario, recordatorio)
        return redirect("calendario:recordatorios")
    if accion == "guardar" and formulario.is_valid():
        try:
            servicios.editar_recordatorio(usuario, recordatorio, formulario.datos_del_recordatorio(), formulario.cleaned_data["visibilidad"])
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("calendario:recordatorio", recordatorio.pk)
    contexto = {"recordatorio": recordatorio, "formulario": formulario, "abrir": accion == "guardar"}
    return render(request, "calendario/recordatorio.html", contexto)


# ── Suscripción .ics ─────────────────────────────────────────────────────────────────────────────────


# Pantalla «Suscripción»: la dirección secreta para ver el calendario en otro programa, y el botón para
# cambiarla (la anterior deja de funcionar).
#   - POST «accion» = «cambiar».
def suscripcion(request):
    if request.method == "POST" and request.POST.get("accion") == "cambiar":
        servicios.cambiar_clave(request.user)
        return redirect("calendario:suscripcion")
    clave = servicios.clave_de(request.user)
    direccion = request.build_absolute_uri(reverse("calendario:ics", args=[clave.clave]))
    return render(request, "calendario/suscripcion.html", {"direccion": direccion, "clave": clave})


# El calendario de una persona en formato .ics, para los programas de calendario. Se pide sin sesión (los
# programas no la tienen): basta la clave secreta de la dirección. Manda desde hace 2 meses hasta dentro
# de un año. Si la clave no existe (o se cambió), 404.
#   - clave: la clave secreta.
@login_not_required
def ics(request, clave):
    fila = ClaveDeCalendario.objects.select_related("usuario").filter(clave=clave, usuario__activo=True).first()
    if fila is None:
        raise Http404("No hay ningún calendario con esa dirección.")
    ahora = timezone.now()
    fechas = servicios.fechas(fila.usuario, ahora - formato_ics.ATRAS, ahora + formato_ics.ADELANTE)
    texto = formato_ics.escribir(fechas, f"Asambleas: {fila.usuario.alias}", request.get_host(), "https" if request.is_secure() else "http")
    respuesta = HttpResponse(texto, content_type="text/calendar; charset=utf-8")
    respuesta["Content-Disposition"] = 'inline; filename="calendario.ics"'
    return respuesta
