"""
Ayuda para las pantallas de la trastienda (el panel de Django).

La trastienda es solo para emergencias técnicas del superadmin (docs/diseno.md, apartado 4), pero
debe entenderse sin conocer el código. ConAyuda añade a la lista y a la ficha de cada tabla un texto
que explica qué muestra la pantalla y qué se puede gestionar en ella. Lo usan los admin.py de cada
módulo.
"""


class ConAyuda:
    """
    Añadido para cualquier ModelAdmin: muestra el texto de «ayuda» encima de la lista y de la ficha. Se
    pone delante en la herencia: class UsuarioEnLaTrastienda(ConAyuda, admin.ModelAdmin).
    """

    # Texto que explica la pantalla. Los saltos de línea dobles separan párrafos.
    ayuda = ""
    # Plantillas que pintan la ayuda y después la pantalla normal de Django.
    change_list_template = "trastienda/lista.html"
    change_form_template = "trastienda/ficha.html"

    # Lista de la tabla: añade la ayuda a los datos de la plantilla.
    def changelist_view(self, request, extra_context=None):
        return super().changelist_view(request, {**(extra_context or {}), "ayuda": self.ayuda})

    # Ficha (crear o editar): añade la ayuda a los datos de la plantilla.
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        return super().changeform_view(request, object_id, form_url, {**(extra_context or {}), "ayuda": self.ayuda})
