"""
Notificaciones del módulo «limpieza» (las reparte «comunicaciones»; ver limpieza/apps.py). Llegan a
quienes ven lo archivado: una sola notificación por persona, con cuántos elementos son.
"""

from collections import Counter, defaultdict

from django.urls import reverse

from audiencias.servicios import personas_de
from base.contrato import AvisoPreparado

from .models import Archivado
from .servicios import AVISO_PREVIO


# Cuántos de unos elementos archivados ve cada persona: {id de la persona: cuántos}. Una consulta, más
# una por cada audiencia distinta.
#   - archivados: ids de filas de Archivado.
def _cuantos_por_persona(archivados):
    por_audiencia, audiencias = Counter(), {}
    for fila in Archivado.objects.filter(pk__in=archivados, audiencia__isnull=False).select_related("audiencia"):
        por_audiencia[fila.audiencia_id] += 1
        audiencias[fila.audiencia_id] = fila.audiencia
    cuantos = Counter()
    for audiencia_id, numero in por_audiencia.items():
        for persona in personas_de(audiencias[audiencia_id]) or ():
            cuantos[persona] += numero
    return cuantos


# Agrupa a las personas por el número de elementos que les tocan, para preparar un aviso por número.
#   - cuantos: {persona: número}.
#   - redactar: función que recibe el número y devuelve el texto.
#   - enlace: adónde lleva el aviso.
def _preparar(cuantos, redactar, enlace):
    por_numero = defaultdict(list)
    for persona, numero in cuantos.items():
        por_numero[numero].append(persona)
    return [AvisoPreparado(tuple(personas), redactar(numero), enlace) for numero, personas in sorted(por_numero.items())]


# «Se han archivado 3 elementos que ves…». A quienes los ven.
def archivados(archivados, **resto):
    def redactar(numero):
        if numero == 1:
            return "Se ha archivado un elemento que ves: sale de las listas y se borrará más adelante si nadie lo conserva."
        return f"Se han archivado {numero} elementos que ves: salen de las listas y se borrarán más adelante si nadie los conserva."

    return _preparar(_cuantos_por_persona(archivados), redactar, reverse("limpieza:archivados"))


# «Dentro de 15 días se borrarán 2 elementos archivados que ves…». A quienes los ven.
def se_borraran(archivados, **resto):
    def redactar(numero):
        cuales = "un elemento archivado" if numero == 1 else f"{numero} elementos archivados"
        verbo = "se borrará" if numero == 1 else "se borrarán"
        return f"Dentro de {AVISO_PREVIO} días {verbo} {cuales} que ves. Si quieres guardar algo, pulsa «Conservar» en el archivo."

    return _preparar(_cuantos_por_persona(archivados), redactar, reverse("limpieza:archivados") + "?pronto=1")
