"""
Configuración del panel de Django para este proyecto: usa la trastienda reordenada
(config/trastienda.py) en lugar del panel por defecto. Está en INSTALLED_APPS en lugar de
«django.contrib.admin».
"""

from django.contrib.admin.apps import AdminConfig


class TrastiendaConfig(AdminConfig):
    """El panel de Django, con la trastienda como sitio por defecto."""

    default_site = "config.trastienda.Trastienda"
