"""
Tipologías de ejemplo, con campos: las del diseño (apartado 9) y un subtipo propio de «ORG Tajo»; y las
tareas modelo de «Preparación de acción». Las crea y las borra la orden «python manage.py ejemplos».
"""

from django.db.models import Q

from grupos.models import Organizacion

from .models import Campo, Tipologia
from .servicios import crear_campo, crear_tarea_modelo, crear_tipologia

# Árbol común de ejemplo: familia → [(nombre, [campos (nombre, tipo, opciones)], [subtipos])].
COMUNES = {
    Tipologia.EVENTO: [
        ("Reunión", [("Orden del día previsto", Campo.TEXTO_LARGO, "")], []),
        (
            "Acción",
            [
                ("Número de asistentes previstos", Campo.NUMERO, ""),
                ("Material necesario", Campo.TEXTO_LARGO, ""),
                ("Requiere permiso municipal", Campo.SI_NO, ""),
            ],
            [("Concentración", [("Lugar de encuentro", Campo.TEXTO, ""), ("Tipo de convocatoria", Campo.LISTA, "Abierta\nSolo afiliación")], [])],
        ),
        ("Recaudatorio", [("Objetivo en euros", Campo.NUMERO, ""), ("Fecha límite", Campo.FECHA, "")], []),
        ("Genérico", [], []),
    ],
    Tipologia.PROYECTO: [
        ("Comunicación", [("Canal principal", Campo.LISTA, "Redes\nCarteles\nPrensa")], []),
        ("Tecnología", [], []),
        ("Preparación de acción", [("Fecha de la acción", Campo.FECHA, "")], []),
        ("Genérico", [], []),
    ],
}

# Tareas modelo de ejemplo de cada tipo común de proyecto: (título, días, espera a la anterior).
TAREAS_MODELO = {
    "Preparación de acción": [
        ("Pedir permiso al distrito", 7, False),
        ("Preparar el material", 14, True),
        ("Difundir la convocatoria", 21, True),
    ],
}


# Crea el árbol común (si no existe ya «Reunión») y el subtipo «Acción de barrio» de ORG Tajo.
def crear():
    if not Tipologia.objects.filter(organizacion__isnull=True, familia=Tipologia.EVENTO, nombre="Reunión").exists():
        for familia, ramas in COMUNES.items():
            _crear_ramas(familia, ramas, None)
    tajo = Organizacion.objects.filter(nombre="ORG Tajo").first()
    accion = Tipologia.objects.filter(organizacion__isnull=True, nombre="Acción").first()
    if tajo and accion and not Tipologia.objects.filter(organizacion=tajo, nombre="Acción de barrio").exists():
        barrio = crear_tipologia(Tipologia.EVENTO, "Acción de barrio", padre=accion, organizacion=tajo)
        crear_campo(barrio, "Barrio", Campo.TEXTO, obligatorio=True)


# Crea un nivel del árbol de ejemplo y, debajo de cada tipo, sus subtipos.
def _crear_ramas(familia, ramas, padre):
    for nombre, campos, subtipos in ramas:
        tipologia = crear_tipologia(familia, nombre, padre=padre)
        for nombre_del_campo, tipo, opciones in campos:
            crear_campo(tipologia, nombre_del_campo, tipo, opciones=opciones)
        if familia == Tipologia.PROYECTO:
            for titulo, dias, espera in TAREAS_MODELO.get(nombre, []):
                crear_tarea_modelo(tipologia, titulo, dias=dias, espera_a_la_anterior=espera)
        _crear_ramas(familia, subtipos, tipologia)


# Borra las tipologías de ejemplo: primero las más bajas del árbol (un tipo con subtipos no se puede
# borrar). Solo las comunes y las de ORG Tajo con esos nombres, para no tocar las que haya creado otra
# organización. Las de ORG Tajo se borran también aquí, antes que la organización.
def borrar():
    nombres = {"Acción de barrio"}
    pendientes = [ramas for ramas in COMUNES.values()]
    while pendientes:
        for nombre, _campos, subtipos in pendientes.pop():
            nombres.add(nombre)
            pendientes.append(subtipos)
    while True:
        hojas = Tipologia.objects.filter(
            Q(organizacion__isnull=True) | Q(organizacion__nombre="ORG Tajo"), nombre__in=nombres, hijas__isnull=True
        )
        if not hojas.exists():
            break
        hojas.delete()
