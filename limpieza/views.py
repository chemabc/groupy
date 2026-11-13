"""
Pantallas del módulo «limpieza»:

- «Archivo → Archivados»: lo archivado que ve cada persona, con qué día se borrará y el botón
  «Conservar». El superadmin, además, puede dejar de conservar y borrar ya (podar a mano).
- «Archivo → Borrados»: el registro de lo que se ha borrado (lo que veía cada persona).
- «Configuración → Limpieza»: los plazos de cada tipo de elemento (solo el superadmin).
"""

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from base.registro import registro
from permisos.decoradores import requiere_permiso
from permisos.servicios import SinPermiso

from . import servicios
from .formularios import FormularioDePlazo
from .models import Archivado

# Cuántos elementos se muestran como mucho en cada lista.
MAXIMO = 300


# Pantalla «Archivados»: lo archivado que se ve, lo más reciente primero, con su tipo, cuándo se archivó
# y qué día se borrará (o quién lo conservó). Unas 3 consultas.
#   - GET «tipo»: solo los de un tipo de elemento.
#   - GET «pronto»: solo lo que ya tiene aviso de borrado y nadie ha conservado.
def archivados(request):
    tipo, pronto = request.GET.get("tipo", ""), bool(request.GET.get("pronto"))
    consulta = servicios.archivados_visibles(request.user).select_related("conservado_por")
    if tipo in registro.limpiables:
        consulta = consulta.filter(tipo=tipo)
    if pronto:
        consulta = consulta.filter(avisado_el__isnull=False, conservado_el__isnull=True)
    vigentes, ahora = servicios.plazos(), timezone.now()
    filas = [
        {
            "archivado": archivado,
            "tipo": vigentes[archivado.tipo].limpiable.nombre if archivado.tipo in vigentes else archivado.tipo,
            "se_borra_el": servicios.se_borra_el(archivado, vigentes.get(archivado.tipo), ahora),
        }
        for archivado in consulta[:MAXIMO]
    ]
    tipos = [(codigo, plazo.limpiable.nombre) for codigo, plazo in vigentes.items() if plazo.con_archivo]
    return render(
        request, "limpieza/archivados.html",
        {"filas": filas, "tipos": tipos, "tipo": tipo, "pronto": pronto, "superadmin": request.user.is_superuser},
    )


# Acciones sobre un elemento archivado (botones de «Archivados»). Vuelve a la lista, con sus filtros.
#   - POST «accion»: «conservar» (quien lo ve), «dejar» (dejar de conservar) o «podar» (borrar ya),
#     estas dos solo el superadmin.
#   - POST «volver»: la dirección de la lista (con sus filtros) a la que volver.
@require_POST
def archivado(request, pk):
    fila = get_object_or_404(servicios.archivados_visibles(request.user), pk=pk)
    acciones = {"conservar": servicios.conservar, "dejar": servicios.dejar_de_conservar, "podar": servicios.podar}
    accion = acciones.get(request.POST.get("accion"))
    if accion is None:
        raise SinPermiso("Esa acción no existe.")
    try:
        accion(request.user, fila)
    except ValidationError as error:
        raise SinPermiso(" ".join(error.messages)) from error
    volver = request.POST.get("volver", "")
    return redirect(volver if volver.startswith(reverse("limpieza:archivados")) else "limpieza:archivados")


# Pantalla «Borrados»: el registro de lo borrado que se veía, lo más reciente primero. Unas 2 consultas.
def borrados(request):
    nombres = {codigo: limpiable.nombre for codigo, limpiable in registro.limpiables.items()}
    lista = list(servicios.borrados_visibles(request.user).select_related("quien")[:MAXIMO])
    filas = [{"borrado": borrado, "tipo": nombres.get(borrado.tipo, borrado.tipo)} for borrado in lista]
    return render(request, "limpieza/borrados.html", {"filas": filas})


# Pantalla «Configuración → Limpieza»: los plazos de cada tipo, para cambiarlos o volver a los de
# partida. Solo el superadmin (permiso «limpieza.configurar»). Cuesta 1 consulta.
#   - POST «tipo» y los campos de FormularioDePlazo; o «partida» con «tipo» para volver a los de partida.
@requiere_permiso("limpieza.configurar")
def plazos(request):
    error = ""
    if request.method == "POST":
        tipo = request.POST.get("tipo", "")
        if request.POST.get("partida"):
            servicios.plazo_de_partida(tipo)
            return redirect("limpieza:plazos")
        formulario = FormularioDePlazo(request.POST)
        vigente = servicios.plazos().get(tipo)
        if vigente and formulario.is_valid():
            datos = formulario.cleaned_data
            servicios.guardar_plazo(tipo, datos["activo"], datos["archivar_a"] or vigente.archivar_a, datos["borrar_a"])
            return redirect("limpieza:plazos")
        error = "Revisa los días: tienen que ser números enteros mayores que cero." if vigente else "Ese tipo de elemento no existe."
    vigentes = servicios.plazos()
    return render(
        request, "limpieza/plazos.html",
        {
            "con_archivo": [plazo for plazo in vigentes.values() if plazo.con_archivo],
            "sin_archivo": [plazo for plazo in vigentes.values() if not plazo.con_archivo],
            "aviso_previo": servicios.AVISO_PREVIO,
            "error": error,
        },
    )
