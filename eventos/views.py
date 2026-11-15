"""
Pantallas de la sección «Eventos»: próximos, pasados, mis eventos, convocar (eligiendo grupo y tipo, con
los campos de la tipología), la ficha de cada evento («¿Vas a ir?», cometidos, compartir), editar y el
cartel (que solo se entrega a quien puede ver el evento).
"""

from datetime import timedelta
from urllib.parse import quote

from django.core.exceptions import ValidationError
from django.db.models import Count, Min, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from audiencias.selector import clave_de, opciones
from base.registro import registro
from base.tablas import Columna, Filtro, FuenteDeLista, Tabla
from grupos.models import Grupo
from permisos.servicios import SinPermiso, explicar_falta, permisos_de
from solicitudes.models import Solicitud
from tipologias.models import Tipologia
from tipologias.servicios import a_json, arbol, campos_de, formulario_de

from . import series as servicios_de_series
from . import servicios
from .formularios import FormularioDeEvento, FormularioDeSerie
from .models import Asistencia, Evento, Serie

# Cuántos eventos se muestran como mucho en cada lista.
MAXIMO = 100


# ── Listas ───────────────────────────────────────────────────────────────────────────────────────────


# Consulta base de las listas: sin lo archivado (está en «Archivo»), con grupo, organización y tipología
# cargados y cuántas personas han dicho que van («van»).
#   - consulta: de qué eventos se parte (los que ve la persona, o los de los grupos que administra).
def _base(consulta):
    return consulta.filter(archivado__isnull=True).select_related("grupo__organizacion", "tipologia").annotate(
        van=Count("asistencias", filter=Q(asistencias__respuesta=Asistencia.SI))
    )


# Desde cuándo un evento cuenta como «próximo»: los que empezaron hace menos de 3 horas siguen en curso.
def _desde():
    return timezone.now() - timedelta(hours=3)


# Apoyos de las reuniones que los esperan, por evento: {id del evento: «1/2»}. Una consulta.
def _apoyos(eventos):
    pendientes = [evento.pk for evento in eventos if evento.estado == Evento.PENDIENTE]
    if not pendientes:
        return {}
    solicitudes = Solicitud.objects.filter(tipo="eventos.reunion", estado=Solicitud.PENDIENTE, datos__evento_id__in=pendientes)
    return {solicitud.datos["evento_id"]: f"{solicitud.apoyos}/{solicitud.apoyos_necesarios}" for solicitud in solicitudes}


