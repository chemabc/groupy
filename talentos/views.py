"""
Pantallas de la sección «Talentos»: mis talentos (y con qué grupos los comparto), peticiones (listas y
cada una, con «Lo ofrezco» y «Tengo dudas»), pedir talentos, cuántos hay en mis grupos y el catálogo
(superadmin).
"""

from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from grupos.models import Grupo
from grupos.servicios import grupos_de
from permisos.decoradores import requiere_permiso
from permisos.servicios import SinPermiso, explicar_falta, permisos_de, puede

from . import servicios
from .formularios import FormularioDePeticion, FormularioDeTalento
from .models import Necesidad, Ofrecimiento, PeticionDeTalentos, Talento, TalentoDePersona


# Grupos de una persona (también los que contienen a los suyos), en orden de árbol, con su organización.
def _mis_grupos(usuario):
    return list(Grupo.objects.en_orden_de_arbol().select_related("organizacion").filter(pk__in=grupos_de(usuario)))


# ── Mis talentos ─────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Mis talentos»: los suyos, cada uno con las casillas de los grupos con los que lo comparte, y
# el formulario para añadir otro (con las sugerencias del catálogo). Cuesta unas 6 consultas.
#   - POST «accion»: anadir (FormularioDeTalento), compartir (con «talento», «grupos» y «detalle») o quitar.
def mis_talentos(request):
    usuario = request.user
    accion = request.POST.get("accion") if request.method == "POST" else None
    formulario = FormularioDeTalento(request.POST if accion == "anadir" else None)
    error = ""
    try:
        if accion == "anadir" and formulario.is_valid():
            datos = formulario.cleaned_data
            servicios.anadir(usuario, datos["nombre"], datos["tipo"], datos["detalle"])
            return redirect("talentos:mis_talentos")
        if accion == "compartir":
            suyo = get_object_or_404(TalentoDePersona, pk=request.POST.get("talento"), usuario=usuario)
            suyo.detalle = request.POST.get("detalle", "")[:200]
            suyo.save(update_fields=["detalle"])
            servicios.compartir(suyo, [int(g) for g in request.POST.getlist("grupos") if g.isdigit()])
            return redirect("talentos:mis_talentos")
        if accion == "quitar":
            servicios.quitar(usuario, request.POST.get("talento"))
            return redirect("talentos:mis_talentos")
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
    grupos = _mis_grupos(usuario)
    suyos = list(TalentoDePersona.objects.filter(usuario=usuario).select_related("talento").prefetch_related("compartidos"))
    filas = [{"suyo": suyo, "compartidos": {c.grupo_id for c in suyo.compartidos.all()}} for suyo in suyos]
    contexto = {
        "filas": filas,
        "grupos": grupos,
        "formulario": formulario,
        "catalogo": list(Talento.objects.values_list("nombre", flat=True)),
        "error": error,
    }
    return render(request, "talentos/mis_talentos.html", contexto)


# ── Peticiones ───────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Peticiones»: las de los grupos de quien mira (y las que hizo o atiende su administración),
# primero las abiertas, con cuántos se han ofrecido para cada talento. Cuesta unas 6 consultas.
def peticiones(request):
    usuario = request.user
    mios = grupos_de(usuario)
    consulta = PeticionDeTalentos.objects.select_related("grupo__organizacion", "autor").prefetch_related("necesidades__talento")
    if not usuario.is_superuser:
        consulta = consulta.filter(Q(grupo_id__in=mios) | Q(autor=usuario))
    lista = list(consulta.order_by("estado", "-creada")[:100])
    ofrecidos = dict(
        Ofrecimiento.objects.filter(necesidad__peticion__in=lista).values("necesidad_id").annotate(n=Count("pk")).values_list("necesidad_id", "n")
    )
    filas = [
        {"peticion": peticion, "necesidades": [{"necesidad": n, "ofrecidos": ofrecidos.get(n.pk, 0)} for n in peticion.necesidades.all()]}
        for peticion in lista
    ]
    return render(request, "talentos/peticiones.html", {"filas": filas, "puede_pedir": _grupos_donde_pide(usuario) != []})


