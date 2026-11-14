"""
Pantallas del módulo «etiquetas»:
- Las sugerencias mientras se escribe en un selector de etiquetas (componente «selectorDePalabras» de
  base/static/base/interfaz.js), en JSON.
- «Administrar → Mi organización → Etiquetas»: las etiquetas de cada organización (y las comunes, para el superadmin),
  para crearlas, renombrarlas, ponerles palabras relacionadas, fusionar repetidas y borrarlas.
"""

from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from base.tablas import normalizar
from grupos.models import Pertenencia
from permisos.servicios import SinPermiso, explicar_falta, organizaciones_con

from .formularios_de_pantalla import FormularioDeEtiqueta
from .models import Etiqueta
from .servicios import crear_etiqueta, fusionar, limpiar, renombrar, sugerir

PERMISO = "etiquetas.ordenar"
# Valor del desplegable para las etiquetas comunes (de todas las organizaciones).
COMUNES = "comunes"


# Devuelve en JSON las etiquetas que coinciden con lo escrito: {"sugerencias": [{"nombre", "comun"}]}.
# Solo se sugieren las de la organización indicada si quien escribe está en ella (o es superadmin); si
# no, solo las comunes. Así nadie ve las etiquetas de otra organización.
#   - GET «q»: lo escrito.
#   - GET «organizacion»: número de la organización en la que se etiqueta (opcional).
def sugerencias(request):
    organizacion = request.GET.get("organizacion", "")
    organizacion = int(organizacion) if organizacion.isdigit() else None
    if organizacion is not None and not request.user.is_superuser:
        dentro = Pertenencia.objects.filter(usuario=request.user, grupo__organizacion_id=organizacion).exists()
        organizacion = organizacion if dentro else None
    return JsonResponse({"sugerencias": sugerir(request.GET.get("q", ""), organizacion)})


# Pantalla «Administrar → Mi organización → Etiquetas»: arriba se elige de quién (una organización que puede ordenar
# quien mira o, para el superadmin, las comunes); debajo, sus etiquetas con cuántas cosas las llevan, y
# los formularios para crear, cambiar, fusionar y borrar. Cuesta 4 consultas.
#   - GET «de»: número de la organización o «comunes». «q»: buscar (también en las relacionadas).
#   - POST «accion»: crear, editar (etiqueta), fusionar (etiquetas y destino) o borrar (etiqueta).
def etiquetas(request):
    usuario = request.user
    organizaciones = list(organizaciones_con(usuario, PERMISO))
    if not organizaciones:
        raise SinPermiso(explicar_falta(PERMISO))
    opciones = [(str(organizacion.pk), organizacion.nombre) for organizacion in organizaciones]
    if usuario.is_superuser:
        opciones.append((COMUNES, "Comunes (todas las organizaciones)"))
    de = request.POST.get("de") or request.GET.get("de") or opciones[0][0]
    if de not in dict(opciones):
        raise SinPermiso(explicar_falta(PERMISO))
    organizacion = next((o for o in organizaciones if str(o.pk) == de), None)
    propias = Etiqueta.objects.filter(organizacion=organizacion) if organizacion else Etiqueta.objects.filter(organizacion__isnull=True)
    direccion = f"{reverse('etiquetas:etiquetas')}?de={de}"

    accion = request.POST.get("accion") if request.method == "POST" else None
    nueva = FormularioDeEtiqueta(request.POST if accion == "crear" else None)
    error, editada = "", None
    try:
        if accion == "crear" and nueva.is_valid():
            crear_etiqueta(nueva.cleaned_data["nombre"], organizacion, nueva.cleaned_data["relacionadas"], usuario)
            return redirect(direccion)
        if accion == "editar":
            editada = get_object_or_404(propias, pk=request.POST.get("etiqueta"))
            formulario = FormularioDeEtiqueta(request.POST)
            if formulario.is_valid():
                renombrar(editada, formulario.cleaned_data["nombre"], formulario.cleaned_data["relacionadas"])
                return redirect(direccion)
            error = " ".join(f"{campo}: {' '.join(errores)}" for campo, errores in formulario.errors.items())
        if accion == "fusionar":
            elegidas = list(propias.filter(pk__in=request.POST.getlist("etiquetas")))
            destino = next((e for e in elegidas if str(e.pk) == request.POST.get("destino")), None)
            if destino is None or len(elegidas) < 2:
                raise ValidationError("Para fusionar, marca al menos dos etiquetas y elige con cuál se quedan (debe ser una de las marcadas).")
            fusionar(destino, elegidas)
            return redirect(direccion)
        if accion == "borrar":
            get_object_or_404(propias, pk=request.POST.get("etiqueta")).delete()
            return redirect(direccion)
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)

    buscado = normalizar(limpiar(request.GET.get("q", "")))
    lista = propias.annotate(usos_totales=Count("usos")).order_by("normalizada")
    if buscado:
        lista = lista.filter(Q(normalizada__contains=buscado) | Q(relacionadas_normalizadas__contains=buscado))
    contexto = {
        "opciones": opciones,
        "de": de,
        "q": request.GET.get("q", ""),
        "etiquetas": list(lista),
        "nueva": nueva,
        "error": error,
        "editada": editada,
        "abrir": accion,
    }
    return render(request, "etiquetas/etiquetas.html", contexto)
