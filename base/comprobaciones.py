"""
Comprobaciones del contrato de módulo, dentro del sistema de comprobaciones de Django.

Django ejecuta estas comprobaciones al arrancar el servidor, al pasar las pruebas y con
«python manage.py check». Si un módulo declara algo mal (un código repetido, una función que no
existe…), el error sale ahí, con un texto que dice qué falla y dónde, en lugar de estallar más tarde en
mitad de una pantalla.
"""

from django.apps import apps
from django.core import checks
from django.urls import NoReverseMatch, URLPattern, URLResolver, get_resolver, reverse
from django.utils.module_loading import import_string

from .registro import registro


# Comprobación principal: devuelve un error de Django por cada problema del contrato. Django la llama
# solo, porque está registrada con @checks.register (etiqueta «contrato»).
#   - app_configs: si se piden solo algunas apps, Django las pasa aquí. Se ignora: el contrato se
#     comprueba siempre entero, porque los errores suelen cruzar módulos.
@checks.register("contrato")
def comprobar_contrato(app_configs=None, **kwargs):
    errores = [checks.Error(texto, id="base.E001") for texto in registro.errores]
    errores += _comprobar_funciones()
    errores += _comprobar_modelos()
    errores += _comprobar_direcciones()
    return errores


# Comprueba que existen todas las funciones que los módulos indican como texto (receptores de
# eventos_sw, fuentes del calendario y datos de ejemplo). Importarlas aquí, una vez al arrancar, evita
# descubrir la errata el día que se emite el eventos_sw.
def _comprobar_funciones():
    rutas = [escucha.receptor for lista in registro.escuchas.values() for escucha in lista]
    rutas += [fuente.funcion for fuente in registro.fuentes_de_calendario.values()]
    for datos in registro.datos_de_ejemplo.values():
        rutas += [datos.crear, datos.borrar]
    errores = []
    for ruta in rutas:
        try:
            import_string(ruta)
        except ImportError:
            errores.append(checks.Error(f"No se encuentra la función «{ruta}».", id="base.E002"))
    return errores


# Comprueba que existen los modelos que se nombran como texto en las anclas y en los elementos limpiables.
def _comprobar_modelos():
    modelos = [ancla.modelo for ancla in registro.anclas.values()]
    modelos += [limpiable.modelo for limpiable in registro.limpiables.values()]
    errores = []
    for modelo in modelos:
        try:
            apps.get_model(modelo)
        except (LookupError, ValueError):
            errores.append(checks.Error(f"No existe el modelo «{modelo}».", id="base.E003"))
    return errores


# Comprueba que existen las direcciones web a las que llevan las entradas y las vistas del menú. Si un
# módulo escribe mal el nombre de una ruta, se ve aquí y no al pintar el menú. Las entradas y las vistas
# deben poder abrirse sin datos (reverse sin parámetros); las «otras_rutas» (fichas, que llevan un
# número), basta con que existan.
def _comprobar_direcciones():
    errores = []
    existentes = set(_nombres_de_rutas(get_resolver()))
    sin_parametros = {
        url for entrada in registro.menu for url in _direcciones_sin_parametros(entrada)
    }
    for url in registro.rutas:
        if url not in existentes:
            errores.append(checks.Error(f"El menú lleva a «{url}», pero esa dirección no existe.", id="base.E004"))
            continue
        if url in sin_parametros:
            try:
                reverse(url)
            except NoReverseMatch:
                errores.append(checks.Error(f"El menú lleva a «{url}», que pide datos en la dirección: va en «otras_rutas».", id="base.E004"))
    return errores


# Direcciones de una entrada del menú, de sus vistas y de sus subsecciones (no sus «otras_rutas»), que
# deben poder abrirse sin datos.
def _direcciones_sin_parametros(entrada):
    yield entrada.url
    yield from (vista.url for vista in entrada.vistas)
    for subseccion in entrada.subsecciones:
        yield from _direcciones_sin_parametros(subseccion)


# Nombres completos de todas las rutas de la aplicación («grupos:grupo»), recorriendo las listas de
# direcciones incluidas con su espacio de nombres.
#   - resolutor: la lista de direcciones (al principio, la general de config/urls.py).
#   - prefijo: el espacio de nombres acumulado («grupos:»).
def _nombres_de_rutas(resolutor, prefijo=""):
    for patron in resolutor.url_patterns:
        if isinstance(patron, URLResolver):
            espacio = f"{prefijo}{patron.namespace}:" if patron.namespace else prefijo
            yield from _nombres_de_rutas(patron, espacio)
        elif isinstance(patron, URLPattern) and patron.name:
            yield f"{prefijo}{patron.name}"