# Pantalla de una petición: cada talento con «x de y» ofrecidos, los botones «Lo ofrezco» / «Retirar» (si
# se tiene el talento), el enlace «Tengo dudas» (conversación con la administración del grupo) y, para
# quien la hizo y la administración, quién se ofrece y el botón para cerrarla.
#   - pk: número de la petición.
#   - POST «accion»: ofrecer o retirar (con «necesidad» y, al ofrecer, «mensaje»), cerrar o abrir.
def peticion(request, pk):
    usuario = request.user
    peticion = get_object_or_404(PeticionDeTalentos.objects.select_related("grupo__organizacion", "autor"), pk=pk)
    if not servicios.ve_la_peticion(usuario, peticion):
        raise SinPermiso(f"Esta petición solo la ven los miembros de {peticion.grupo} y su administración.")
    accion = request.POST.get("accion") if request.method == "POST" else None
    error = ""
    try:
        if accion in ("ofrecer", "retirar"):
            necesidad = get_object_or_404(Necesidad, pk=request.POST.get("necesidad"), peticion=peticion)
            if accion == "ofrecer":
                servicios.ofrecer(usuario, necesidad, request.POST.get("mensaje", "")[:300])
            else:
                servicios.retirar(usuario, necesidad)
            return redirect("talentos:peticion", peticion.pk)
        if accion in ("cerrar", "abrir"):
            servicios.cambiar_estado(usuario, peticion, PeticionDeTalentos.CERRADA if accion == "cerrar" else PeticionDeTalentos.ABIERTA)
            return redirect("talentos:peticion", peticion.pk)
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
    administra = servicios.ve_quien_se_ofrece(usuario, peticion)
    tengo = set(TalentoDePersona.objects.filter(usuario=usuario).values_list("talento_id", flat=True))
    necesidades = list(peticion.necesidades.select_related("talento").prefetch_related("ofrecimientos__usuario"))
    filas = []
    for necesidad in necesidades:
        ofrecimientos = list(necesidad.ofrecimientos.all())
        filas.append(
            {
                "necesidad": necesidad,
                "ofrecidos": len(ofrecimientos),
                "quienes": ofrecimientos if administra else [],
                "lo_tengo": necesidad.talento_id in tengo,
                "lo_ofrezco": any(o.usuario_id == usuario.pk for o in ofrecimientos),
            }
        )
    # «Tengo dudas» lleva a escribir a la administración del grupo (pantalla de «comunicaciones», por su
    # nombre de ruta: no se importa ese módulo), con el asunto ya puesto.
    dudas = f"{reverse('comunicaciones:nueva_conversacion')}?{urlencode({'administracion': f'g{peticion.grupo_id}', 'asunto': f'Talentos: {peticion.asunto}'})}"
    contexto = {"peticion": peticion, "filas": filas, "administra": administra, "dudas": dudas, "error": error}
    return render(request, "talentos/peticion.html", contexto)


# Grupos donde una persona puede pedir talentos (con «talentos.pedir»), como (id, «ORG › camino»).
def _grupos_donde_pide(usuario):
    consulta = Grupo.objects.en_orden_de_arbol().select_related("organizacion")
    if not usuario.is_superuser:
        ids = [grupo for grupo, codigos in permisos_de(usuario).grupos.items() if "talentos.pedir" in codigos]
        if not ids:
            return []
        consulta = consulta.filter(pk__in=ids)
    return [(grupo.pk, f"{grupo.organizacion.nombre} › {grupo.camino}") for grupo in consulta]


