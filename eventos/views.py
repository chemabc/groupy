"""
Pantallas de la sección «Eventos»: próximos, pasados, mis eventos, convocar (eligiendo grupo y tipo, con
los campos de la tipología), la ficha de cada evento («¿Vas a ir?», cometidos, compartir), editar y el
cartel (que solo se entrega a quien puede ver el evento).
"""

from datetime import timedelta
from urllib.parse import quote

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from audiencias.selector import clave_de, opciones
from base.registro import registro
from grupos.models import Grupo
from permisos.servicios import SinPermiso, explicar_falta, permisos_de
from solicitudes.models import Solicitud
from tipologias.models import Tipologia
from tipologias.servicios import a_json, arbol, campos_de, formulario_de

from . import servicios
from .formularios import FormularioDeEvento
from .models import Asistencia, Evento

# Cuántos eventos se muestran como mucho en cada lista.
MAXIMO = 100


# ── Listas ───────────────────────────────────────────────────────────────────────────────────────────


# Consulta base de las listas: con grupo, organización y tipología cargados.
def _base(usuario):
    return servicios.visibles(usuario).select_related("grupo__organizacion", "tipologia")


# Pantalla «Próximos»: los eventos que se ven, desde los que están en curso (empezaron hace menos de 3
# horas) hacia delante. Cuesta unas 5 consultas.
def proximos(request):
    desde = timezone.now() - timedelta(hours=3)
    lista = list(_base(request.user).filter(inicio__gte=desde).exclude(estado=Evento.PENDIENTE).order_by("inicio")[:MAXIMO])
    return render(request, "eventos/lista.html", {"eventos": lista, "vacio": "No hay eventos próximos que puedas ver."})


# Pantalla «Pasados»: los ya celebrados, del más reciente al más antiguo.
def pasados(request):
    lista = list(_base(request.user).filter(inicio__lt=timezone.now()).exclude(estado=Evento.PENDIENTE).order_by("-inicio")[:MAXIMO])
    return render(request, "eventos/lista.html", {"eventos": lista, "vacio": "Aún no hay eventos pasados."})


# Pantalla «Mis eventos»: los que ha convocado (también los pendientes de apoyos) y a los que va o quizá.
def mios(request):
    usuario = request.user
    voy = Asistencia.objects.filter(usuario=usuario).exclude(respuesta=Asistencia.NO).values("evento_id")
    lista = list(_base(usuario).filter(Q(convocante=usuario) | Q(pk__in=voy)).order_by("-inicio")[:MAXIMO])
    return render(request, "eventos/lista.html", {"eventos": lista, "vacio": "Aún no has convocado ni te has apuntado a ningún evento.", "con_convocar": True})


# ── Convocar y editar ────────────────────────────────────────────────────────────────────────────────


# Grupos donde una persona puede convocar (con «eventos.convocar»), en orden de árbol.
def _grupos_donde_convoca(usuario):
    consulta = Grupo.objects.en_orden_de_arbol().select_related("organizacion")
    if usuario.is_superuser:
        return list(consulta)
    ids = [grupo for grupo, codigos in permisos_de(usuario).grupos.items() if "eventos.convocar" in codigos]
    return list(consulta.filter(pk__in=ids))


