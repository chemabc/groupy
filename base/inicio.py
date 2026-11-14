"""
La portada, «Inicio» (ver docs/diseno.md, apartado 4, «Inicio»): junta las tarjetas que declaran los
módulos (TarjetaDeInicio, en su contrato) en el orden de config/inicio.py, y pide a cada una su resumen.

«base» no importa ningún módulo de más arriba: llama a la función de cada tarjeta por su ruta, como hace
el calendario con sus fuentes. Lo usan las vistas «Inicio → Panel» y «Inicio → Mis datos»
(base/views.py) y la comprobación del arranque (base/comprobaciones.py).
"""

from dataclasses import dataclass

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.module_loading import import_string

from .registro import registro

# Pantallas de Inicio que tienen tarjetas.
PANTALLAS = ("panel", "mis_datos")


@dataclass
class TarjetaPintada:
    """
    Una tarjeta lista para la plantilla: su ficha del contrato y el resumen que ha dado su función.
    """

    # La TarjetaDeInicio del contrato (título, icono, color).
    tarjeta: object
    # El ResumenDeTarjeta que ha devuelto su función.
    resumen: object
    # Su plantilla propia ya pintada (por ejemplo, el árbol de grupos), o vacío si no tiene.
    html: str = ""


# Devuelve la disposición de Inicio (config/inicio.py), buscada por el ajuste DISPOSICION_DEL_INICIO
# porque «base» no importa nada de fuera directamente.
def disposicion_del_inicio():
    return import_string(settings.DISPOSICION_DEL_INICIO)


# Las filas de tarjetas de una pantalla de Inicio para una persona: una lista de filas, y cada fila, una
# lista de TarjetaPintada. Se saltan las tarjetas cuya función devuelve None y las filas que quedan
# vacías. Las consultas son la suma de las de cada tarjeta (cada una hace siempre las mismas).
#   - pantalla: «panel» o «mis_datos».
#   - request: la petición (de ella sale quien mira, y la usan las plantillas propias de las tarjetas).
def filas_de(pantalla, request):
    usuario = request.user
    filas = []
    for fila in disposicion_del_inicio().get(pantalla, ()):
        pintadas = []
        for codigo in fila:
            tarjeta = registro.tarjetas_de_inicio.get(codigo)
            if tarjeta is None:
                continue
            resumen = import_string(tarjeta.funcion)(usuario)
            if resumen is not None:
                html = render_to_string(resumen.plantilla, resumen.contexto, request) if resumen.plantilla else ""
                pintadas.append(TarjetaPintada(tarjeta, resumen, html))
        if pintadas:
            filas.append(pintadas)
    return filas


# Problemas de la disposición de Inicio, como textos: pantallas desconocidas, tarjetas colocadas que
# nadie declara, tarjetas repetidas y tarjetas declaradas que no están colocadas. La usa
# base/comprobaciones.py («python manage.py check», error base.E007).
#   - disposicion: la disposición a revisar (por defecto, la de config/inicio.py).
#   - declaradas: los códigos de las tarjetas declaradas (por defecto, las del registro).
def problemas_de_la_disposicion(disposicion=None, declaradas=None):
    disposicion = disposicion_del_inicio() if disposicion is None else disposicion
    declaradas = set(registro.tarjetas_de_inicio) if declaradas is None else set(declaradas)
    problemas = []
    colocadas = set()
    for pantalla, filas in disposicion.items():
        if pantalla not in PANTALLAS:
            problemas.append(f"La disposición de Inicio tiene una pantalla desconocida: «{pantalla}».")
        for fila in filas:
            for codigo in fila:
                if codigo in colocadas:
                    problemas.append(f"La tarjeta de Inicio «{codigo}» sale dos veces en config/inicio.py.")
                colocadas.add(codigo)
                if codigo not in declaradas:
                    problemas.append(f"config/inicio.py coloca la tarjeta «{codigo}», pero ningún módulo la declara.")
    for codigo in sorted(declaradas - colocadas):
        problemas.append(f"La tarjeta de Inicio «{codigo}» no está colocada en config/inicio.py.")
    return problemas
