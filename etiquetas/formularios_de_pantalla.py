"""
Formularios de la pantalla «Administrar → Mi organización → Etiquetas» (etiquetas/views.py, etiquetas). Los del
selector de etiquetas, que usan los demás módulos, están en etiquetas/formularios.py.
"""

from django import forms


class FormularioDeEtiqueta(forms.Form):
    """Etiqueta nueva o cambiada: nombre y palabras relacionadas."""

    nombre = forms.CharField(
        label="Etiqueta", max_length=40,
        help_text="De una a tres palabras. Se guarda con la primera letra en mayúscula, el resto en minúsculas y sin tildes.",
    )
    relacionadas = forms.CharField(
        label="Palabras relacionadas", required=False,
        help_text="Sinónimos o palabras parecidas, separadas por comas. Al buscar cualquiera de ellas, aparece esta etiqueta.",
    )