# Pantalla «Convocar»: primero se elige el grupo y el tipo (formulario GET, que se envía solo al cambiar
# un desplegable); después, los datos del evento, quién lo ve y los campos de su tipo.
#   - GET «grupo», «tipologia».
#   - POST: los datos de FormularioDeEvento y los del formulario de la tipología (prefijo «tipo»).
def convocar(request):
    usuario = request.user
    grupos = _grupos_donde_convoca(usuario)
    if not grupos:
        raise SinPermiso(explicar_falta("eventos.convocar"))
    grupo = next((g for g in grupos if str(g.pk) == request.GET.get("grupo", "")), grupos[0])
    ramas = arbol(Tipologia.EVENTO, [grupo.organizacion_id])
    tipologia = next((r.tipologia for r in ramas if str(r.tipologia.pk) == request.GET.get("tipologia", "")), None)
    contexto = {"grupos": grupos, "grupo": grupo, "ramas": ramas, "tipologia": tipologia}
    if tipologia is not None:
        reunion = servicios.es_reunion(tipologia)
        datos = request.POST if request.method == "POST" else None
        formulario = FormularioDeEvento(datos, request.FILES or None, visibilidades=opciones(grupo), reunion=reunion)
        propios = _propios(tipologia, datos)
        if request.method == "POST" and formulario.is_valid() and propios.is_valid():
            try:
                evento = servicios.convocar(
                    usuario, grupo, tipologia, formulario.datos_del_evento(), formulario.cleaned_data["visibilidad"],
                    campos=a_json(propios.cleaned_data), justificacion=formulario.cleaned_data.get("justificacion", ""),
                )
            except ValidationError as error:
                formulario.add_error(None, error)
            else:
                return redirect("eventos:evento", evento.pk)
        contexto.update(formulario=formulario, propios=propios, reunion=reunion)
    return render(request, "eventos/convocar.html", contexto)


# Formulario con los campos propios de una tipología, con el prefijo «tipo» (sus campos se llaman
# «tipo-…»), para que no choquen con los comunes del evento.
#   - datos: lo enviado, o None.
#   - valores: los ya guardados, para editar.
def _propios(tipologia, datos, valores=None):
    formulario = formulario_de(tipologia, datos, valores)
    formulario.prefix = "tipo"
    return formulario


