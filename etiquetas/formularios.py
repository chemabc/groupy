"""
Campo de formulario para poner etiquetas a algo, para los formularios de los demás módulos.
"""

from django.core.exceptions import ValidationError
from django.urls import reverse

from base.formularios import CampoDePalabras, SelectorDePalabras

from .servicios import comprobar_nombre


class CampoDeEtiquetas(CampoDePalabras):
    """
    Etiquetas de algo: el selector de palabras con sugerencias de la organización (y las comunes), que
    comprueba que cada una tiene de una a tres palabras. Al guardar, el módulo llama a
    etiquetas.servicios.etiquetar() con la lista.
    """

    # Prepara el campo.
    #   - organizacion: la organización de lo que se etiqueta (para sugerir sus etiquetas), o None.
    def __init__(self, *args, organizacion=None, **kwargs):
        kwargs.setdefault("label", "Etiquetas")
        kwargs.setdefault("required", False)
        kwargs.setdefault("help_text", "De una a tres palabras cada una, para encontrarlo después. Escribe y pulsa Intro, o elige una sugerencia.")
        super().__init__(*args, **kwargs)
        direccion = reverse("etiquetas:sugerencias")
        if organizacion is not None:
            direccion += f"?organizacion={getattr(organizacion, 'pk', organizacion)}"
        self.widget = SelectorDePalabras(url_de_sugerencias=direccion, forma="frase")

    # Comprueba cada etiqueta y devuelve la lista limpia; junta todos los errores en uno.
    def clean(self, value):
        palabras = super().clean(value)
        errores, limpias = [], []
        for palabra in palabras:
            try:
                limpias.append(comprobar_nombre(palabra))
            except ValidationError as error:
                errores.extend(error.messages)
        if errores:
            raise ValidationError(errores)
        return limpias
