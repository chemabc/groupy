"""
Avisos pendientes en la trastienda (panel de Django), para revisar a mano los que han fallado mientras
no exista la pantalla «Salud del sistema».
"""

from django.contrib import admin

from .models import AvisoPendiente


@admin.register(AvisoPendiente)
class AvisoPendienteAdmin(admin.ModelAdmin):
    """Lista de avisos pendientes, con los fallidos fáciles de filtrar."""

    # Columnas de la lista.
    list_display = ["evento", "receptor", "creado", "intentos", "fallido", "proximo_intento"]
    # Filtros del lateral.
    list_filter = ["fallido", "evento"]
