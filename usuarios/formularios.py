"""
Formularios del módulo «usuarios».
"""

from django.contrib.auth.forms import AuthenticationForm


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
