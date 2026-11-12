"""
Cómo se pintan los formularios en toda la aplicación.

FORM_RENDERER (config/settings.py) apunta a Renderizador, así que todos los campos de todos los
formularios se pintan con base/templates/base/campo.html: etiqueta, campo, botón «copiar», explicación
(help_text) y errores. Ningún formulario tiene que hacer nada para tenerlo.
"""

from django import forms
from django.forms.renderers import DjangoTemplates

# Tipos de campo que no llevan botón «copiar»: casillas y opciones (no tienen un texto que copiar),
# ficheros, contraseñas (no conviene dejarlas en el portapapeles) y campos ocultos.
NO_SE_COPIAN = (
    forms.CheckboxInput,
    forms.RadioSelect,
    forms.CheckboxSelectMultiple,
    forms.FileInput,
    forms.PasswordInput,
    forms.HiddenInput,
)


class CampoLigado(forms.BoundField):
    """
    Un campo de un formulario concreto (el «BoundField» de Django), con lo que la plantilla necesita
    saber y que no debe decidir ella.
    """

    # Si el campo lleva botón «copiar».
    @property
    def se_puede_copiar(self):
        return not isinstance(self.field.widget, NO_SE_COPIAN)


class Renderizador(DjangoTemplates):
    """
    Pintor de formularios de la aplicación: el de Django, con nuestra plantilla de campo y nuestra clase
    de campo ligado.
    """

    # Plantilla con la que se pinta cada campo.
    field_template_name = "base/campo.html"
    # Clase que Django usa para cada campo de cada formulario.
    bound_field_class = CampoLigado
