"""
Formularios de la sección «Solicitudes» y de «Administrar → Mi organización → Apoyos y plazos».
"""

from django import forms


class FormularioDeSolicitud(forms.Form):
    """Solicitud nueva de un tipo genérico (solo con descripción y justificación), a un grupo."""

    tipo = forms.ChoiceField(label="Qué pides", help_text="Por ahora, entrar en un grupo. Los debates y las reuniones se piden desde su sección.")
    grupo = forms.TypedChoiceField(label="A qué grupo", coerce=int, help_text="El grupo al que se lo pides. Lo verán sus miembros.")
    descripcion = forms.CharField(
        label="Qué pides", widget=forms.Textarea(attrs={"rows": 2}), help_text="En una o dos frases: «Quiero entrar en la asamblea de mi barrio»."
    )
    justificacion = forms.CharField(
        label="Por qué", required=False, widget=forms.Textarea(attrs={"rows": 3}), help_text="Lo que ayude a los demás a decidir."
    )

    # Prepara los desplegables.
    #   - tipos: (código, nombre) de los tipos que se piden desde aquí.
    #   - grupos: (id, «ORG › camino») de los grupos posibles.
    def __init__(self, *args, tipos, grupos, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].choices = tipos
        self.fields["grupo"].choices = [("", "---------"), *grupos]


class FormularioDeAjuste(forms.Form):
    """Apoyos y días de un tipo de solicitud."""

    apoyos = forms.IntegerField(label="Apoyos", min_value=0, max_value=500, help_text="Apoyos de miembros del grupo que hacen falta.")
    dias = forms.IntegerField(label="Días", min_value=1, max_value=365, help_text="Días para conseguirlos antes de caducar.")
