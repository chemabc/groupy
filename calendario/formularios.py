"""
Formularios del módulo «calendario».
"""

from datetime import datetime, time

from django import forms
from django.utils import timezone

from .models import Recordatorio

# Opciones de «¿Quién lo ve?» de un recordatorio. Las dos últimas solo para quien tiene
# «calendario.ampliar_recordatorios» en el grupo (la administración); el servicio lo comprueba.
VISIBILIDADES = [
    ("privado", "Solo yo"),
    ("grupo:0", "Mi grupo (y sus subgrupos)"),
    ("grupo:1", "Hasta el grupo padre (solo la administración del grupo)"),
    ("grupo:2", "Hasta el grupo abuelo (solo la administración del grupo)"),
]


class FormularioDeRecordatorio(forms.ModelForm):
    """Datos de un recordatorio: grupo, qué, cuándo y quién lo ve."""

    grupo = forms.TypedChoiceField(label="Grupo", coerce=int, help_text="El grupo en el que lo apuntas.")
    visibilidad = forms.ChoiceField(label="Quién lo ve", choices=VISIBILIDADES, initial="privado", help_text="Todo nace privado.")

    class Meta:
        model = Recordatorio
        fields = ["titulo", "notas", "todo_el_dia", "inicio", "fin"]
        widgets = {
            "notas": forms.Textarea(attrs={"rows": 3}),
            "inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "fin": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    # Prepara el desplegable de grupos y el formato de las fechas.
    #   - grupos: los grupos donde puede apuntarlo (al editar, el grupo no se cambia).
    #   - con_padres: si se ofrecen «hasta el padre» y «hasta el abuelo».
    def __init__(self, *args, grupos, con_padres, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grupo"].choices = [(grupo.pk, f"{grupo.organizacion.nombre} › {grupo.nombre}") for grupo in grupos]
        if not con_padres:
            self.fields["visibilidad"].choices = VISIBILIDADES[:2]
        for campo in ("inicio", "fin"):
            self.fields[campo].input_formats = ["%Y-%m-%dT%H:%M"]

    # Si es de día entero, las horas no cuentan: se dejan a las 00:00 del día.
    def clean(self):
        datos = super().clean()
        if datos.get("todo_el_dia"):
            for campo in ("inicio", "fin"):
                if datos.get(campo):
                    dia = timezone.localtime(datos[campo]).date()
                    datos[campo] = timezone.make_aware(datetime.combine(dia, time()))
        return datos

    # Los datos del recordatorio (sin el grupo ni la visibilidad, que no son campos que se copien tal cual).
    def datos_del_recordatorio(self):
        return {campo: self.cleaned_data[campo] for campo in self.Meta.fields}
