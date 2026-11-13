"""
Formularios del módulo «lugares».
"""

from django import forms

from .models import Lugar, PropuestaDeLugar
from .servicios import CAMPOS


class FormularioDeLugar(forms.ModelForm):
    """Datos de un lugar (alta y cambios del superadmin)."""

    class Meta:
        model = Lugar
        fields = [*CAMPOS, "activo"]
        widgets = {"notas": forms.Textarea(attrs={"rows": 4})}


class FormularioDePropuesta(forms.ModelForm):
    """Propuesta de un lugar nuevo o de un cambio: los datos del lugar y el motivo."""

    class Meta:
        model = PropuestaDeLugar
        fields = [*CAMPOS, "motivo"]
        widgets = {"notas": forms.Textarea(attrs={"rows": 4}), "motivo": forms.Textarea(attrs={"rows": 2})}


class FormularioDeHoja(forms.Form):
    """Subir la hoja con los lugares."""

    fichero = forms.FileField(label="Hoja", help_text="Un .ods (LibreOffice) o .csv con las columnas de la plantilla.")