# Tabla filtrable de una lista de eventos (la común: base/tablas.py), con fecha y hora, título (enlace a su
# ficha), tipo, grupo, estado, cuántos van y, si se pide, los apoyos y el papel de quien mira. Se filtra por
# tipo, grupo, estado y papel; se busca por título, grupo, organización y tipo; se ordena por cualquier
# columna. Devuelve la respuesta (la página entera o, si la pide la propia tabla, solo sus filas).
#   - eventos: la lista ya leída (como mucho MAXIMO).
#   - identificador: nombre de la tabla en la página.
#   - contexto: lo que necesita la plantilla además de la tabla (vacio, con_convocar…).
#   - con_apoyos: si sale la columna de apoyos (para quien administra).
#   - papeles: {id del evento: «Convoco», «Voy» o «Quizá»} para la columna «Mi papel», o None si no sale.
def _tabla(request, eventos, identificador, contexto, con_apoyos=False, papeles=None):
    apoyos = _apoyos(eventos) if con_apoyos else {}
    filas = []
    for evento in eventos:
        fila = {
            "pk": evento.pk, "inicio": evento.inicio, "titulo": evento.titulo, "tipo": evento.tipologia.nombre, "grupo": evento.grupo.nombre,
            "organizacion": evento.grupo.organizacion.nombre, "estado": evento.get_estado_display(), "van": evento.van,
        }
        if con_apoyos:
            fila["apoyos"] = apoyos.get(evento.pk, "—")
        if papeles is not None:
            fila["papel"] = papeles.get(evento.pk, "")
        filas.append(fila)
    columnas = [
        Columna("inicio", "Fecha"), Columna("titulo", "Evento", enlace="eventos:evento"), Columna("tipo", "Tipo"), Columna("grupo", "Grupo"),
        Columna("estado", "Estado"), Columna("van", "Van", filtrable=False),
    ]
    if con_apoyos:
        columnas.append(Columna("apoyos", "Apoyos", filtrable=False))
    if papeles is not None:
        columnas.append(Columna("papel", "Mi papel"))
    distintos = lambda campo: tuple((valor, valor) for valor in sorted({fila[campo] for fila in filas}))
    filtros = [Filtro("tipo", "Tipo", distintos("tipo")), Filtro("grupo", "Grupo", distintos("grupo")), Filtro("estado", "Estado", distintos("estado"))]
    if papeles is not None:
        filtros.append(Filtro("papel", "Mi papel", distintos("papel")))
    tabla = Tabla(request, identificador=identificador, columnas=columnas, fuente=FuenteDeLista(filas, campos_de_busqueda=["titulo", "grupo", "organizacion", "tipo"]), filtros=filtros)
    plantilla = tabla.plantilla_parcial()
    if plantilla:
        return render(request, plantilla, {"tabla": tabla})
    return render(request, "eventos/lista.html", {"tabla": tabla, "hay": bool(filas), "vacio": "", "con_convocar": False, **contexto})


# Pantalla «Eventos de mis grupos → Próximos»: los eventos que se ven, desde los que están en curso hacia
# delante. Unas 5 consultas.
def proximos(request):
    lista = list(_base(servicios.visibles(request.user)).filter(inicio__gte=_desde()).exclude(estado=Evento.PENDIENTE).order_by("inicio")[:MAXIMO])
    return _tabla(request, lista, "eventos", {"vacio": "No hay eventos próximos que puedas ver."})


# Pantalla «Eventos de mis grupos → Pasados»: los ya celebrados, del más reciente al más antiguo.
def pasados(request):
    lista = list(_base(servicios.visibles(request.user)).filter(inicio__lt=_desde()).exclude(estado=Evento.PENDIENTE).order_by("-inicio")[:MAXIMO])
    return _tabla(request, lista, "eventos", {"vacio": "Aún no hay eventos pasados."})


# Papel de quien mira en cada evento: «Convoco» (los que convocó) o su respuesta a «¿Vas a ir?» (Voy,
# Quizá). Una consulta.
def _papeles(usuario, eventos):
    nombres = {Asistencia.SI: "Voy", Asistencia.NO_SE: "Quizá"}
    respuestas = Asistencia.objects.filter(usuario=usuario, evento__in=[e.pk for e in eventos]).exclude(respuesta=Asistencia.NO)
    papeles = {evento_id: nombres[respuesta] for evento_id, respuesta in respuestas.values_list("evento_id", "respuesta")}
    papeles.update({evento.pk: "Convoco" for evento in eventos if evento.convocante_id == usuario.pk})
    return papeles


# Pantallas «Mis eventos → Próximos» y «→ Pasados»: los que ha convocado (también los que esperan apoyos)
# y a los que va o quizá, con su papel en cada uno. Unas 6 consultas.
#   - pasados: si son los pasados (del más reciente al más antiguo) o los próximos.
def mios(request, pasados=False):
    usuario = request.user
    voy = Asistencia.objects.filter(usuario=usuario).exclude(respuesta=Asistencia.NO).values("evento_id")
    consulta = _base(servicios.visibles(usuario)).filter(Q(convocante=usuario) | Q(pk__in=voy))
    consulta = consulta.filter(inicio__lt=_desde()).order_by("-inicio") if pasados else consulta.filter(inicio__gte=_desde()).order_by("inicio")
    lista = list(consulta[:MAXIMO])
    vacio = "No tienes eventos pasados." if pasados else "No has convocado ni te has apuntado a ningún evento próximo."
    return _tabla(request, lista, "mios", {"vacio": vacio, "con_convocar": True}, con_apoyos=True, papeles=_papeles(usuario, lista))


