"""
Formularios del módulo «documentos».
"""

from django import forms

from .models import Documento


class FormularioDeDocumentoNuevo(forms.Form):
    """
    Crear un documento: tipo, título y, si no cuelga de nada, quién lo ve (el grupo se elige antes, arriba
    de la pantalla). Si cuelga de algo (una reunión), toma su grupo y su visibilidad, y ese campo no sale.
    """

    tipo = forms.ChoiceField(label="Tipo", choices=Documento.TIPOS, help_text="El acta se crea mejor desde su orden del día, que copia los puntos.")
    titulo = forms.CharField(label="Título", max_length=200, help_text="«Orden del día de la asamblea del jueves».")
    visibilidad = forms.ChoiceField(label="Quién lo ve", help_text="Todo nace privado. Quien lo ve puede leerlo y comentarlo.")

    # Prepara el desplegable de visibilidad.
    #   - visibilidades: opciones del selector de audiencias del grupo elegido, o None si cuelga de algo.
    def __init__(self, *args, visibilidades, **kwargs):
        super().__init__(*args, **kwargs)
        if visibilidades is None:
            del self.fields["visibilidad"]
        else:
            self.fields["visibilidad"].choices = visibilidades
