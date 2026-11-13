"""
Formularios del módulo «limpieza».
"""

from django import forms


class FormularioDePlazo(forms.Form):
    """Los plazos de un tipo de elemento en «Configuración → Limpieza»."""

    activo = forms.BooleanField(label="Activo", required=False, help_text="Si se limpia este tipo. Sin marcar: no se archiva ni se borra nada de él.")
    archivar_a = forms.IntegerField(
        label="Días hasta archivar", min_value=1, max_value=36500, required=False,
        help_text="Días desde que terminó hasta archivarlo (sale de las listas).",
    )
    borrar_a = forms.IntegerField(
        label="Días hasta borrar", min_value=1, max_value=36500,
        help_text="Días desde que se archivó hasta borrarlo (o desde que terminó, si se borra sin archivar).",
    )
