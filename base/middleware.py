"""
Capas (middleware) del módulo «base», que pasan por cada petición web.
"""

from django.utils.cache import patch_vary_headers


class VariarSegunHtmx:
    """
    Avisa al navegador de que la misma dirección puede devolver la página entera o solo la zona central,
    según las cabeceras de htmx. Sin este aviso, el navegador podría guardar la zona suelta y mostrarla
    sin menú al volver atrás o al recargar.
    """

    # Django crea la capa una vez al arrancar y le pasa la función que sigue la cadena.
    def __init__(self, get_response):
        self.get_response = get_response

    # Para cada petición: deja que la responda la vista y añade a la respuesta la cabecera «Vary».
    def __call__(self, request):
        respuesta = self.get_response(request)
        patch_vary_headers(respuesta, ["HX-Request", "HX-Target"])
        return respuesta
