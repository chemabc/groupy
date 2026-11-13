"""
Direcciones del módulo «etiquetas» que usa el navegador: las sugerencias mientras se escribe en un
selector de etiquetas (componente «selectorDePalabras» de base/static/base/interfaz.js).
"""

from django.http import JsonResponse

from grupos.models import Pertenencia

from .servicios import sugerir


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
