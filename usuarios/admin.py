"""
Usuarios en la trastienda (el panel de Django), solo para emergencias técnicas. Las pantallas de
verdad del superadmin llegan más adelante en la fase 1.
"""

from django.contrib import admin

from .models import Usuario


@admin.register(Usuario)
class UsuarioEnLaTrastienda(admin.ModelAdmin):
    """Lista y ficha de usuarios en la trastienda. La contraseña no se edita aquí, solo se ve cifrada."""

    list_display = ["alias", "es_superadmin", "activo", "activado_el", "last_login"]
    list_filter = ["es_superadmin", "activo"]
    search_fields = ["alias_normalizado"]
    fields = ["alias", "correo_alternativo", "es_superadmin", "activo", "activado_el", "password", "last_login"]
    readonly_fields = ["password", "last_login"]
