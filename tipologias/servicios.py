"""
Operaciones del módulo «tipologias»: el árbol que ve cada persona, quién puede cambiar cada tipología,
los campos de una tipología (con los heredados) y el formulario de esos campos, que usarán los módulos
«proyectos» y «eventos» al crear algo de un tipo.

Reglas: las tipologías comunes las cambia solo el superadmin; las de una organización, su admin
(permiso «tipologias.gestionar») y el superadmin. Cada organización ve las comunes y las suyas.
"""

import datetime
import decimal
from dataclasses import dataclass

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from grupos.models import Organizacion
from permisos.servicios import permisos_de

from .models import Campo, TareaModelo, Tipologia

# Permiso para gestionar las tipologías de una organización.
PERMISO = "tipologias.gestionar"


# Organizaciones cuyas tipologías puede gestionar una persona: todas si es superadmin; si no, las que
# administra con el permiso. Lista de (número, nombre), en orden. Una consulta.
def organizaciones_que_gestiona(usuario):
    mapa = permisos_de(usuario)
    consulta = Organizacion.objects.order_by("nombre")
    if not mapa.es_superadmin:
        consulta = consulta.filter(pk__in=[pk for pk, codigos in mapa.organizaciones.items() if PERMISO in codigos])
    return list(consulta.values_list("pk", "nombre"))


# Dice si una persona puede cambiar una tipología (y añadirle campos o subtipos de su organización).
#   - organizaciones: las que gestiona (de organizaciones_que_gestiona), para no volver a consultarlas.
def puede_editar(usuario, tipologia, organizaciones):
    if usuario.is_superuser:
        return True
    return tipologia.organizacion_id is not None and tipologia.organizacion_id in {pk for pk, _nombre in organizaciones}


@dataclass
class Rama:
    """Una tipología dentro del árbol, con su nivel (0 las principales) y su camino («Acción › Concentración»)."""

    tipologia: Tipologia
    nivel: int
    camino: str


# Árbol de una familia con las tipologías que ve una persona (las comunes y las de las organizaciones
# indicadas; el superadmin, todas), en orden: cada una debajo de su padre. Una consulta.
#   - familia: Tipologia.PROYECTO o Tipologia.EVENTO.
#   - organizaciones: números de las organizaciones cuyas tipologías se ven (None: todas).
def arbol(familia, organizaciones=None):
    consulta = Tipologia.objects.filter(familia=familia).select_related("organizacion")
    if organizaciones is not None:
        consulta = consulta.filter(Q(organizacion__isnull=True) | Q(organizacion_id__in=organizaciones))
    tipologias = list(consulta)
    hijas = {}
    for tipologia in tipologias:
        hijas.setdefault(tipologia.padre_id, []).append(tipologia)
    resultado = []

    # Añade las tipologías de un nivel (y debajo de cada una, las suyas), por orden alfabético.
    def recorrer(padre_id, nivel, antes):
        for tipologia in sorted(hijas.get(padre_id, []), key=lambda t: t.nombre.lower()):
            camino = f"{antes} › {tipologia.nombre}" if antes else tipologia.nombre
            resultado.append(Rama(tipologia, nivel, camino))
            recorrer(tipologia.pk, nivel + 1, camino)

    recorrer(None, 0, "")
    return resultado


# Cadena de una tipología de arriba abajo: [la principal, …, su padre, ella]. Usa las tipologías ya
# cargadas si se le pasan ({id: tipología}); si no, consulta un nivel cada vez (los árboles son bajos).
def cadena(tipologia, cargadas=None):
    resultado, actual = [], tipologia
    while actual is not None:
        resultado.append(actual)
        if actual.padre_id is None:
            break
        actual = cargadas.get(actual.padre_id) if cargadas else actual.padre
    return list(reversed(resultado))


# Campos de una tipología con los heredados: primero los de la principal, después los de cada nivel, y
# dentro de cada uno en su orden. Una consulta (más la cadena, si no se pasan las cargadas).
def campos_de(tipologia, cargadas=None):
    niveles = {t.pk: nivel for nivel, t in enumerate(cadena(tipologia, cargadas))}
    campos = list(Campo.objects.filter(tipologia_id__in=niveles).select_related("tipologia"))
    return sorted(campos, key=lambda campo: (niveles[campo.tipologia_id], campo.orden, campo.pk))


# Tareas modelo de una tipología con las heredadas: primero las de la principal, después las de cada
# nivel, cada una en su orden. Una consulta (más la cadena, si no se pasan las cargadas).
def tareas_modelo_de(tipologia, cargadas=None):
    niveles = {t.pk: nivel for nivel, t in enumerate(cadena(tipologia, cargadas))}
    tareas = list(TareaModelo.objects.filter(tipologia_id__in=niveles).select_related("tipologia"))
    return sorted(tareas, key=lambda tarea: (niveles[tarea.tipologia_id], tarea.orden, tarea.pk))


