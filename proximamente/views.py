"""
Pantalla del módulo «proximamente».
"""

from django.shortcuts import render

from base.registro import puede_ver_entrada, registro
from permisos.servicios import SinPermiso, explicar_falta

from .apps import POR_CLAVE


# Pantalla de una herramienta pendiente: dice que aún está vacía y qué hará. Quién puede abrirla lo decide
# su entrada del menú, con la misma regla que la muestra u oculta allí.
#   - clave: la herramienta («moderacion»), que pone la dirección.
def pendiente(request, clave):
    pendiente = POR_CLAVE[clave]
    entrada = registro.entradas[f"proximamente.{clave}"]
    if not puede_ver_entrada(request.user, entrada):
        raise SinPermiso(explicar_falta(entrada.permiso))
    return render(request, "base/proximamente.html", {"descripcion": pendiente.descripcion})
