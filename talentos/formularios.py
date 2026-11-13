"""
Formularios del módulo «talentos».
"""

from django import forms

from .models import Talento

# Cuántas filas de «talento que hace falta» tiene el formulario de petición.
FILAS_DE_NECESIDADES = 5


class FormularioDeTalento(forms.Form):
    """Añadir un talento propio."""

    nombre = forms.CharField(
        label="Talento", max_length=60, widget=forms.TextInput(attrs={"list": "catalogo-de-talentos", "autocomplete": "off"}),
        help_text="Escríbelo: te propondremos los del catálogo para no repetirlos.",
    )
    tipo = forms.ChoiceField(label="Tipo", choices=Talento.TIPOS, help_text="Si es nuevo en el catálogo: algo que tienes o algo que sabes hacer.")
    detalle = forms.CharField(label="Detalle", max_length=200, required=False, help_text="Algo más, opcional («furgoneta de 9 plazas»).")


class FormularioDePeticion(forms.Form):
    """Petición de talentos a un grupo: para qué y qué hace falta (hasta cinco talentos con su número)."""

    grupo = forms.TypedChoiceField(label="A qué grupo", coerce=int, help_text="Llega a quienes comparten los talentos con ese grupo o sus subgrupos.")
    asunto = forms.CharField(label="Para qué", max_length=120, help_text="En pocas palabras: «Mudanza del local».")
    descripcion = forms.CharField(label="Descripción", required=False, widget=forms.Textarea(attrs={"rows": 3}), help_text="Cuándo, dónde y lo que haga falta saber.")

    # Prepara el desplegable de grupos y añade las filas de talentos («talento_1», «cantidad_1»…).
    #   - grupos: (id, «ORG › camino») de los grupos donde puede pedir.
    def __init__(self, *args, grupos, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grupo"].choices = grupos
        for numero in range(1, FILAS_DE_NECESIDADES + 1):
            self.fields[f"talento_{numero}"] = forms.CharField(
                label=f"Talento {numero}", max_length=60, required=numero == 1,
                widget=forms.TextInput(attrs={"list": "catalogo-de-talentos", "autocomplete": "off"}),
                help_text="Uno del catálogo (o nuevo)." if numero == 1 else "",
            )
            self.fields[f"cantidad_{numero}"] = forms.IntegerField(label="Cuántos", min_value=1, max_value=999, initial=1, required=False)

    # Lista de (nombre del talento, cantidad) de las filas rellenas.
    def necesidades(self):
        filas = []
        for numero in range(1, FILAS_DE_NECESIDADES + 1):
            nombre = (self.cleaned_data.get(f"talento_{numero}") or "").strip()
            if nombre:
                filas.append((nombre, self.cleaned_data.get(f"cantidad_{numero}") or 1))
        return filas
