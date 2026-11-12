"""
Organizaciones y grupos en la trastienda (el panel de Django), solo para emergencias técnicas. Las
pantallas de verdad llegan en la pieza de pantallas del superadmin.

Ojo: lo que se cambia aquí no pasa por grupos/servicios.py, así que no avisa con eventos_sw (salvo crear
o mover grupos, que avisa el propio modelo).
"""

from django.contrib import admin

from .models import AdminDeOrganizacion, Grupo, InvitacionDeGrupo, Organizacion, Pertenencia, RelacionEntreGrupos


@admin.register(Organizacion)
class OrganizacionEnLaTrastienda(admin.ModelAdmin):
    """Lista de organizaciones."""

    list_display = ["nombre", "creada_el"]
    search_fields = ["nombre"]


@admin.register(Grupo)
class GrupoEnLaTrastienda(admin.ModelAdmin):
    """Lista de grupos, con su organización y su padre."""

    list_display = ["nombre", "organizacion", "padre", "ambito"]
    list_filter = ["organizacion"]
    search_fields = ["nombre"]


@admin.register(Pertenencia)
class PertenenciaEnLaTrastienda(admin.ModelAdmin):
    """Quién está en cada grupo, con su rol."""

    list_display = ["usuario", "grupo", "rol", "es_base", "desde"]
    list_filter = ["rol", "es_base", "grupo__organizacion"]


@admin.register(AdminDeOrganizacion)
class AdminDeOrganizacionEnLaTrastienda(admin.ModelAdmin):
    """Admins de cada organización."""

    list_display = ["usuario", "organizacion", "desde"]


@admin.register(RelacionEntreGrupos)
class RelacionEnLaTrastienda(admin.ModelAdmin):
    """Relaciones libres entre grupos."""

    list_display = ["origen", "tipo", "destino"]


@admin.register(InvitacionDeGrupo)
class InvitacionEnLaTrastienda(admin.ModelAdmin):
    """Invitaciones entre grupos de organizaciones distintas."""

    list_display = ["grupo_que_invita", "grupo_invitado", "ancla_tipo", "ancla_id", "estado", "creada_el"]
    list_filter = ["estado"]
