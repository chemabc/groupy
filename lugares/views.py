"""
Pantallas del módulo «lugares»: mi lugar (elegir, proponer un lugar nuevo o un cambio), mapa y lista,
ficha de un lugar, gestión del superadmin (propuestas, nuevo lugar, importar y recordatorio) y
«Administrar → Mi organización → Lugares».
"""

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from base.hojas import TIPO_ODS, Hoja, HojaIlegible, crear_ods, filas_por_columna, leer_filas
from base.tablas import Columna, FuenteDeLista, Tabla
from permisos.decoradores import requiere_permiso
from permisos.servicios import SinPermiso, explicar_falta, organizaciones_con

from . import servicios
from .formularios import FormularioDeHoja, FormularioDeLugar, FormularioDePropuesta
from .models import ConfiguracionDeLugares, Lugar, LugarDePersona, PropuestaDeLugar
from .servicios import CAMPOS

# Columnas de la hoja de importación: {campo: [nombres posibles]}; el primero es el de la plantilla.
COLUMNAS = {
    "nombre": ["Nombre"],
    "direccion": ["Dirección", "Direccion"],
    "url_localizacion": ["URL de localización", "URL", "Localización", "Mapa"],
    "latitud": ["Latitud", "Lat"],
    "longitud": ["Longitud", "Lon", "Lng"],
    "telefonos": ["Teléfonos", "Teléfono", "Telefonos"],
    "correos": ["Correos", "Correo"],
    "notas": ["Notas"],
}
# Clave de la sesión donde se guarda el plan de importación entre la vista previa y la confirmación.
CLAVE_DEL_PLAN = "lugares:plan_de_importacion"


# ── Mi lugar ─────────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Mi lugar»: el lugar elegido con sus datos, el desplegable para elegir o cambiarlo, y los
# formularios para proponer un cambio en sus datos o un lugar nuevo. Debajo, las propuestas propias.
#   - POST «accion»: elegir (con «lugar»), quitar, cambio o nuevo (con los datos de FormularioDePropuesta).
def mi_lugar(request):
    usuario = request.user
    eleccion = LugarDePersona.objects.select_related("lugar").filter(usuario=usuario).first()
    actual = eleccion.lugar if eleccion else None
    accion = request.POST.get("accion") if request.method == "POST" else None
    inicial = {campo: getattr(actual, campo) for campo in CAMPOS} if actual else {}
    cambio = FormularioDePropuesta(request.POST if accion == "cambio" else None, initial=inicial, prefix="cambio")
    nuevo = FormularioDePropuesta(request.POST if accion == "nuevo" else None, prefix="nuevo")
    error, aviso = "", ""
    try:
        if accion == "elegir":
            servicios.elegir(usuario, get_object_or_404(Lugar, pk=request.POST.get("lugar")))
            return redirect("lugares:mi_lugar")
        if accion == "quitar":
            servicios.quitar(usuario)
            return redirect("lugares:mi_lugar")
        if accion == "cambio" and actual and cambio.is_valid():
            servicios.proponer(usuario, cambio.cleaned_data, lugar=actual, motivo=cambio.cleaned_data["motivo"])
            aviso = "Propuesta enviada. El superadmin la revisará y te avisará."
            cambio = FormularioDePropuesta(initial=inicial, prefix="cambio")
        if accion == "nuevo" and nuevo.is_valid():
            servicios.proponer(usuario, nuevo.cleaned_data, motivo=nuevo.cleaned_data["motivo"])
            aviso = "Propuesta enviada. El superadmin la revisará y te avisará."
            nuevo = FormularioDePropuesta(prefix="nuevo")
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
    contexto = {
        "actual": actual,
        "lugares": Lugar.objects.filter(activo=True).only("pk", "nombre", "direccion"),
        "cambio": cambio,
        "nuevo": nuevo,
        "propuestas": PropuestaDeLugar.objects.filter(propuesta_por=usuario).select_related("lugar")[:20],
        "error": error,
        "aviso": aviso,
        "abrir": accion,
    }
    return render(request, "lugares/mi_lugar.html", contexto)


# ── Mapa, lista y ficha ──────────────────────────────────────────────────────────────────────────────


# Lanza SinPermiso si la persona no puede ver el mapa ni la lista (ninguna de sus organizaciones lo
# muestra).
def _exigir_mapa(usuario):
    if not servicios.ve_el_mapa(usuario):
        raise SinPermiso("Tus organizaciones no muestran el mapa de lugares a sus miembros. Lo decide su admin en «Administrar → Mi organización → Lugares».")


# Pantalla «Mapa»: los lugares con coordenadas en un mapa (isla de Leaflet, componente «mapa» de
# base/static/base/interfaz.js), con el número de personas solo si son 5 o más. Cuesta unas 6 consultas.
def mapa(request):
    _exigir_mapa(request.user)
    personas = servicios.recuentos(request.user)
    puntos = [
        {
            "lat": lugar.latitud, "lon": lugar.longitud, "titulo": lugar.nombre, "texto": lugar.direccion,
            "personas": personas.get(lugar.pk), "enlace": reverse("lugares:lugar", args=[lugar.pk]),
        }
        for lugar in Lugar.objects.filter(activo=True, latitud__isnull=False, longitud__isnull=False)
    ]
    sin_coordenadas = Lugar.objects.filter(activo=True, latitud__isnull=True).count()
    return render(request, "lugares/mapa.html", {"puntos": puntos, "sin_coordenadas": sin_coordenadas})