# Lo que enseña cada pestaña de «Administrar → Eventos de mis grupos»: (filtro de la consulta, orden, texto
# si no hay ninguno).
ADMINISTRADOS = {
    "proximos": (lambda c: c.filter(estado=Evento.CONVOCADO, inicio__gte=_desde()), "inicio", "Tus grupos no tienen eventos próximos."),
    "pendientes": (lambda c: c.filter(estado=Evento.PENDIENTE), "inicio", "Ninguna reunión de tus grupos espera apoyos."),
    "pasados": (lambda c: c.filter(estado=Evento.CONVOCADO, inicio__lt=_desde()), "-inicio", "Tus grupos aún no tienen eventos pasados."),
    "cancelados": (lambda c: c.filter(estado=Evento.CANCELADO), "-inicio", "Tus grupos no tienen eventos cancelados."),
}


# Pantalla «Administrar → Eventos y talentos → Eventos de mis grupos»: los eventos de los grupos que
# administra quien mira y de sus subgrupos, en cuatro pestañas (próximos, los que esperan apoyos, pasados y
# cancelados), con los apoyos de los que los esperan. Desde la ficha de cada uno puede editarlo o
# cancelarlo; cuántos van sí, pero no quiénes (eso es de quien convoca y de los cometidos). Unas 5 consultas.
#   - cual: la pestaña («proximos», «pendientes», «pasados» o «cancelados»; viene de eventos/urls.py).
def administrados(request, cual):
    filtrar, orden, vacio = ADMINISTRADOS[cual]
    if not request.user.is_superuser and not any("grupos.ver_arbol" in codigos for codigos in permisos_de(request.user).grupos.values()):
        raise SinPermiso(explicar_falta("grupos.ver_arbol"))
    lista = list(filtrar(_base(servicios.de_grupos_administrados(request.user))).order_by(orden)[:MAXIMO])
    return _tabla(request, lista, "administrados", {"vacio": vacio}, con_apoyos=cual == "pendientes")


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
        formulario = FormularioDeEvento(datos, request.FILES or None, visibilidades=opciones(grupo), reunion=reunion, con_repeticion=True)
        propios = _propios(tipologia, datos)
        if request.method == "POST" and formulario.is_valid() and propios.is_valid():
            limpios = formulario.cleaned_data
            comunes = {
                "visibilidad": limpios["visibilidad"], "campos": a_json(propios.cleaned_data), "justificacion": limpios.get("justificacion", ""),
            }
            try:
                if limpios["repetir"]:
                    datos_de_serie = {**formulario.datos_del_evento(), "frecuencia": limpios["repetir"], "hasta": limpios["repetir_hasta"]}
                    serie = servicios_de_series.crear_serie(usuario, grupo, tipologia, datos_de_serie, **comunes)
                    return redirect("eventos:serie", serie.pk)
                evento = servicios.convocar(usuario, grupo, tipologia, formulario.datos_del_evento(), **comunes)
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
    evento = get_object_or_404(Evento.objects.select_related("grupo__organizacion", "tipologia", "audiencia", "convocante", "lugar", "serie"), pk=pk)
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
        "serie": servicios_de_series.describir(evento.serie) if evento.serie else "",
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


