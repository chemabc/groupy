"""
Pantallas de la sección «Solicitudes» (pendientes, pasadas, mis solicitudes, pedir algo y cada
solicitud) y de «Configuración → Solicitudes» (apoyos y plazos). Ver docs/diseno.md, apartado 6.

Cada persona ve las solicitudes de sus grupos (también de los que contienen a los suyos), las de los
grupos donde da el sí de la administración y las suyas; el superadmin, todas. Los apoyos se ven con el
alias de quien apoya; los rechazos, solo como número.
"""

from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from base.registro import registro
from grupos.models import Grupo, Pertenencia
from grupos.servicios import grupos_de
from permisos.servicios import SinPermiso, explicar_falta, organizaciones_con

from . import servicios
from .formularios import FormularioDeAjuste, FormularioDeSolicitud
from .models import AjusteDeSolicitud, Apoyo, Solicitud

# Cuántas solicitudes se muestran como mucho en cada lista.
MAXIMO = 200


# Prepara las filas de una lista de solicitudes: cada una con su tipo, quién la apoya, la respuesta de
# quien mira y lo que puede hacer. 2 consultas para todas las filas (respuestas propias y apoyos).
#   - usuario: quien mira.
#   - solicitudes: lista de solicitudes (con grupo, organización y solicitante cargados).
#   - mios: los ids de sus grupos.
def _filas(usuario, solicitudes, mios):
    ids = [solicitud.pk for solicitud in solicitudes]
    mias = dict(Apoyo.objects.filter(usuario=usuario, solicitud_id__in=ids).values_list("solicitud_id", "acepta"))
    quien_apoya = defaultdict(list)
    for solicitud_id, alias in Apoyo.objects.filter(solicitud_id__in=ids, acepta=True).order_by("usuario__alias").values_list("solicitud_id", "usuario__alias"):
        quien_apoya[solicitud_id].append(alias)
    filas = []
    for solicitud in solicitudes:
        tipo = registro.solicitudes.get(solicitud.tipo)
        pendiente = solicitud.estado == Solicitud.PENDIENTE
        filas.append(
            {
                "solicitud": solicitud,
                "tipo": tipo.nombre if tipo else solicitud.tipo,
                "quien_apoya": quien_apoya.get(solicitud.pk, []),
                "mi_respuesta": mias.get(solicitud.pk),
                "puede_responder": pendiente and servicios.puede_responder(usuario, solicitud, mios),
                "puede_aprobar": pendiente and solicitud.necesita_aprobacion and not solicitud.aprobada_por_id and servicios.puede_aprobar(usuario, solicitud),
                "superadmin_basta": pendiente and usuario.is_superuser and bool(tipo and tipo.basta_el_superadmin),
                "es_mia": solicitud.solicitante_id == usuario.pk,
            }
        )
    return filas


# Consulta de las solicitudes que ve una persona, con lo necesario para pintarlas. Antes caduca las que
# hayan vencido.
def _visibles(usuario, mios):
    servicios.caducar_vencidas()
    return servicios.visibles_para(usuario, mios).select_related("grupo__organizacion", "solicitante", "aprobada_por")


# Pantalla «Solicitudes → Pendientes». Cuesta unas 7 consultas.
def pendientes(request):
    mios = grupos_de(request.user)
    lista = list(_visibles(request.user, mios).filter(estado=Solicitud.PENDIENTE).order_by("caduca_el", "pk")[:MAXIMO])
    return render(request, "solicitudes/lista.html", {"filas": _filas(request.user, lista, mios), "vacio": "No hay solicitudes pendientes."})


# Pantalla «Solicitudes → Pasadas»: aceptadas, canceladas y caducadas. Cuesta unas 7 consultas.
def pasadas(request):
    mios = grupos_de(request.user)
    lista = list(_visibles(request.user, mios).exclude(estado=Solicitud.PENDIENTE).order_by("-resuelta_el", "-pk")[:MAXIMO])
    return render(request, "solicitudes/lista.html", {"filas": _filas(request.user, lista, mios), "vacio": "No hay solicitudes pasadas."})


# Pantalla «Solicitudes → Mis solicitudes». Cuesta unas 7 consultas.
def mias(request):
    mios = grupos_de(request.user)
    lista = list(_visibles(request.user, mios).filter(solicitante=request.user)[:MAXIMO])
    return render(request, "solicitudes/lista.html", {"filas": _filas(request.user, lista, mios), "vacio": "Aún no has pedido nada.", "con_pedir": True})