# Pantalla «Pedir talentos»: a qué grupo, para qué y qué talentos hacen falta (hasta cinco, con su número).
# Con «?grupo=<id>» se elige ese grupo. Solo quien tiene «talentos.pedir» en algún grupo.
#   - POST: los datos de FormularioDePeticion.
def nueva_peticion(request):
    usuario = request.user
    grupos = _grupos_donde_pide(usuario)
    if not grupos:
        raise SinPermiso(explicar_falta("talentos.pedir"))
    formulario = FormularioDePeticion(request.POST or None, initial={"grupo": request.GET.get("grupo")}, grupos=grupos)
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            necesidades = [(servicios.obtener_o_crear(nombre, Talento.HABILIDAD, usuario), cantidad) for nombre, cantidad in formulario.necesidades()]
            peticion = servicios.pedir(usuario, Grupo.objects.get(pk=datos["grupo"]), datos["asunto"], datos["descripcion"], necesidades)
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("talentos:peticion", peticion.pk)
    contexto = {"formulario": formulario, "catalogo": list(Talento.objects.values_list("nombre", flat=True))}
    return render(request, "talentos/nueva_peticion.html", contexto)


# ── Recuentos ────────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Talentos de mis grupos»: se elige uno de sus grupos y se ve cuántas personas comparten cada
# talento con él (o con sus subgrupos). Nunca quiénes. Cuesta unas 5 consultas.
#   - GET «grupo»: el grupo elegido (por defecto, el primero).
def del_grupo(request):
    usuario = request.user
    grupos = _mis_grupos(usuario) if not usuario.is_superuser else list(Grupo.objects.en_orden_de_arbol().select_related("organizacion"))
    elegido_id = request.GET.get("grupo", "")
    elegido = next((g for g in grupos if str(g.pk) == elegido_id), grupos[0] if grupos else None)
    contexto = {
        "grupos": grupos,
        "elegido": elegido,
        "recuento": servicios.recuento_del_grupo(elegido) if elegido else [],
        "puede_pedir": bool(elegido) and puede(usuario, "talentos.pedir", grupo=elegido),
    }
    return render(request, "talentos/del_grupo.html", contexto)


# ── Catálogo ─────────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Catálogo» (superadmin): los talentos con cuántas personas los tienen; renombrar, cambiar el
# tipo y las relacionadas, y fusionar repetidos (marcándolos y eligiendo cuál se queda).
#   - POST «accion»: editar (con «talento», «nombre», «tipo», «relacionadas») o fusionar (con «talentos» y «destino»).
@requiere_permiso("talentos.catalogo")
def catalogo(request):
    accion = request.POST.get("accion") if request.method == "POST" else None
    error = ""
    try:
        if accion == "editar":
            talento = get_object_or_404(Talento, pk=request.POST.get("talento"))
            nombre = " ".join(request.POST.get("nombre", "").split())
            otro = servicios.buscar(nombre)
            if not nombre or (otro and otro.pk != talento.pk):
                raise ValidationError(f"Ya hay un talento «{otro}»: fusiónalos en lugar de repetir el nombre." if otro else "El nombre está vacío.")
            talento.nombre, talento.relacionadas = nombre, request.POST.get("relacionadas", "")
            talento.tipo = request.POST.get("tipo") if request.POST.get("tipo") in dict(Talento.TIPOS) else talento.tipo
            talento.save()
            return redirect("talentos:catalogo")
        if accion == "fusionar":
            elegidos = list(Talento.objects.filter(pk__in=request.POST.getlist("talentos")))
            destino = next((t for t in elegidos if str(t.pk) == request.POST.get("destino")), None)
            if destino is None or len(elegidos) < 2:
                raise ValidationError("Para fusionar, marca al menos dos talentos y elige cuál se queda (uno de los marcados).")
            servicios.fusionar(destino, elegidos)
            return redirect("talentos:catalogo")
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
    talentos = list(Talento.objects.annotate(numero_de_personas=Count("personas")).order_by("normalizada"))
    return render(request, "talentos/catalogo.html", {"talentos": talentos, "tipos": Talento.TIPOS, "error": error})
