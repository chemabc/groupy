"""
Operaciones del módulo «etiquetas»: sugerir mientras se escribe, crear las que falten al usarlas,
etiquetar cualquier cosa (con un ancla), buscar por etiqueta (también por sus palabras relacionadas) y
fusionar etiquetas repetidas.

Regla de visibilidad: en una organización se sugieren y se usan sus etiquetas y las comunes; nunca las de
otra organización.
"""

import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from base.registro import registro
from base.tablas import forma_de_frase, normalizar

from .models import Etiqueta, EtiquetaDe

# Máximo de palabras de una etiqueta y de sugerencias que se devuelven.
MAXIMO_DE_PALABRAS = 3
MAXIMO_DE_SUGERENCIAS = 10
# Forma de una etiqueta: letras (sin tildes; la ñ sí), números y guiones, separados por espacios.
FORMA = re.compile(r"^[\w\-]+( [\w\-]+){0,2}$")


# Deja el nombre de una etiqueta en su forma fija: sin espacios de más ni comas o almohadillas sueltas,
# sin tildes, y en minúsculas salvo la primera letra («  #REUNIÓN   general» → «Reunion general»). Así
# todas se ven igual, se escriban como se escriban. Se usa al guardar, al etiquetar y al buscar.
#   - nombre: lo escrito («  Local   nuevo », «#huelga»).
def limpiar(nombre):
    return forma_de_frase(" ".join(str(nombre).replace(",", " ").split()).lstrip("#").strip())


# Comprueba que un nombre sirve como etiqueta (de una a tres palabras, sin símbolos raros, hasta 40
# caracteres) y lo devuelve limpio. Lanza ValidationError con la explicación si no sirve.
def comprobar_nombre(nombre):
    limpio = limpiar(nombre)
    if not limpio:
        raise ValidationError("La etiqueta está vacía.")
    if len(limpio) > 40 or not FORMA.match(limpio):
        raise ValidationError(
            f"«{limpio}» no sirve como etiqueta: de una a {MAXIMO_DE_PALABRAS} palabras (letras, números o guiones), 40 caracteres como mucho."
        )
    return limpio


# Etiquetas que se pueden usar en una organización: las suyas y las comunes (consulta, sin ejecutar).
#   - organizacion: la organización (objeto o id), o None para solo las comunes.
def disponibles(organizacion):
    organizacion_id = getattr(organizacion, "pk", organizacion)
    return Etiqueta.objects.filter(Q(organizacion__isnull=True) | Q(organizacion_id=organizacion_id))


# Sugerencias mientras se escribe: etiquetas de la organización y comunes cuyo nombre o palabras
# relacionadas contienen lo escrito (sin tildes ni mayúsculas). Primero las que empiezan por lo escrito.
# Una consulta. Devuelve una lista de diccionarios {nombre, comun}.
#   - texto: lo escrito hasta ahora.
#   - organizacion: la organización en la que se etiqueta (o None).
def sugerir(texto, organizacion):
    buscado = normalizar(limpiar(texto))
    if not buscado:
        return []
    candidatas = disponibles(organizacion).filter(Q(normalizada__contains=buscado) | Q(relacionadas_normalizadas__contains=buscado))
    ordenadas = sorted(candidatas[:50], key=lambda etiqueta: (not etiqueta.normalizada.startswith(buscado), etiqueta.normalizada))
    return [{"nombre": etiqueta.nombre, "comun": etiqueta.organizacion_id is None} for etiqueta in ordenadas[:MAXIMO_DE_SUGERENCIAS]]


# Devuelve las etiquetas con esos nombres en la organización, creando las que falten (cualquiera puede
# crearlas al usarlas). Si existe una común con el mismo nombre, se usa la común.
#   - nombres: lista de nombres escritos.
#   - organizacion: la organización (objeto); las nuevas son suyas.
#   - usuario: quién las usa (queda como creador de las nuevas).
@transaction.atomic
def obtener_o_crear(nombres, organizacion, usuario=None):
    limpios = {}
    for nombre in nombres:
        limpio = comprobar_nombre(nombre)
        limpios.setdefault(normalizar(limpio), limpio)
    existentes = {etiqueta.normalizada: etiqueta for etiqueta in disponibles(organizacion).filter(normalizada__in=limpios)}
    resultado = []
    for normalizada, limpio in limpios.items():
        etiqueta = existentes.get(normalizada)
        if etiqueta is None:
            etiqueta = Etiqueta.objects.create(organizacion=organizacion, nombre=limpio, normalizada=normalizada, creada_por=usuario)
        resultado.append(etiqueta)
    return resultado