# Pantalla «Editar»: los mismos datos que al convocar, ya rellenos. La visibilidad de una reunión no se
# cambia (se pidieron apoyos para esa).
#   - pk: el evento.
def editar(request, pk):
    usuario = request.user
    evento = get_object_or_404(Evento.objects.select_related("grupo__organizacion", "tipologia", "audiencia"), pk=pk)
    if not servicios.puede_gestionar(usuario, evento):
        raise SinPermiso("Solo quien lo convocó o la administración del grupo pueden cambiarlo.")
    reunion = servicios.es_reunion(evento.tipologia)
    datos = request.POST if request.method == "POST" else None
    formulario = FormularioDeEvento(
        datos, request.FILES or None, instance=evento, visibilidades=opciones(evento.grupo), reunion=False,
        initial={"visibilidad": evento.visibilidad if evento.estado == Evento.PENDIENTE else clave_de(evento.audiencia, evento.grupo)},
    )
    if reunion:
        formulario.fields["visibilidad"].disabled = True
        formulario.fields["visibilidad"].help_text = "La de una reunión no se cambia: se pidieron apoyos para esa."
    propios = _propios(evento.tipologia, datos, evento.campos)
    if request.method == "POST" and formulario.is_valid() and propios.is_valid():
        try:
            servicios.editar(
                usuario, evento, formulario.datos_del_evento(), visibilidad=formulario.cleaned_data["visibilidad"], campos=a_json(propios.cleaned_data)
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("eventos:evento", evento.pk)
    contexto = {"evento": evento, "formulario": formulario, "propios": propios, "tipologia": evento.tipologia}
    return render(request, "eventos/editar.html", contexto)


# ── Ficha ────────────────────────────────────────────────────────────────────────────────────────────


# Pantalla de un evento: sus datos y los de su tipo, el cartel, «¿Vas a ir?» con el recuento (y los alias
# para quien convoca o tiene un cometido), los cometidos (apuntarse o quitarse) y los botones para
# compartir. Cuesta unas 9 consultas.
#   - pk: el evento.
#   - POST «accion»: si, no, no_se (asistencia), apuntar o desapuntar (con «cometido» y, para otra persona,
#     «persona»), o cancelar.
def evento(request, pk):
    usuario = request.user
    evento = get_object_or_404(Evento.objects.select_related("grupo__organizacion", "tipologia", "audiencia", "convocante", "lugar"), pk=pk)
    if not servicios.ve(usuario, evento):
        raise SinPermiso("Este evento no es para ti: solo lo ven las personas a las que llega.")
    accion = request.POST.get("accion") if request.method == "POST" else None
    error = ""
    try:
        if accion in dict(Asistencia.RESPUESTAS):
            servicios.responder(usuario, evento, accion)
        elif accion in ("apuntar", "desapuntar"):
            codigo = request.POST.get("cometido", "")
            if codigo not in registro.cometidos or not codigo.startswith("eventos."):
                raise ValidationError("Cometido desconocido.")
            persona = usuario
            if request.POST.get("persona"):
                persona = get_object_or_404(type(usuario), pk=request.POST["persona"])
            (servicios.apuntar if accion == "apuntar" else servicios.desapuntar)(usuario, evento, persona, codigo)
        elif accion == "cancelar":
            servicios.cancelar(usuario, evento)
        if accion:
            return redirect("eventos:evento", evento.pk)
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
    de_cometidos = servicios.cometidos(evento)
    ve_quien = servicios.ve_quien_va(usuario, evento, de_cometidos)
    mi_respuesta = Asistencia.objects.filter(evento=evento, usuario=usuario).values_list("respuesta", flat=True).first()
    contexto = {
        "evento": evento,
        "error": error,
        "campos": [(campo.nombre, evento.campos.get(campo.clave)) for campo in campos_de(evento.tipologia) if evento.campos.get(campo.clave) not in (None, "")],
        "recuento": servicios.recuento(evento),
        "mi_respuesta": mi_respuesta,
        "respuestas": Asistencia.RESPUESTAS,
        "quien_va": list(evento.asistencias.exclude(respuesta=Asistencia.NO).select_related("usuario").order_by("respuesta", "usuario__alias")) if ve_quien else None,
        "cometidos": _cometidos_para_pintar(de_cometidos, usuario),
        "gestiona": servicios.puede_gestionar(usuario, evento),
        "compartir": _enlaces_para_compartir(request, evento),
        "solicitud": _solicitud_pendiente(evento),
    }
    return render(request, "eventos/evento.html", contexto)


# Los cometidos de los eventos (declarados en el contrato), cada uno con quién lo tiene y si quien mira
# está apuntado.
def _cometidos_para_pintar(de_cometidos, usuario):
    filas = []
    for codigo, cometido in registro.cometidos.items():
        if not codigo.startswith("eventos."):
            continue
        quienes = [c.usuario for c in de_cometidos if c.codigo == codigo]
        filas.append({"codigo": codigo, "nombre": cometido.nombre, "descripcion": cometido.descripcion, "quienes": quienes, "estoy": usuario in quienes})
    return filas


# Enlaces para compartir el evento en las redes, con su texto para las redes (o el título) y su dirección.
def _enlaces_para_compartir(request, evento):
    texto = evento.texto_para_redes or f"{evento.titulo} — {timezone.localtime(evento.inicio):%d/%m/%Y %H:%M}"
    url = request.build_absolute_uri()
    juntos = quote(f"{texto} {url}")
    return [
        ("Telegram", f"https://t.me/share/url?url={quote(url)}&text={quote(texto)}"),
        ("WhatsApp", f"https://wa.me/?text={juntos}"),
        ("Mastodon", f"https://mastodon.social/share?text={juntos}"),
        ("Bluesky", f"https://bsky.app/intent/compose?text={juntos}"),
    ]


# La solicitud de apoyos de una reunión pendiente (para enlazarla), o None.
def _solicitud_pendiente(evento):
    if evento.estado != Evento.PENDIENTE:
        return None
    return Solicitud.objects.filter(tipo="eventos.reunion", datos__evento_id=evento.pk).order_by("-pk").first()


# El cartel de un evento: se entrega solo a quien puede ver el evento (no hay dirección pública).
#   - pk: el evento.
def cartel(request, pk):
    evento = get_object_or_404(Evento.objects.select_related("audiencia"), pk=pk)
    if not evento.cartel or not servicios.ve(request.user, evento):
        raise Http404("No hay cartel.")
    return FileResponse(evento.cartel.open("rb"))
