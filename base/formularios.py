"""
Cómo se pintan los formularios en toda la aplicación.

FORM_RENDERER (config/settings.py) apunta a Renderizador, así que todos los campos de todos los
formularios se pintan con base/templates/base/campo.html: etiqueta, campo, botón «copiar», explicación
(help_text) y errores. Ningún formulario tiene que hacer nada para tenerlo.
"""

import json

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

    # Si el campo lleva botón «copiar»: todos, salvo los tipos de NO_SE_COPIAN y los que lo desactivan
    # a propósito con el atributo «data-sin-copiar» (por ejemplo, el alias de la pantalla de entrada).
    @property
    def se_puede_copiar(self):
        widget = self.field.widget
        return not isinstance(widget, NO_SE_COPIAN) and "data-sin-copiar" not in widget.attrs


class Renderizador(DjangoTemplates):
    """
    Pintor de formularios de la aplicación: el de Django, con nuestra plantilla de campo y nuestra clase
    de campo ligado.
    """

    # Plantilla con la que se pinta cada campo.
    field_template_name = "base/campo.html"
    # Clase que Django usa para cada campo de cada formulario.
    bound_field_class = CampoLigado


class SelectorDePalabras(forms.Widget):
    """
    Cuadro para escribir varias palabras cortas (por ejemplo, etiquetas) que se ven como «pastillas» con
    una ×, con sugerencias mientras se escribe. Lo mueve el componente «selectorDePalabras» de
    base/static/base/interfaz.js; cada palabra se envía en un campo oculto con el nombre del campo. No
    lleva botón «copiar».
    """

    template_name = "base/selector_de_palabras.html"

    # Prepara el cuadro.
    #   - url_de_sugerencias: dirección que devuelve las sugerencias en JSON ({"sugerencias": [{"nombre",
    #     "comun"}]}); se le añade «q» con lo escrito. Puede llevar ya otros parámetros (?organizacion=3).
    #   - forma: «frase» para que cada palabra se pase, al añadirla, a la forma de las etiquetas (primera
    #     letra en mayúscula, el resto en minúsculas y sin tildes); vacío para dejarla como se escribe.
    def __init__(self, url_de_sugerencias="", attrs=None, forma=""):
        super().__init__({"data-sin-copiar": "", **(attrs or {})})
        self.url_de_sugerencias = url_de_sugerencias
        self.forma = forma

    # Datos para la plantilla: las palabras actuales (en JSON), la dirección de las sugerencias y la forma.
    def get_context(self, name, value, attrs):
        contexto = super().get_context(name, value, attrs)
        contexto["widget"]["valores_json"] = json.dumps(list(value or []), ensure_ascii=False)
        contexto["widget"]["url"] = str(self.url_de_sugerencias)
        contexto["widget"]["forma"] = self.forma
        return contexto

    # Lo que llega del navegador: una lista con las palabras (un campo oculto por palabra).
    def value_from_datadict(self, data, files, name):
        return data.getlist(name) if hasattr(data, "getlist") else data.get(name, [])


class CampoDePalabras(forms.Field):
    """
    Campo con varias palabras cortas (el SelectorDePalabras). Devuelve la lista sin espacios de más ni
    repetidas (sin contar mayúsculas ni tildes). Los módulos pueden heredarlo para comprobar más cosas.
    """

    widget = SelectorDePalabras

    # Convierte lo recibido en la lista limpia de palabras.
    def to_python(self, value):
        from .tablas import normalizar

        vistas, palabras = set(), []
        for palabra in value or []:
            palabra = " ".join(str(palabra).split())
            if palabra and normalizar(palabra) not in vistas:
                vistas.add(normalizar(palabra))
                palabras.append(palabra)
        return palabras
