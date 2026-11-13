"""
Tipologías en la trastienda (el panel de Django): solo para emergencias. El trabajo diario se hace en
«Configuración → Tipologías».
"""

from django.contrib import admin

from base.trastienda import ConAyuda

from .models import Campo, Tipologia


class CampoDentroDeLaTipologia(admin.TabularInline):
    """Los campos de una tipología, dentro de su ficha."""

    model = Campo
    extra = 0
    fields = ["nombre", "tipo", "obligatorio", "ayuda", "opciones", "orden"]


@admin.register(Tipologia)
class TipologiaEnLaTrastienda(ConAyuda, admin.ModelAdmin):
    """Tipologías de proyectos y de eventos, comunes y de cada organización, con sus campos."""

    ayuda = (
        "Tipologías: los tipos de proyecto y de evento, en árbol, con los campos que pide cada uno. Un subtipo "
        "pide también los campos de su tipo.\n\n"
        "Lo normal es cambiarlas en «Configuración → Tipologías», que comprueba quién puede tocar cada una. "
        "Aquí no se comprueba: úsalo solo para arreglar algo que no se pueda hacer desde allí."
    )
    list_display = ["nombre", "familia", "padre", "de_quien"]
    list_filter = ["familia", ("organizacion", admin.EmptyFieldListFilter), "organizacion"]
    search_fields = ["nombre"]
    fields = ["familia", "padre", "organizacion", "nombre", "descripcion"]
    inlines = [CampoDentroDeLaTipologia]

    # Carga el padre y la organización en la misma consulta que la lista.
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("padre", "organizacion")

    # Columna «de quién»: la organización o «Común».
    @admin.display(description="de quién", ordering="organizacion__nombre")
    def de_quien(self, tipologia):
        return tipologia.organizacion or "Común"
