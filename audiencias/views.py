"""
Pantalla «Configuración → Visibilidad»: qué niveles de visibilidad ofrece cada organización a quien
publica algo en ella (ver docs/diseno.md, apartado 3.4). La ve el superadmin (todas las organizaciones)
y el admin de cada organización (la suya), con el permiso «audiencias.configurar».
"""

from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse

from permisos.servicios import SinPermiso, explicar_falta, organizaciones_con

from .formularios import ALTURAS, FormularioDeVisibilidad
from .models import ConfiguracionDeVisibilidad
from .servicios import guardar_configuracion

PERMISO = "audiencias.configurar"


# Frase que resume lo que permite una configuración, para leerla de un vistazo: «Privado; su grupo hasta
# el grupo padre; toda la organización. No permite lo público.».
def resumen(configuracion):
    partes = ["privado", f"su grupo: {dict(ALTURAS).get(configuracion.altura_maxima, f'hasta {configuracion.altura_maxima} niveles').lower()}", "grupos concretos"]
    if configuracion.permite_toda_la_organizacion:
        partes.append("toda la organización")
    if configuracion.permite_publico:
        partes.append("público")
    texto = "Se puede elegir: " + "; ".join(partes) + "."
    if not configuracion.permite_publico:
        texto += " No se permite lo público."
    return texto


# Pantalla de la visibilidad: una tarjeta por organización con su configuración y el formulario para
# cambiarla. Cuesta 4 consultas, sea cual sea el número de organizaciones.
#   - POST: «organizacion» y los datos de FormularioDeVisibilidad.
def visibilidad(request):
    organizaciones = list(organizaciones_con(request.user, PERMISO))
    if not organizaciones:
        raise SinPermiso(explicar_falta(PERMISO))
    # Configuraciones guardadas, de una vez (las que no tienen usan la de por defecto).
    guardadas = {c.organizacion_id: c for c in ConfiguracionDeVisibilidad.objects.filter(organizacion__in=organizaciones)}
    elegida = None
    if request.method == "POST":
        por_numero = {organizacion.pk: organizacion for organizacion in organizaciones}
        elegida = por_numero.get(_numero(request.POST.get("organizacion")))
        if elegida is None:
            raise SinPermiso(explicar_falta(PERMISO))
    tarjetas = []
    for organizacion in organizaciones:
        # La guardada o, si no tiene, la de por defecto (la más cerrada), sin guardarla.
        configuracion = guardadas.get(organizacion.pk) or ConfiguracionDeVisibilidad(organizacion=organizacion)
        inicial = {
            "altura_maxima": configuracion.altura_maxima,
            "permite_toda_la_organizacion": configuracion.permite_toda_la_organizacion,
            "permite_publico": configuracion.permite_publico,
        }
        formulario = FormularioDeVisibilidad(request.POST if organizacion is elegida else None, initial=inicial, prefix=f"o{organizacion.pk}")
        if organizacion is elegida and formulario.is_valid():
            try:
                guardar_configuracion(organizacion, **formulario.cleaned_data)
            except ValidationError as error:
                formulario.add_error(None, error)
            else:
                return redirect(f"{reverse('audiencias:visibilidad')}#organizacion-{organizacion.pk}")
        tarjetas.append(
            {
                "organizacion": organizacion,
                "resumen": resumen(configuracion),
                "por_defecto": organizacion.pk not in guardadas,
                "formulario": formulario,
            }
        )
    return render(request, "audiencias/visibilidad.html", {"tarjetas": tarjetas, "elegida": elegida})


# Número de un texto, o None si no lo es.
def _numero(texto):
    return int(texto) if texto and texto.isdigit() else None
