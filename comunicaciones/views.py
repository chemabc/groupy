"""
Pantallas de la sección «Comunicaciones» (ver docs/diseno.md, apartado 17):

- Notificaciones: la bandeja de cada persona, con filtro por origen. Cada notificación se abre (y queda
  vista), se marca como vista o se borra con su papelera; arriba, «Marcar todas como vistas» y «Limpiar
  las vistas».
- Preferencias: qué tipos de aviso quiere recibir cada persona.
- Conversaciones con la administración: las de cada persona y las de las administraciones que atiende.
- Avisos de la administración: enviar avisos a grupos o personas, y ver los enviados.
- «Plataforma → Catálogos comunes → Niveles de aviso»: los niveles (Información, Atención, Problema…) con su color.

Cada persona solo ve y toca sus notificaciones y sus conversaciones, y las de las administraciones que
atiende (comunicaciones/administraciones.py).
"""

from django.core.exceptions import ValidationError
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from base.contrato import ORIGENES_DE_AVISO
from base.registro import registro
from grupos.models import Grupo
from permisos.decoradores import requiere_permiso
from permisos.servicios import SinPermiso, explicar_falta

from . import servicios
from .administraciones import (
    Buzon,
    administraciones_de,
    administraciones_para_escribir,
    buscar,
    filtro_de_lo_que_atiende,
    grupos_que_alcanza,
    puede_atender,
)
from .formularios import FormularioDeAviso, FormularioDeConversacion, FormularioDeMensaje, FormularioDeNivel
from .models import AvisoDeAdministracion, Conversacion, NivelDeAviso, Notificacion

# Cuántas notificaciones se muestran de entrada; «Mostrar más» suma otras tantas.
POR_PAGINA = 50


# Pantalla «Notificaciones». Cuesta 4 consultas, sea cual sea el número de notificaciones.
#   - GET «origen»: muestra solo las de ese origen. «cuantas»: cuántas se muestran.
#   - POST «accion»: vista (con «notificacion»), borrar (con «notificacion»), todas_vistas o limpiar.
def notificaciones(request):
    usuario = request.user
    origen = request.GET.get("origen", "")
    origen = origen if origen in dict(ORIGENES_DE_AVISO) else ""
    accion = request.POST.get("accion") if request.method == "POST" else None
    if accion:
        if accion == "vista":
            servicios.marcar_vistas(usuario, [request.POST.get("notificacion")])
        elif accion == "borrar":
            servicios.borrar(usuario, request.POST.get("notificacion"))
        elif accion == "todas_vistas":
            servicios.marcar_vistas(usuario)
        elif accion == "limpiar":
            servicios.limpiar_vistas(usuario)
        return redirect(f"{reverse('comunicaciones:notificaciones')}?origen={origen}" if origen else "comunicaciones:notificaciones")
    cuantas = request.GET.get("cuantas", "")
    cuantas = max(POR_PAGINA, min(int(cuantas), 1000)) if cuantas.isdigit() else POR_PAGINA
    # Recuento por origen (todas y sin ver), en una sola consulta, para las pestañas de las bandejas.
    recuentos = {
        fila["origen"]: fila
        for fila in Notificacion.objects.filter(usuario=usuario)
        .values("origen")
        .annotate(total=Count("pk"), sin_ver=Count("pk", filter=Q(vista_el__isnull=True)))
        .order_by()
    }
    bandejas = [
        {"codigo": codigo, "nombre": nombre, "total": recuentos[codigo]["total"], "sin_ver": recuentos[codigo]["sin_ver"]}
        for codigo, nombre in ORIGENES_DE_AVISO
        if codigo in recuentos
    ]
    lista = Notificacion.objects.filter(usuario=usuario).select_related("aviso__nivel")
    if origen:
        lista = lista.filter(origen=origen)
    filas = list(lista[: cuantas + 1])
    contexto = {
        "bandejas": bandejas,
        "origen": origen,
        "total": sum(bandeja["total"] for bandeja in bandejas),
        "sin_ver_total": sum(bandeja["sin_ver"] for bandeja in bandejas),
        "hay_vistas": any(bandeja["total"] > bandeja["sin_ver"] for bandeja in bandejas),
        "notificaciones": filas[:cuantas],
        "mas": cuantas + POR_PAGINA if len(filas) > cuantas else None,
    }
    return render(request, "comunicaciones/notificaciones.html", contexto)


