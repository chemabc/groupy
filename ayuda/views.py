"""
Pantallas del módulo «ayuda»: cada documento de docs/ convertido en página.
"""

from django.http import Http404
from django.shortcuts import render

from base.registro import puede_ver_entrada, registro
from permisos.servicios import SinPermiso, explicar_falta

from .documentos import POR_CLAVE, convertido


# Pantalla de un documento de la ayuda (por ejemplo, «Ayuda → Documentación de la plataforma →
# Tutorial»), con su índice plegable a la izquierda. La misma página se ve en la zona principal o, si la
# pide el botón «?» rojo de la cabecera, en el panel de ayuda de la derecha (base/contexto.py elige la
# plantilla). Quién puede verla lo decide la subsección del menú a la que pertenece el documento, con la
# misma regla que la muestra u oculta en el menú: si no se puede, sale la explicación de qué falta.
#   - clave: el documento («tutorial», «diseno»…), que pone la dirección.
def documento(request, clave):
    ficha = POR_CLAVE.get(clave)
    if ficha is None:
        raise Http404("No existe ese documento.")
    entrada = registro.entradas[ficha.apartado]
    if not puede_ver_entrada(request.user, entrada):
        raise SinPermiso(explicar_falta(entrada.permiso))
    return render(request, "ayuda/documento.html", {"documento": convertido(clave)})
