"""
Cómo se pintan los formularios en toda la aplicación.

FORM_RENDERER (config/settings.py) apunta a Renderizador, así que todos los campos de todos los
formularios se pintan con base/templates/base/campo.html: etiqueta, campo, botón «copiar», explicación
(help_text) y errores. Ningún formulario tiene que hacer nada para tenerlo.
"""

import json

from django import forms
from django.db.models import Q
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


class SelectorDePersonas(forms.Widget):
    """
    Selector de personas (por ejemplo, quién se encarga de una tarea y quién colabora): las elegidas se ven
    como pastillas con una ×, y el botón «Elegir…» abre una ventana con las personas que ven aquello,
    ordenadas por cercanía (primero el propio grupo, después sus subgrupos y luego, nivel a nivel, los de
    más arriba), con un buscador que filtra mientras se escribe. Lo mueve el componente
    «selectorDePersonas» de base/static/base/interfaz.js; cada alias elegido se envía en un campo oculto
    con el nombre del campo. La lista la pide la ventana al abrirse (no cuesta nada si no se abre).

    El módulo que lo usa da la dirección que devuelve la lista (en JSON, de
    audiencias.cercania.Cercania.como_datos). Si quien elige no puede ver la lista (su organización la ha
    cerrado), la ventana solo deja escribir el alias exacto.
    """

    template_name = "base/selector_de_personas.html"

    # Prepara el selector.
    #   - url_de_la_lista: dirección que devuelve la lista en JSON.
    #   - varias: si se pueden elegir varias personas (colaboradoras) o solo una (responsable).
    #   - parametros: nombres de otros campos del mismo formulario cuyo valor se añade a la dirección al
    #     pedir la lista (por ejemplo, «visibilidad»: la lista cambia según quién lo vaya a ver).
    #   - vacio: texto que se ve cuando no hay nadie elegido («Tú, si no eliges a nadie»).
    def __init__(self, url_de_la_lista="", varias=False, parametros=(), vacio="Nadie", attrs=None):
        super().__init__({"data-sin-copiar": "", **(attrs or {})})
        self.url_de_la_lista = url_de_la_lista
        self.varias = varias
        self.parametros = tuple(parametros)
        self.vacio = vacio

    # Datos para la plantilla: los alias elegidos (en JSON), la dirección, si son varias, los parámetros y
    # el texto de vacío.
    def get_context(self, name, value, attrs):
        contexto = super().get_context(name, value, attrs)
        if isinstance(value, str):
            value = [value] if value else []
        contexto["widget"].update(
            valores_json=json.dumps([str(alias) for alias in value or []], ensure_ascii=False),
            url=str(self.url_de_la_lista),
            varias=self.varias,
            parametros=" ".join(self.parametros),
            vacio=self.vacio,
        )
        return contexto

    # Lo que llega del navegador: la lista de alias (un campo oculto por persona).
    def value_from_datadict(self, data, files, name):
        return data.getlist(name) if hasattr(data, "getlist") else data.get(name, [])


class CampoDePersonas(forms.Field):
    """
    Campo con una o varias personas, elegidas con el SelectorDePersonas. Convierte los alias en personas
    y comprueba que estén entre las que pueden elegirse («permitidas»: las que ven aquello). El error es
    el mismo exista o no el alias, para no dar pistas de quién hay fuera. Devuelve una persona (o None)
    si es de una sola, o una lista si son varias.
    """

    # Prepara el campo.
    #   - varias: como en SelectorDePersonas.
    #   - permitidas: función sin parámetros que devuelve los ids de las personas que se pueden elegir. Es
    #     una función para que solo se calcule al comprobar lo enviado. La pone el formulario del módulo.
    #   - url_de_la_lista, parametros, vacio: para el selector.
    #   - error_fuera: el principio del error si alguien no se puede elegir (le siguen los alias).
    def __init__(
        self, *args, varias=False, permitidas=None, url_de_la_lista="", parametros=(), vacio="Nadie",
        error_fuera="No está entre quienes ven esto", **kwargs,
    ):
        kwargs.setdefault("widget", SelectorDePersonas(url_de_la_lista, varias=varias, parametros=parametros, vacio=vacio))
        super().__init__(*args, **kwargs)
        self.varias = varias
        self.permitidas = permitidas
        self.error_fuera = error_fuera

    # Convierte la lista de alias recibida en personas, sin repetidas. Una consulta (más la de permitidas).
    def to_python(self, value):
        from django.contrib.auth import get_user_model

        alias = []
        for uno in value or []:
            uno = str(uno).strip()
            if uno and uno.lower() not in {a.lower() for a in alias}:
                alias.append(uno)
        if not self.varias and len(alias) > 1:
            raise forms.ValidationError("Elige solo una persona.")
        if not alias:
            return [] if self.varias else None
        modelo = get_user_model()
        campo = modelo.USERNAME_FIELD
        condicion = Q()
        for uno in alias:
            condicion |= Q(**{f"{campo}__iexact": uno})
        encontradas = {getattr(persona, campo).lower(): persona for persona in modelo._default_manager.filter(condicion)}
        permitidas = self.permitidas() if self.permitidas is not None else None
        fuera = [uno for uno in alias if uno.lower() not in encontradas or (permitidas is not None and encontradas[uno.lower()].pk not in permitidas)]
        if fuera:
            raise forms.ValidationError(f"{self.error_fuera}: {', '.join(fuera)}.")
        personas = [encontradas[uno.lower()] for uno in alias]
        return personas if self.varias else personas[0]

    # Lo que se vuelve a pintar en el selector: los alias (también si llega una persona o una lista).
    def prepare_value(self, value):
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return [getattr(uno, "get_username", lambda uno=uno: uno)() for uno in value]
        return [getattr(value, "get_username", lambda: value)()]