# Formulario con los campos personalizados de una tipología (con los heredados). Lo usarán proyectos y
# eventos para pedir esos datos; con a_json() los valores se guardan en el propio objeto.
#   - tipologia: la tipología.
#   - datos: lo enviado (request.POST) o None.
#   - valores: los ya guardados (el JSON del objeto), para editar.
def formulario_de(tipologia, datos=None, valores=None):
    formulario = forms.Form(datos, initial=valores or {})
    for campo in campos_de(tipologia):
        formulario.fields[campo.clave] = _campo_de_formulario(campo)
    return formulario


# Campo de formulario de Django para un campo personalizado, según su tipo.
def _campo_de_formulario(campo):
    comunes = {"label": campo.nombre, "required": campo.obligatorio, "help_text": campo.ayuda}
    if campo.tipo == Campo.TEXTO_LARGO:
        return forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), **comunes)
    if campo.tipo == Campo.NUMERO:
        return forms.DecimalField(max_digits=14, decimal_places=2, **comunes)
    if campo.tipo == Campo.FECHA:
        return forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), **comunes)
    if campo.tipo == Campo.SI_NO:
        # Una casilla nunca es obligatoria: «obligatoria» querría decir que hay que marcarla.
        return forms.BooleanField(**{**comunes, "required": False})
    if campo.tipo == Campo.LISTA:
        opciones = [("", "---------")] + [(opcion, opcion) for opcion in campo.lista_de_opciones]
        return forms.ChoiceField(choices=opciones, **comunes)
    return forms.CharField(max_length=200, **comunes)


# Convierte los valores limpios de formulario_de() en algo que se puede guardar en JSON (las fechas como
# AAAA-MM-DD y los números como texto, para no perder decimales).
def a_json(valores):
    resultado = {}
    for clave, valor in valores.items():
        if isinstance(valor, datetime.date):
            valor = valor.isoformat()
        elif isinstance(valor, decimal.Decimal):
            valor = str(valor)
        resultado[clave] = valor
    return resultado


# ── Cambios ──────────────────────────────────────────────────────────────────────────────────────────


# Crea una tipología, comprobando las reglas del árbol. Devuelve la tipología.
#   - familia: Tipologia.PROYECTO o Tipologia.EVENTO.
#   - nombre, descripcion: como se verá.
#   - padre: la tipología de la que es subtipo, o None para un tipo principal.
#   - organizacion: la organización (objeto), u organizacion_id (su número); ninguna, común. Si el padre
#     es de una organización, el subtipo es de la misma.
@transaction.atomic
def crear_tipologia(familia, nombre, padre=None, organizacion=None, descripcion="", organizacion_id=None):
    organizacion_id = getattr(organizacion, "pk", organizacion_id)
    if padre is not None and padre.organizacion_id is not None:
        organizacion_id = padre.organizacion_id
    tipologia = Tipologia(familia=familia, nombre=nombre.strip(), padre=padre, organizacion_id=organizacion_id, descripcion=descripcion)
    tipologia.full_clean()
    tipologia.save()
    return tipologia


# Borra una tipología que no tiene subtipos (con sus campos). Más adelante, también comprobará que no
# la usa ningún proyecto ni evento.
@transaction.atomic
def borrar_tipologia(tipologia):
    if tipologia.hijas.exists():
        raise ValidationError("Antes hay que borrar o mover sus subtipos.")
    tipologia.delete()


# Añade un campo al final de una tipología. Devuelve el campo.
@transaction.atomic
def crear_campo(tipologia, nombre, tipo, obligatorio=False, ayuda="", opciones=""):
    ultimo = tipologia.campos.order_by("-orden").values_list("orden", flat=True).first()
    campo = Campo(
        tipologia=tipologia, nombre=nombre.strip(), tipo=tipo, obligatorio=obligatorio, ayuda=ayuda, opciones=opciones,
        orden=(ultimo or 0) + 1,
    )
    campo.full_clean()
    campo.save()
    return campo


# Pone los campos de una tipología en el orden indicado (el resultado de arrastrarlos). Los ids que no
# son de esa tipología se ignoran.
#   - ids: lista con los ids de sus campos, en el orden nuevo.
@transaction.atomic
def ordenar_campos(tipologia, ids):
    suyos = {campo.pk: campo for campo in tipologia.campos.all()}
    for posicion, pk in enumerate((pk for pk in ids if pk in suyos), start=1):
        if suyos[pk].orden != posicion:
            suyos[pk].orden = posicion
            suyos[pk].save(update_fields=["orden"])


# Añade una tarea modelo al final de una tipología de proyectos. Devuelve la tarea modelo.
#   - titulo, descripcion, dias, espera_a_la_anterior: sus datos (ver TareaModelo).
@transaction.atomic
def crear_tarea_modelo(tipologia, titulo, descripcion="", dias=None, espera_a_la_anterior=False):
    if tipologia.familia != Tipologia.PROYECTO:
        raise ValidationError("Las tareas modelo son solo de los tipos de proyecto.")
    ultimo = tipologia.tareas_modelo.order_by("-orden").values_list("orden", flat=True).first()
    tarea = TareaModelo(
        tipologia=tipologia, titulo=titulo.strip(), descripcion=descripcion, dias=dias, espera_a_la_anterior=espera_a_la_anterior,
        orden=(ultimo or 0) + 1,
    )
    tarea.full_clean()
    tarea.save()
    return tarea