# Pantalla «Lista»: tabla filtrable con todos los lugares y su número de personas (desde 5). Cuesta unas
# 6 consultas.
def lista(request):
    _exigir_mapa(request.user)
    personas = servicios.recuentos(request.user)
    filas = [
        {"pk": lugar.pk, "nombre": lugar.nombre, "direccion": lugar.direccion, "telefonos": lugar.telefonos, "personas": personas.get(lugar.pk, "")}
        for lugar in Lugar.objects.filter(activo=True)
    ]
    tabla = Tabla(
        request,
        identificador="lugares",
        columnas=[
            Columna("nombre", "Lugar", enlace="lugares:lugar"),
            Columna("direccion", "Dirección"),
            Columna("telefonos", "Teléfonos"),
            Columna("personas", "Personas (desde 5)"),
        ],
        fuente=FuenteDeLista(filas, campos_de_busqueda=["nombre", "direccion"]),
    )
    plantilla = tabla.plantilla_parcial()
    if plantilla:
        return render(request, plantilla, {"tabla": tabla})
    return render(request, "lugares/lista.html", {"tabla": tabla})


# Pantalla de un lugar: sus datos y su número de personas (desde 5). El superadmin, además, lo edita.
#   - pk: número del lugar.
#   - POST: los datos de FormularioDeLugar (solo el superadmin).
def lugar(request, pk):
    lugar = get_object_or_404(Lugar, pk=pk)
    gestiona = request.user.is_superuser
    if not gestiona:
        _exigir_mapa(request.user)
    formulario = FormularioDeLugar(request.POST if request.method == "POST" else None, instance=lugar) if gestiona else None
    if formulario is not None and request.method == "POST" and formulario.is_valid():
        formulario.save()
        return redirect("lugares:lugar", lugar.pk)
    contexto = {"lugar": lugar, "personas": servicios.recuentos(request.user).get(lugar.pk), "formulario": formulario}
    return render(request, "lugares/lugar.html", contexto)


# ── Gestión (superadmin) ─────────────────────────────────────────────────────────────────────────────


# Pantalla «Propuestas»: las pendientes, con lo que cambia en cada cambio, para aceptarlas o rechazarlas;
# las ya revisadas, debajo; y el botón para recordar a quien no ha elegido lugar.
#   - POST «accion»: aceptar o rechazar (con «propuesta» y «respuesta»), o recordar.
@requiere_permiso("lugares.gestionar")
def propuestas(request):
    accion = request.POST.get("accion") if request.method == "POST" else None
    error, aviso = "", ""
    if accion in ("aceptar", "rechazar"):
        propuesta = get_object_or_404(PropuestaDeLugar.objects.select_related("lugar"), pk=request.POST.get("propuesta"))
        respuesta = request.POST.get("respuesta", "").strip()
        try:
            if accion == "aceptar":
                servicios.aceptar(propuesta, respuesta)
            elif not respuesta:
                raise ValidationError("Para rechazar una propuesta, explica por qué en la respuesta.")
            else:
                servicios.rechazar(propuesta, respuesta)
            return redirect("lugares:propuestas")
        except ValidationError as excepcion:
            error = " ".join(excepcion.messages)
    if accion == "recordar":
        servicios.recordar_a_quien_no_tiene_lugar()
        aviso = "Recordatorio enviado a quienes aún no han elegido lugar."
    pendientes = []
    for propuesta in PropuestaDeLugar.objects.filter(estado=PropuestaDeLugar.PENDIENTE).select_related("lugar", "propuesta_por"):
        cambios = []
        if propuesta.lugar_id:
            for campo in CAMPOS:
                antes, despues = getattr(propuesta.lugar, campo), getattr(propuesta, campo)
                if (antes or "") != (despues or ""):
                    cambios.append({"campo": PropuestaDeLugar._meta.get_field(campo).verbose_name, "antes": antes, "despues": despues})
        pendientes.append({"propuesta": propuesta, "cambios": cambios})
    revisadas = PropuestaDeLugar.objects.exclude(estado=PropuestaDeLugar.PENDIENTE).select_related("lugar", "propuesta_por")[:50]
    contexto = {"pendientes": pendientes, "revisadas": revisadas, "error": error, "aviso": aviso}
    return render(request, "lugares/propuestas.html", contexto)