# Abre una notificación: la marca como vista y lleva a su enlace (o a la bandeja, si no tiene). Solo
# lleva a direcciones de la propia aplicación.
#   - pk: número de la notificación (de quien la abre).
def abrir(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk, usuario=request.user)
    servicios.marcar_vistas(request.user, [notificacion.pk])
    seguro = url_has_allowed_host_and_scheme(notificacion.enlace, allowed_hosts={request.get_host()})
    return redirect(notificacion.enlace if notificacion.enlace and seguro else "comunicaciones:notificaciones")


# Pantalla «Preferencias»: los tipos de aviso de todos los módulos, agrupados por origen, con una casilla
# para recibirlos o no. Cuesta 3 consultas.
#   - POST: la lista «activados» con los códigos marcados.
def preferencias(request):
    aviso = ""
    if request.method == "POST":
        servicios.poner_preferencias(request.user, request.POST.getlist("activados"))
        aviso = "Preferencias guardadas."
    apagados = servicios.desactivados(request.user)
    grupos = []
    for codigo, nombre in ORIGENES_DE_AVISO:
        tipos = [
            {"codigo": tipo.codigo, "nombre": tipo.nombre, "activado": tipo.codigo not in apagados}
            for tipo in sorted(registro.avisos.values(), key=lambda tipo: tipo.nombre)
            if tipo.origen == codigo
        ]
        if tipos:
            grupos.append({"nombre": nombre, "tipos": tipos})
    return render(request, "comunicaciones/preferencias.html", {"grupos": grupos, "aviso": aviso})


# ── Avisos de la administración ──────────────────────────────────────────────────────────────────────


