"""
Pantallas del módulo «mantenimiento»: la documentación del proyecto y la entrada a la trastienda. Solo
para quien tiene el permiso «mantenimiento.ver» (de entrada, el superadmin).
"""

from django.http import Http404
from django.shortcuts import render

from permisos.decoradores import requiere_permiso

from .documentos import DOCUMENTOS, documento


# Pantalla «Desarrollo y mantenimiento → Documentación»: un documento de docs/ convertido en página,
# con la lista de documentos arriba y su índice a la izquierda. Sin nombre, el primero (el diseño).
#   - nombre: el documento que se quiere ver («diseno», «tutorial»…).
@requiere_permiso("mantenimiento.ver")
def documentacion(request, nombre=DOCUMENTOS[0][0]):
    convertido = documento(nombre)
    if convertido is None:
        raise Http404("No existe ese documento.")
    contexto = {"documentos": DOCUMENTOS, "actual": nombre, "documento": convertido}
    return render(request, "mantenimiento/documentacion.html", contexto)


# Pantalla «Desarrollo y mantenimiento → Trastienda»: explica qué es y lleva a ella con un botón.
@requiere_permiso("mantenimiento.ver")
def trastienda(request):
    return render(request, "mantenimiento/trastienda.html")