# Pantalla «Nuevo lugar»: alta a mano.
@requiere_permiso("lugares.gestionar")
def nuevo(request):
    formulario = FormularioDeLugar(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        lugar = formulario.save()
        return redirect("lugares:lugar", lugar.pk)
    return render(request, "lugares/nuevo.html", {"formulario": formulario})


# Pantalla «Importar»: subir la hoja → vista previa (qué se crea, qué ya existe, errores por fila) →
# confirmar. El plan se guarda en la sesión entre los dos pasos. Con «?plantilla» descarga la plantilla.
#   - POST «accion»: subir (con «fichero») o confirmar.
@requiere_permiso("lugares.gestionar")
def importar(request):
    if "plantilla" in request.GET:
        respuesta = HttpResponse(crear_ods(_plantilla()), content_type=TIPO_ODS)
        respuesta["Content-Disposition"] = 'attachment; filename="plantilla-lugares.ods"'
        return respuesta
    accion = request.POST.get("accion") if request.method == "POST" else None
    formulario = FormularioDeHoja(request.POST if accion == "subir" else None, request.FILES if accion == "subir" else None)
    plan, error, aviso = request.session.get(CLAVE_DEL_PLAN), "", ""
    if accion == "subir" and formulario.is_valid():
        try:
            filas, faltan = filas_por_columna(leer_filas(formulario.cleaned_data["fichero"]), COLUMNAS, ["nombre", "direccion", "url_localizacion"])
        except HojaIlegible as excepcion:
            error, plan = str(excepcion), None
        else:
            if faltan:
                error, plan = f"Faltan columnas: {', '.join(COLUMNAS[c][0] for c in faltan)}.", None
            else:
                plan = servicios.planear_importacion(filas)
        request.session[CLAVE_DEL_PLAN] = plan
    if accion == "confirmar" and plan:
        try:
            creados = servicios.importar(plan)
            aviso, plan = f"Importados {creados} lugares.", None
            request.session.pop(CLAVE_DEL_PLAN, None)
        except ValidationError as excepcion:
            error = " ".join(excepcion.messages)
    contexto = {
        "formulario": formulario, "plan": plan, "error": error, "aviso": aviso,
        "con_errores": bool(plan) and any(e["estado"] == "error" for e in plan),
        "por_crear": sum(1 for e in plan or [] if e["estado"] == "crear"),
    }
    return render(request, "lugares/importar.html", contexto)


# La plantilla de importación: hoja «Datos» con la cabecera y un ejemplo, y hoja «Instrucciones».
def _plantilla():
    datos = Hoja(
        "Datos",
        [
            [nombres[0] for nombres in COLUMNAS.values()],
            ["IES Cervantes", "C/ Mayor 1, 28801 Alcalá de Henares", "https://www.openstreetmap.org/#map=18/40.4820/-3.3640", "", "", "918 000 000", "secretaria@ejemplo.org", "Entrada por la calle de atrás"],
        ],
        anchos=[6, 9, 10, 3, 3, 5, 6, 8],
    )
    instrucciones = Hoja(
        "Instrucciones",
        [
            ["Una fila por lugar. Obligatorias: Nombre, Dirección y URL de localización."],
            ["La URL es el enlace al sitio en un mapa (OpenStreetMap o Google Maps): de ella se sacan las coordenadas."],
            ["Si la URL no las lleva, rellena Latitud y Longitud (con punto: 40.4168 y -3.7038)."],
            ["Teléfonos y correos pueden ser varios, separados por comas. Notas: texto libre."],
            ["Un lugar con el mismo nombre y la misma dirección que otro que ya existe no se toca."],
        ],
        con_cabecera=False,
        anchos=[20],
    )
    return [datos, instrucciones]


# ── Configuración ────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Administrar → Mi organización → Lugares»: por cada organización que ajusta quien mira, qué ven sus miembros y
# si se publica el mapa.
#   - POST: «organizacion» y las casillas mapa_para_miembros, recuentos_para_miembros, publicar_en_la_web.
def configuracion(request):
    organizaciones = list(organizaciones_con(request.user, "lugares.configurar"))
    if not organizaciones:
        raise SinPermiso(explicar_falta("lugares.configurar"))
    guardadas = {c.organizacion_id: c for c in ConfiguracionDeLugares.objects.filter(organizacion__in=organizaciones)}
    campos = ["mapa_para_miembros", "recuentos_para_miembros", "publicar_en_la_web"]
    if request.method == "POST":
        por_numero = {organizacion.pk: organizacion for organizacion in organizaciones}
        numero = request.POST.get("organizacion", "")
        organizacion = por_numero.get(int(numero)) if numero.isdigit() else None
        if organizacion is None:
            raise SinPermiso(explicar_falta("lugares.configurar"))
        ConfiguracionDeLugares.objects.update_or_create(organizacion=organizacion, defaults={campo: campo in request.POST for campo in campos})
        return redirect("lugares:configuracion")
    tarjetas = []
    for organizacion in organizaciones:
        actual = guardadas.get(organizacion.pk) or ConfiguracionDeLugares(organizacion=organizacion)
        tarjetas.append(
            {
                "organizacion": organizacion,
                "opciones": [
                    {"campo": campo, "etiqueta": ConfiguracionDeLugares._meta.get_field(campo).verbose_name,
                     "ayuda": ConfiguracionDeLugares._meta.get_field(campo).help_text, "marcado": getattr(actual, campo)}
                    for campo in campos
                ],
            }
        )
    return render(request, "lugares/configuracion.html", {"tarjetas": tarjetas})