# Pantalla «Avisos de la administración»: el formulario para avisar, en nombre de una de las
# administraciones de quien escribe, y los avisos enviados por las administraciones que atiende.
# Cuesta unas 8 consultas.
#   - POST: los datos de FormularioDeAviso.
def avisos(request):
    usuario = request.user
    buzones = administraciones_de(usuario)
    if not buzones:
        raise SinPermiso(explicar_falta("comunicaciones.avisar"))
    alcanzables = set().union(*(grupos_que_alcanza(buzon) for buzon in buzones))
    grupos = [
        (grupo.pk, f"{grupo.organizacion.nombre} › {grupo.camino}")
        for grupo in Grupo.objects.en_orden_de_arbol().select_related("organizacion").filter(pk__in=alcanzables)
    ]
    formulario = FormularioDeAviso(
        request.POST or None, administraciones=[(buzon.clave, buzon.nombre) for buzon in buzones], grupos=grupos
    )
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            servicios.enviar_aviso(
                usuario, buscar(buzones, datos["administracion"]), datos["nivel"], datos["asunto"], datos["texto"],
                grupos=list(Grupo.objects.select_related("organizacion").filter(pk__in=datos["grupos"])),
                personas=datos["personas"], permite_responder=datos["permite_responder"],
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("comunicaciones:avisos")
    enviados = AvisoDeAdministracion.objects.select_related("nivel", "autor", "grupo__organizacion", "organizacion")
    filtro = filtro_de_lo_que_atiende(usuario)
    if filtro is not None:
        enviados = enviados.filter(filtro)
    contexto = {"formulario": formulario, "enviados": list(enviados[:100])}
    return render(request, "comunicaciones/avisos.html", contexto)


# Pantalla de un aviso de la administración: su texto completo, con el color de su nivel, y el botón
# para responder si se permite. La ven quienes lo recibieron y quienes atienden esa administración.
#   - pk: número del aviso.
def aviso(request, pk):
    usuario = request.user
    aviso = get_object_or_404(AvisoDeAdministracion.objects.select_related("nivel", "autor", "grupo__organizacion", "organizacion"), pk=pk)
    recibido = aviso.notificaciones.filter(usuario=usuario).first()
    atiende = puede_atender(usuario, aviso.grupo_id, aviso.organizacion_id, aviso.grupo.organizacion_id if aviso.grupo_id else None)
    if recibido is None and not atiende:
        raise SinPermiso("Este aviso solo lo ven quienes lo recibieron y la administración que lo envió.")
    if recibido is not None and recibido.vista_el is None:
        servicios.marcar_vistas(usuario, [recibido.pk])
    contexto = {"aviso": aviso, "atiende": atiende, "puede_responder": aviso.permite_responder and recibido is not None}
    return render(request, "comunicaciones/aviso.html", contexto)


# ── Conversaciones con la administración ─────────────────────────────────────────────────────────────


# Pantalla «Comunicaciones → Conversaciones → Con la administración»: las conversaciones de quien mira con
# las administraciones (primero las que tienen algo sin leer). Lo que llega a las administraciones que
# atiende está aparte, en «Administrar» (atendidas). Cuesta 2 consultas.
#   - GET «estado»: muestra solo las de ese estado.
def conversaciones(request):
    return _conversaciones(request, como_admin=False)


# Pantalla «Administrar → Buzón de la administración → Conversaciones que atiendo»: lo que llega a las
# administraciones que atiende quien mira (primero lo que tiene algo sin leer). Cuesta unas 4 consultas.
#   - GET «estado»: muestra solo las de ese estado.
def atendidas(request):
    return _conversaciones(request, como_admin=True)


# Lo común a las dos pantallas de conversaciones.
#   - como_admin: si son las que atiende (True) o las suyas (False).
def _conversaciones(request, como_admin):
    usuario = request.user
    estado = request.GET.get("estado", "")
    estado = estado if estado in dict(Conversacion.ESTADOS) else ""
    base = Conversacion.objects.select_related("persona", "grupo__organizacion", "organizacion")
    if estado:
        base = base.filter(estado=estado)
    mias, atiende, filtro = [], [], None
    if como_admin:
        filtro = filtro_de_lo_que_atiende(usuario)
        atiende = base.exclude(persona=usuario).order_by("-pendiente_admins", "-actualizada")
        atiende = list((atiende if filtro is None else atiende.filter(filtro))[:200])
    else:
        mias = list(base.filter(persona=usuario).order_by("-pendiente_persona", "-actualizada"))
    contexto = {
        "como_admin": como_admin,
        "mias": mias,
        "atiende": atiende,
        "estado": estado,
        "estados": Conversacion.ESTADOS,
    }
    return render(request, "comunicaciones/conversaciones.html", contexto)


# Pantalla «Escribir a la administración»: elegir a cuál y escribir el primer mensaje. Con «?aviso=<id>»
# (desde un aviso que se puede responder) se elige sola la administración del aviso; con
# «?administracion=<clave>&asunto=<texto>», esa administración y ese asunto.
#   - POST: los datos de FormularioDeConversacion.
def nueva_conversacion(request):
    usuario = request.user
    buzones = administraciones_para_escribir(usuario)
    aviso = None
    numero = request.GET.get("aviso", "")
    if numero.isdigit():
        aviso = (
            AvisoDeAdministracion.objects.select_related("grupo__organizacion", "organizacion")
            .filter(pk=numero, permite_responder=True, notificaciones__usuario=usuario)
            .first()
        )
    # Con «?administracion=g5&asunto=…» (por ejemplo, «Tengo dudas» en una petición de talentos) se
    # elige esa administración y se escribe el asunto.
    inicial = {"administracion": request.GET.get("administracion", ""), "asunto": request.GET.get("asunto", "")[:120]}
    if aviso is not None:
        del_aviso = Buzon(grupo=aviso.grupo, organizacion=aviso.organizacion)
        if buscar(buzones, del_aviso.clave) is None:
            buzones.insert(0, del_aviso)
        inicial = {"administracion": del_aviso.clave, "asunto": f"Re: {aviso.asunto}"[:120]}
    formulario = FormularioDeConversacion(
        request.POST or None, initial=inicial, administraciones=[(buzon.clave, buzon.nombre) for buzon in buzones]
    )
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        conversacion = servicios.abrir_conversacion(
            usuario, buscar(buzones, datos["administracion"]), datos["asunto"], datos["texto"], aviso=aviso
        )
        return redirect("comunicaciones:conversacion", conversacion.pk)
    return render(request, "comunicaciones/nueva_conversacion.html", {"formulario": formulario, "aviso": aviso})


# Pantalla de una conversación: sus mensajes, el formulario para responder y, para quien la atiende, el
# estado. Mientras está abierta, la lista de mensajes se vuelve a pedir cada 10 segundos (htmx, con
# «?fragmento=mensajes»). Abrirla la marca como leída por quien mira.
#   - pk: número de la conversación.
#   - POST «accion»: responder (con «texto») o estado (con «estado»).
def conversacion(request, pk):
    usuario = request.user
    conversacion = get_object_or_404(Conversacion.objects.select_related("persona", "grupo__organizacion", "organizacion", "aviso"), pk=pk)
    es_persona = conversacion.persona_id == usuario.pk
    atiende = not es_persona and puede_atender(
        usuario, conversacion.grupo_id, conversacion.organizacion_id, conversacion.grupo.organizacion_id if conversacion.grupo_id else None
    )
    if not es_persona and not atiende:
        raise SinPermiso("Esta conversación solo la ven la persona que escribe y quienes atienden esa administración.")
    accion = request.POST.get("accion") if request.method == "POST" else None
    respuesta = FormularioDeMensaje(request.POST if accion == "responder" else None)
    if accion == "responder" and respuesta.is_valid():
        servicios.escribir(conversacion, usuario, respuesta.cleaned_data["texto"], como_admin=atiende)
        return redirect("comunicaciones:conversacion", conversacion.pk)
    if accion == "estado":
        if not atiende:
            raise SinPermiso("El estado de la conversación lo cambian los admins que la atienden.")
        servicios.cambiar_estado(conversacion, request.POST.get("estado", ""))
        return redirect("comunicaciones:conversacion", conversacion.pk)
    servicios.marcar_leida(conversacion, como_admin=atiende)
    contexto = {
        "conversacion": conversacion,
        "mensajes": list(conversacion.mensajes.all()),
        "atiende": atiende,
        "respuesta": respuesta,
        "estados": Conversacion.ESTADOS,
    }
    if request.GET.get("fragmento") == "mensajes":
        return render(request, "comunicaciones/mensajes.html", contexto)
    return render(request, "comunicaciones/conversacion.html", contexto)


# ── Niveles de aviso ─────────────────────────────────────────────────────────────────────────────────


# Pantalla «Plataforma → Catálogos comunes → Niveles de aviso»: los niveles con su color, para cambiarlos, crear más o
# borrar los que no se usan. Solo el superadmin (permiso «comunicaciones.niveles»). Cuesta 3 consultas.
#   - POST «accion»: crear, editar (con «nivel») o borrar (con «nivel»).
@requiere_permiso("comunicaciones.niveles")
def niveles(request):
    accion = request.POST.get("accion") if request.method == "POST" else None
    editado = get_object_or_404(NivelDeAviso, pk=request.POST.get("nivel")) if accion in ("editar", "borrar") else None
    nuevo = FormularioDeNivel(request.POST if accion == "crear" else None, prefix="nuevo")
    error = ""
    if accion == "crear" and nuevo.is_valid():
        nuevo.save()
        return redirect("comunicaciones:niveles")
    if accion == "editar":
        formulario = FormularioDeNivel(request.POST, instance=editado, prefix=f"n{editado.pk}")
        if formulario.is_valid():
            formulario.save()
            return redirect("comunicaciones:niveles")
        error = " ".join(" ".join(errores) for errores in formulario.errors.values())
    if accion == "borrar":
        try:
            editado.delete()
            return redirect("comunicaciones:niveles")
        except ProtectedError:
            error = f"«{editado}» ya se ha usado en algún aviso: no se puede borrar (puedes cambiarle el nombre o el color)."
    lista = NivelDeAviso.objects.annotate(usos=Count("avisos"))
    filas = [{"nivel": nivel, "formulario": FormularioDeNivel(instance=nivel, prefix=f"n{nivel.pk}")} for nivel in lista]
    return render(request, "comunicaciones/niveles.html", {"filas": filas, "nuevo": nuevo, "error": error, "abrir": accion})
