"""
Pantallas del módulo «decisiones»: la lista (vigentes o todas), filtrable al momento, y la ficha de cada
decisión, donde la administración del grupo la marca como sustituida por otra.
"""

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from base.tablas import Columna, Filtro, FuenteDeLista, Tabla
from permisos.servicios import SinPermiso, puede

from . import servicios
from .models import Decision

# Máximo de decisiones que se cargan en la lista (se filtran en el navegador).
MAXIMO = 500


# Pinta la lista de decisiones (la usan las dos pantallas). Filtros por cómo se tomó y por grupo, y
# búsqueda por palabras; todo al momento. Cuesta 2 consultas.
#   - vigentes: si se esconden las sustituidas.
def _lista(request, vigentes):
    decisiones = list(servicios.visibles(request.user, vigentes).select_related("grupo")[:MAXIMO])
    filas = [
        {
            "pk": decision.pk,
            "texto": decision.texto[:140],
            "forma": decision.get_forma_display(),
            "detalle": decision.detalle,
            "grupo": decision.grupo.nombre,
            "fecha": timezone.localtime(decision.tomada).strftime("%d/%m/%Y"),
            "estado": "Sustituida" if decision.sustituida_por_id else "Vigente",
        }
        for decision in decisiones
    ]
    columnas = [Columna("fecha", "Fecha"), Columna("texto", "Decisión", enlace="decisiones:decision"), Columna("forma", "Cómo"), Columna("detalle", "Detalle"), Columna("grupo", "Grupo")]
    if not vigentes:
        columnas.append(Columna("estado", "Estado"))
    tabla = Tabla(
        request,
        identificador="decisiones",
        columnas=columnas,
        fuente=FuenteDeLista(filas, campos_de_busqueda=["texto", "detalle", "grupo"]),
        filtros=[
            Filtro("forma", "Cómo", opciones=tuple((nombre, nombre) for _codigo, nombre in Decision.FORMAS)),
            Filtro("grupo", "Grupo", opciones=tuple((nombre, nombre) for nombre in sorted({fila["grupo"] for fila in filas}))),
        ],
    )
    plantilla = tabla.plantilla_parcial()
    if plantilla:
        return render(request, plantilla, {"tabla": tabla})
    return render(request, "decisiones/lista.html", {"tabla": tabla, "vigentes": vigentes})


# Pantalla «Participación → Decisiones → Vigentes».
def lista(request):
    return _lista(request, vigentes=True)


# Pantalla «Participación → Decisiones → Todas» (también las sustituidas).
def todas(request):
    return _lista(request, vigentes=False)


# Ficha de una decisión: qué, cómo, cuándo, su origen, a cuál sustituye y por cuál está sustituida. Quien
# administra el grupo elige aquí la decisión que la sustituye (o la deja vigente).
#   - pk: el número de la decisión.
#   - POST «nueva»: el número de la decisión que la sustituye (vacío: vigente).
def decision(request, pk):
    usuario = request.user
    decision = get_object_or_404(servicios.visibles(usuario, vigentes=False).select_related("grupo", "sustituida_por"), pk=pk)
    gestiona = puede(usuario, "decisiones.sustituir", grupo=decision.grupo_id)
    error = ""
    if request.method == "POST":
        if not gestiona:
            raise SinPermiso("Solo la administración del grupo puede marcar una decisión como sustituida.")
        elegida = request.POST.get("nueva", "")
        nueva = get_object_or_404(servicios.visibles(usuario, vigentes=False), pk=elegida) if elegida.isdigit() else None
        try:
            servicios.sustituir(usuario, decision, nueva)
        except ValidationError as excepcion:
            error = " ".join(excepcion.messages)
        else:
            return redirect("decisiones:decision", decision.pk)
    candidatas = []
    if gestiona:
        candidatas = list(
            servicios.visibles(usuario, vigentes=False).filter(grupo_id=decision.grupo_id, tomada__gte=decision.tomada).exclude(pk=decision.pk)[:100]
        )
    contexto = {
        "decision": decision,
        "sustituye_a": list(decision.sustituye_a.all()),
        "gestiona": gestiona,
        "candidatas": candidatas,
        "error": error,
    }
    return render(request, "decisiones/decision.html", contexto)