# ── Series ───────────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Series»: las series que la persona puede gestionar (las que ha convocado y las de los grupos
# que administra; todas, si es superadmin), con cuándo se repiten y su próxima vez. Unas 4 consultas.
def series(request):
    usuario = request.user
    consulta = Serie.objects.select_related("grupo__organizacion", "tipologia").order_by("estado", "titulo")
    if not usuario.is_superuser:
        administra = [grupo for grupo, codigos in permisos_de(usuario).grupos.items() if "grupos.editar_grupo" in codigos]
        consulta = consulta.filter(Q(convocante=usuario) | Q(grupo_id__in=administra))
    lista = list(consulta[:MAXIMO])
    proximas = dict(
        Evento.objects.filter(serie__in=lista, inicio__gte=timezone.now()).exclude(estado=Evento.CANCELADO)
        .values("serie_id").annotate(primera=Min("inicio")).values_list("serie_id", "primera")
    )
    filas = [{"serie": serie, "regla": servicios_de_series.describir(serie), "proxima": proximas.get(serie.pk)} for serie in lista]
    return render(request, "eventos/series.html", {"filas": filas})


# Ficha de una serie: cuándo se repite, sus próximas veces (marcando las cambiadas a mano) y, para quien
# la gestiona, cambiarla (también la regla) o terminarla.
#   - POST «accion»: «guardar» (con los datos del formulario) o «terminar».
def serie(request, pk):
    usuario = request.user
    serie = get_object_or_404(Serie.objects.select_related("grupo__organizacion", "tipologia", "convocante"), pk=pk)
    if not servicios_de_series.ve(usuario, serie):
        raise SinPermiso("Esta serie no es para ti: solo la ven las personas a las que llega.")
    gestiona = servicios_de_series.puede_gestionar(usuario, serie)
    accion = request.POST.get("accion") if request.method == "POST" else None
    if accion and not gestiona:
        raise SinPermiso("Solo quien la convocó o la administración del grupo pueden cambiarla.")
    formulario = propios = None
    if gestiona and serie.estado != Serie.TERMINADA:
        reunion = servicios.es_reunion(serie.tipologia)
        datos = request.POST if accion == "guardar" else None
        formulario = FormularioDeSerie(
            datos, request.FILES or None, instance=serie, visibilidades=opciones(serie.grupo), reunion=False,
            initial={"visibilidad": serie.visibilidad},
        )
        if reunion:
            formulario.fields["visibilidad"].disabled = True
            formulario.fields["visibilidad"].help_text = "La de una serie de reuniones no se cambia: se pidieron apoyos para esa."
        propios = _propios(serie.tipologia, datos, serie.campos)
    if accion == "terminar":
        servicios_de_series.terminar_serie(usuario, serie)
        return redirect("eventos:serie", serie.pk)
    if accion == "guardar" and formulario.is_valid() and propios.is_valid():
        try:
            servicios_de_series.editar_serie(
                usuario, serie, formulario.datos_del_evento(), visibilidad=formulario.cleaned_data["visibilidad"], campos=a_json(propios.cleaned_data)
            )
        except ValidationError as error_de_servicio:
            formulario.add_error(None, error_de_servicio)
        else:
            return redirect("eventos:serie", serie.pk)
    veces = list(serie.veces.filter(inicio__gte=timezone.now() - timedelta(hours=3)).order_by("inicio")[:30])
    solicitud = None
    if serie.estado == Serie.PENDIENTE:
        solicitud = Solicitud.objects.filter(tipo="eventos.serie_de_reuniones", datos__serie_id=serie.pk).order_by("-pk").first()
    contexto = {
        "serie": serie, "regla": servicios_de_series.describir(serie), "veces": veces, "gestiona": gestiona,
        "formulario": formulario, "propios": propios, "abrir": accion == "guardar", "solicitud": solicitud,
    }
    return render(request, "eventos/serie.html", contexto)


# El cartel de un evento: se entrega solo a quien puede ver el evento (no hay dirección pública).
#   - pk: el evento.
def cartel(request, pk):
    evento = get_object_or_404(Evento.objects.select_related("audiencia"), pk=pk)
    if not evento.cartel or not servicios.ve(request.user, evento):
        raise Http404("No hay cartel.")
    return FileResponse(evento.cartel.open("rb"))
