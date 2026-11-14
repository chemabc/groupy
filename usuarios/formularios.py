"""
Formularios del módulo «usuarios».
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Usuario


class FormularioDeEntrada(AuthenticationForm):
    """
    Formulario de la pantalla de entrada: alias y contraseña. Es el de Django, con explicaciones y sin
    botón «copiar» en el alias (en la entrada no tiene sentido).
    """

    # Ajusta los campos al crear el formulario.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Alias"
        self.fields["username"].help_text = "Da igual escribirlo con o sin mayúsculas y tildes."
        # data-sin-copiar: base/formularios.py no le pone el botón «copiar».
        self.fields["username"].widget.attrs["data-sin-copiar"] = ""
        self.fields["password"].help_text = "Si la has olvidado, pídele una nueva al superadmin."


class FormularioDeCorreo(forms.ModelForm):
    """
    Formulario de «Configuración de mi cuenta → Mis datos → Datos» para cambiar el correo alternativo, el
    único dato de la cuenta que cada persona cambia por sí misma. Se puede dejar vacío.
    """

    class Meta:
        model = Usuario
        fields = ["correo_alternativo"]
