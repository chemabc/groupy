"""
Formularios del módulo «debates».
"""

from django import forms

from .models import LimitesDeDebate


class FormularioDeDebate(forms.Form):
    """
    Proponer un debate: la pregunta, el contexto, las opciones de partida (una por línea), cuándo se cierra,
    quién participa (si no cuelga de nada) y por qué (para la solicitud de apoyos).
    """

    pregunta = forms.CharField(label="Pregunta", max_length=300, help_text="Lo que se debate: «¿Dónde hacemos el huerto?».")
    descripcion = forms.CharField(label="Contexto", required=False, widget=forms.Textarea(attrs={"rows": 3}), help_text="Lo que hay que saber para debatir (Markdown).")
    opciones = forms.CharField(
        label="Opciones", widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Una por línea, al menos dos. Después se pueden proponer más.",
    )
    cierra = forms.DateTimeField(
        label="Se cierra", required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        help_text="Cuándo termina. Opcional, salvo que tu organización lo pida.",
    )
    visibilidad = forms.ChoiceField(label="Quién participa", help_text="Quién lo ve y puede intervenir. Después se puede ampliar, nunca reducir.")
    justificacion = forms.CharField(label="Por qué", required=False, widget=forms.Textarea(attrs={"rows": 2}), help_text="Para quien apoya la solicitud de abrirlo.")

    # Prepara el desplegable de visibilidad (sin él si cuelga de algo, que le da su audiencia).
    #   - visibilidades: opciones del selector del grupo elegido, o None.
    def __init__(self, *args, visibilidades, **kwargs):
        super().__init__(*args, **kwargs)
        if visibilidades is None:
            del self.fields["visibilidad"]
        else:
            self.fields["visibilidad"].choices = [(clave, texto) for clave, texto in visibilidades if clave != "privado"]

    # Las opciones escritas, una por línea, sin vacías.
    def lista_de_opciones(self):
        return [linea.strip() for linea in self.cleaned_data["opciones"].splitlines() if linea.strip()]


class FormularioDeLimites(forms.ModelForm):
    """Los límites de los debates de la plataforma o de una organización (vacío: sin límite en este nivel)."""

    class Meta:
        model = LimitesDeDebate
        fields = [
            "palabras_blando", "palabras_duro", "intervenciones_blando", "intervenciones_duro",
            "opciones_por_persona", "apoyos_para_opcion", "fin_obligatorio",
        ]
