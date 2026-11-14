"""
Usuarios en la trastienda (el panel de Django), solo para emergencias técnicas. Las pantallas de
verdad del superadmin llegan más adelante en la fase 1.

El módulo «grupos» amplía esta ficha con las pertenencias de cada usuario (grupos/admin.py), porque
«usuarios» está en una capa inferior y no puede conocer los grupos.
"""

from django.contrib import admin
from django.contrib.auth.models import Group

from base.trastienda import ConAyuda

from .models import Usuario

# Django trae su propia tabla de «grupos» (Autenticación y autorización → Grupos), que sirve para
# repartir permisos del panel. No tiene nada que ver con los grupos de las asambleas y confunde, así que
# se quita de la trastienda.
admin.site.unregister(Group)


@admin.register(Usuario)
class UsuarioEnLaTrastienda(ConAyuda, admin.ModelAdmin):
    """Lista y ficha de usuarios en la trastienda. La contraseña no se edita aquí, solo se ve cifrada."""

    ayuda = (
        "Cuentas con seudónimo (alias) de la plataforma. Aquí no hay datos reales de nadie: la identidad "
        "real solo está en la bóveda.\n\n"
        "Se puede: activar o desactivar una cuenta, marcarla como superadmin y cambiar su correo "
        "alternativo. En la ficha se ven y se cambian sus pertenencias (en qué grupos está), y la lista de "
        "todos sus grupos, también los que contienen a los suyos.\n\n"
        "La contraseña no se ve ni se cambia aquí: cada persona la cambia en «Configuración de mi cuenta → Contraseña»."
    )
    list_display = ["alias", "es_superadmin", "activo", "activado_el", "last_login"]
    list_filter = ["es_superadmin", "activo"]
    search_fields = ["alias_normalizado"]
    fields = ["alias", "correo_alternativo", "es_superadmin", "activo", "activado_el", "password", "last_login"]
    readonly_fields = ["password", "last_login"]