# Pone a algo concreto exactamente estas etiquetas (quita las que ya no están y añade las nuevas).
# Devuelve las etiquetas que quedan.
#   - ancla: (tipo, id) de lo etiquetado; el tipo debe estar declarado como ancla en algún contrato.
#   - nombres: los nombres de las etiquetas.
#   - organizacion: la organización de lo etiquetado.
#   - usuario: quién etiqueta.
@transaction.atomic
def etiquetar(ancla, nombres, organizacion, usuario=None):
    if ancla[0] not in registro.anclas:
        raise ValidationError(f"No se puede etiquetar «{ancla[0]}»: ningún módulo lo declara como ancla.")
    etiquetas = obtener_o_crear(nombres, organizacion, usuario)
    EtiquetaDe.objects.filter(ancla_tipo=ancla[0], ancla_id=ancla[1]).exclude(etiqueta__in=etiquetas).delete()
    for etiqueta in etiquetas:
        EtiquetaDe.objects.get_or_create(etiqueta=etiqueta, ancla_tipo=ancla[0], ancla_id=ancla[1])
    return etiquetas


# Nombres de las etiquetas de algo concreto, en orden. Una consulta.
def etiquetas_de(ancla):
    return list(
        EtiquetaDe.objects.filter(ancla_tipo=ancla[0], ancla_id=ancla[1]).order_by("etiqueta__normalizada").values_list("etiqueta__nombre", flat=True)
    )


# Ids de lo etiquetado (de un tipo) con una etiqueta que coincide con lo buscado, por su nombre o por sus
# palabras relacionadas: buscar «paro» encuentra lo etiquetado «huelga» si «paro» es una relacionada.
#   - texto: lo buscado.
#   - ancla_tipo: tipo de lo que se busca («proyectos.proyecto»).
#   - organizacion: la organización en la que se busca.
def buscar(texto, ancla_tipo, organizacion):
    buscado = normalizar(limpiar(texto))
    etiquetas = disponibles(organizacion).filter(Q(normalizada=buscado) | Q(relacionadas_normalizadas__regex=rf"(^|,){re.escape(buscado)}(,|$)"))
    return set(EtiquetaDe.objects.filter(etiqueta__in=etiquetas, ancla_tipo=ancla_tipo).values_list("ancla_id", flat=True))


# Cambia las palabras relacionadas de una etiqueta (separadas por comas), sin repetir ninguna ni el propio
# nombre. Al guardar se calcula su forma normalizada (Etiqueta.save).
@transaction.atomic
def poner_relacionadas(etiqueta, texto):
    vistas, palabras = {etiqueta.normalizada}, []
    for palabra in texto.split(","):
        palabra = limpiar(palabra)
        if palabra and normalizar(palabra) not in vistas:
            vistas.add(normalizar(palabra))
            palabras.append(palabra)
    etiqueta.relacionadas = ", ".join(palabras)
    etiqueta.save()
    return etiqueta


# Fusiona etiquetas repetidas en una: lo etiquetado con las otras pasa a llevar la que se queda, sus
# nombres pasan a ser palabras relacionadas de ella y las otras se borran. Deben ser de la misma
# organización (o comunes). Devuelve la etiqueta que se queda.
#   - destino: la etiqueta que se queda.
#   - otras: las que desaparecen.
@transaction.atomic
def fusionar(destino, otras):
    otras = [etiqueta for etiqueta in otras if etiqueta.pk != destino.pk]
    for etiqueta in otras:
        if etiqueta.organizacion_id != destino.organizacion_id:
            raise ValidationError(f"«{etiqueta}» es de otra organización: solo se fusionan etiquetas de la misma.")
    ya = set(EtiquetaDe.objects.filter(etiqueta=destino).values_list("ancla_tipo", "ancla_id"))
    for uso in EtiquetaDe.objects.filter(etiqueta__in=otras):
        if (uso.ancla_tipo, uso.ancla_id) in ya:
            uso.delete()
        else:
            ya.add((uso.ancla_tipo, uso.ancla_id))
            uso.etiqueta = destino
            uso.save(update_fields=["etiqueta"])
    relacionadas = [destino.relacionadas] if destino.relacionadas else []
    relacionadas += [etiqueta.nombre for etiqueta in otras] + [etiqueta.relacionadas for etiqueta in otras if etiqueta.relacionadas]
    Etiqueta.objects.filter(pk__in=[etiqueta.pk for etiqueta in otras]).delete()
    return poner_relacionadas(destino, ", ".join(relacionadas))
