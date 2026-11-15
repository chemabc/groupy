"""
Formularios del módulo «consultas».
"""

from django import forms

from .models import Consulta, Pregunta


# Cuadro de fecha y hora del navegador (con el formato que entiende).
def _fecha_y_hora():
    return forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")


class FormularioDeConsulta(forms.ModelForm):
    """Crear una consulta: qué, cuándo, quién vota, cuándo y quién ve los resultados y si se puede cambiar el voto."""

    visibilidad = forms.ChoiceField(label="Quién vota", help_text="Quién puede votar (y ve la consulta).")
    visibilidad_resultados = forms.ChoiceField(label="Quién ve los resultados", help_text="Con los niveles de visibilidad de siempre.")

    class Meta:
        model = Consulta
        fields = ["titulo", "descripcion", "abre", "cierra", "resultados", "publicar_el", "secreta", "cambiar_voto"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3}), "abre": _fecha_y_hora(), "cierra": _fecha_y_hora(), "publicar_el": _fecha_y_hora()}

    # Prepara los desplegables de visibilidad con las opciones del grupo.
    #   - visibilidades: opciones del selector de audiencias del grupo elegido.
    def __init__(self, *args, visibilidades, **kwargs):
        super().__init__(*args, **kwargs)
        sin_privado = [(c, t) for c, t in visibilidades if c != "privado"]
        self.fields["visibilidad"].choices = sin_privado
        self.fields["visibilidad_resultados"].choices = sin_privado


class FormularioDePregunta(forms.Form):
    """Añadir una pregunta a una consulta que aún se prepara."""

    texto = forms.CharField(label="Pregunta", max_length=300)
    tipo = forms.ChoiceField(label="Tipo", choices=Pregunta.TIPOS)
    respuestas = forms.CharField(
        label="Respuestas posibles", required=False, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Una por línea (al menos dos). Las de respuesta abierta no llevan.",
    )
    documentacion = forms.CharField(
        label="Documentación", required=False, widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Lo que hay que saber para responder, con enlaces a documentos (Markdown).",
    )
