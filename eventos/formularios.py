"""
Formularios del módulo «eventos».
"""

from django import forms

from lugares.models import Lugar

from .models import Evento


class FormularioDeEvento(forms.ModelForm):
    """Datos comunes de un evento, quién lo ve y, si es una reunión, por qué (para la solicitud)."""

    visibilidad = forms.ChoiceField(label="Quién lo ve", help_text="Todo nace privado. Las opciones dependen de lo que permite la organización.")
    justificacion = forms.CharField(
        label="Por qué hace falta esta reunión", required=False, widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Solo para las reuniones: lo verán quienes pueden apoyar la solicitud.",
    )

    class Meta:
        model = Evento
        fields = [
            "titulo", "descripcion", "inicio", "duracion", "modalidad", "lugar", "direccion", "url",
            "coste", "coste_detalle", "cartel", "texto_para_redes",
        ]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 4}),
            "texto_para_redes": forms.Textarea(attrs={"rows": 3}),
            "inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "cartel": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }

    # Prepara el desplegable de visibilidad y el de lugares, y quita la justificación si no es reunión.
    #   - visibilidades: (clave, explicación) del selector de audiencias.
    #   - reunion: si el evento es una reunión.
    def __init__(self, *args, visibilidades, reunion, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["visibilidad"].choices = visibilidades
        self.fields["lugar"].queryset = Lugar.objects.filter(activo=True)
        self.fields["inicio"].input_formats = ["%Y-%m-%dT%H:%M"]
        if not reunion:
            del self.fields["justificacion"]

    # Comprueba que un evento presencial dice dónde y uno en línea lleva el enlace.
    def clean(self):
        datos = super().clean()
        if datos.get("modalidad") == Evento.PRESENCIAL and not (datos.get("lugar") or datos.get("direccion")):
            self.add_error("direccion", "Di dónde es: elige un lugar de la lista o escribe la dirección.")
        if datos.get("modalidad") == Evento.EN_LINEA and not datos.get("url"):
            self.add_error("url", "Pon el enlace de la videollamada.")
        return datos

    # Los datos del evento, sin la visibilidad ni la justificación (que no son campos del modelo).
    def datos_del_evento(self):
        return {campo: self.cleaned_data[campo] for campo in self.Meta.fields}
