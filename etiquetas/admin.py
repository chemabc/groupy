"""
Etiquetas en la trastienda (el panel de Django): ver, renombrar, poner palabras relacionadas y fusionar
repetidas.
"""

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Count

from base.trastienda import ConAyuda

from .models import Etiqueta
from .servicios import fusionar


@admin.register(Etiqueta)
class EtiquetaEnLaTrastienda(ConAyuda, admin.ModelAdmin):
    """Etiquetas de todas las organizaciones y las comunes."""

    ayuda = (
        "Etiquetas: palabras de una a tres para encontrar las cosas. Cada organización tiene las suyas (no "
        "se ven en las demás) y las «comunes» (sin organización) sirven en todas.\n\n"
        "Se puede: renombrar una etiqueta, ponerle palabras relacionadas (sinónimos: al buscar cualquiera de "
        "ellas aparece la etiqueta) y fusionar repetidas: márcalas en la lista y elige la acción «Fusionar». "
        "Se queda la más usada; las demás pasan a ser palabras relacionadas suyas."
    )
    list_display = ["nombre", "de_quien", "relacionadas", "numero_de_usos", "creada_el"]
    list_filter = [("organizacion", admin.EmptyFieldListFilter), "organizacion"]
    search_fields = ["normalizada", "relacionadas_normalizadas"]
    fields = ["organizacion", "nombre", "relacionadas"]
    actions = ["fusionar_seleccionadas"]

    # Añade el número de usos a cada fila, en la misma consulta.
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("organizacion").annotate(usos_totales=Count("usos"))

    # Columna «de quién»: la organización o «común».
    @admin.display(description="de quién", ordering="organizacion__nombre")
    def de_quien(self, etiqueta):
        return etiqueta.organizacion or "Común"

    # Columna «usos».
    @admin.display(description="usos", ordering="usos_totales")
    def numero_de_usos(self, etiqueta):
        return etiqueta.usos_totales

    # Acción de la lista: fusiona las etiquetas marcadas en la más usada.
    @admin.action(description="Fusionar las etiquetas marcadas (se queda la más usada)")
    def fusionar_seleccionadas(self, request, consulta):
        etiquetas = sorted(consulta, key=lambda etiqueta: -etiqueta.usos_totales)
        if len(etiquetas) < 2:
            self.message_user(request, "Marca al menos dos etiquetas para fusionarlas.", messages.WARNING)
            return
        try:
            destino = fusionar(etiquetas[0], etiquetas[1:])
        except ValidationError as error:
            self.message_user(request, " ".join(error.messages), messages.ERROR)
        else:
            self.message_user(request, f"Fusionadas en «{destino}». Palabras relacionadas: {destino.relacionadas}.")