# Pantalla «Pedir algo»: los tipos que se piden desde aquí (por ahora, entrar en un grupo) y los grupos
# posibles: los de sus organizaciones o, si aún no está en ningún grupo, los de todas.
#   - POST: los datos de FormularioDeSolicitud.
def nueva(request):
    usuario = request.user
    tipos = [(tipo.codigo, tipo.nombre) for tipo in registro.solicitudes.values() if tipo.generica]
    organizaciones = set(Pertenencia.objects.filter(usuario=usuario).values_list("grupo__organizacion_id", flat=True))
    candidatos = Grupo.objects.en_orden_de_arbol().select_related("organizacion")
    if organizaciones:
        candidatos = candidatos.filter(organizacion_id__in=organizaciones)
    grupos = {grupo.pk: grupo for grupo in candidatos}
    formulario = FormularioDeSolicitud(
        request.POST or None, tipos=tipos, grupos=[(pk, f"{g.organizacion.nombre} › {g.camino}") for pk, g in grupos.items()]
    )
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            solicitud = servicios.pedir(usuario, datos["tipo"], grupos[datos["grupo"]], datos["descripcion"], datos["justificacion"])
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("solicitudes:solicitud", solicitud.pk)
    return render(request, "solicitudes/nueva.html", {"formulario": formulario})


# Pantalla de una solicitud, con sus botones: apoyar, rechazar, retirar la respuesta, dar el sí de la
# administración (o del superadmin) y cancelar (quien la pidió).
#   - pk: número de la solicitud.
#   - POST «accion»: apoyar, rechazar, retirar, aprobar o cancelar.
def solicitud(request, pk):
    usuario = request.user
    mios = grupos_de(usuario)
    solicitud = get_object_or_404(_visibles(usuario, mios), pk=pk)
    accion = request.POST.get("accion") if request.method == "POST" else None
    error = ""
    try:
        if accion in ("apoyar", "rechazar"):
            servicios.responder(solicitud, usuario, acepta=accion == "apoyar")
        elif accion == "retirar":
            servicios.retirar_respuesta(solicitud, usuario)
        elif accion == "aprobar":
            servicios.aprobar(solicitud, usuario)
        elif accion == "cancelar":
            servicios.cancelar(solicitud, usuario)
        if accion:
            return redirect("solicitudes:solicitud", solicitud.pk)
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
    fila = _filas(usuario, [solicitud], mios)[0]
    return render(request, "solicitudes/solicitud.html", {"fila": fila, "error": error})


# Pantalla «Configuración → Solicitudes»: apoyos y días de cada tipo, para toda la plataforma (el
# superadmin) y para cada organización que ajusta quien mira (su admin).
#   - POST: «tipo», «organizacion» (número o vacío para la plataforma), «apoyos» y «dias».
def ajustes(request):
    usuario = request.user
    organizaciones = list(organizaciones_con(usuario, "solicitudes.ajustar"))
    if not organizaciones and not usuario.is_superuser:
        raise SinPermiso(explicar_falta("solicitudes.ajustar"))
    ambitos = ([(None, "Toda la plataforma (si la organización no lo cambia)")] if usuario.is_superuser else [])
    ambitos += [(organizacion.pk, organizacion.nombre) for organizacion in organizaciones]
    error = ""
    if request.method == "POST":
        formulario = FormularioDeAjuste(request.POST)
        organizacion = request.POST.get("organizacion") or None
        organizacion = int(organizacion) if organizacion and organizacion.isdigit() else None
        if organizacion not in dict(ambitos) or request.POST.get("tipo") not in registro.solicitudes:
            raise SinPermiso(explicar_falta("solicitudes.ajustar"))
        if formulario.is_valid():
            servicios.ajustar(request.POST["tipo"], organizacion, formulario.cleaned_data["apoyos"], formulario.cleaned_data["dias"])
            return redirect("solicitudes:ajustes")
        error = " ".join(" ".join(errores) for errores in formulario.errors.values())
    # Ajustes guardados de la plataforma y de sus organizaciones, de una vez: {(organización, tipo): ajuste}.
    consulta = AjusteDeSolicitud.objects.filter(Q(organizacion_id__in=[pk for pk, _nombre in ambitos if pk]) | Q(organizacion__isnull=True))
    guardados = {(ajuste.organizacion_id, ajuste.tipo): ajuste for ajuste in consulta}
    tarjetas = []
    for organizacion, nombre in ambitos:
        filas = []
        for tipo in registro.solicitudes.values():
            propio = guardados.get((organizacion, tipo.codigo))
            general = guardados.get((None, tipo.codigo))
            apoyos, dias = (propio.apoyos, propio.dias) if propio else ((general.apoyos, general.dias) if general else (tipo.apoyos, tipo.dias))
            filas.append({"tipo": tipo, "apoyos": apoyos, "dias": dias, "propio": propio is not None})
        tarjetas.append({"organizacion": organizacion, "nombre": nombre, "filas": filas})
    return render(request, "solicitudes/ajustes.html", {"tarjetas": tarjetas, "error": error})
