"""
Operaciones de la bóveda: registrar a una persona, validarla (de momento, solo el alta por el
superadmin), cambiar su correo y los dominios de correo de cada organización.

Todo se hace en la base «boveda» (ver config/enrutador.py), en transacciones de esa base.
"""

import hashlib
import hmac

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import DominioPermitido, PaseEmitido, Persona

# Nombre de la base de la bóveda, para sus transacciones.
BASE = "boveda"


# Huella de un dato (un correo, un DNI): un código de 64 caracteres calculado con la clave secreta de la
# bóveda (HMAC-SHA256). El mismo dato da siempre la misma huella, así que sirve para saber si ya está
# registrado; pero de la huella no se puede volver al dato, y sin la clave no se puede calcular.
#   - dato: el texto (se pasa a minúsculas y sin espacios alrededor antes de calcular).
def huella(dato):
    texto = dato.strip().lower().encode("utf-8")
    return hmac.new(settings.BOVEDA_CLAVE_HMAC.encode("utf-8"), texto, hashlib.sha256).hexdigest()


# Dominio de un correo: lo que va detrás de la arroba, en minúsculas.
def dominio_de(correo):
    return correo.strip().lower().rsplit("@", 1)[-1]


# Dominios permitidos de una organización, como conjunto.
#   - organizacion_id: número de la organización de la plataforma.
def dominios_de(organizacion_id):
    return set(DominioPermitido.objects.filter(organizacion_id=organizacion_id).values_list("dominio", flat=True))


# Comprueba un correo antes de guardarlo: que no esté ya registrado (por su huella) y, si la organización
# tiene dominios permitidos, que sea de uno de ellos. Lanza ValidationError con la explicación.
#   - correo: el correo oficial.
#   - organizacion_id: la organización elegida.
#   - persona: la persona que lo tendrá (para no chocar consigo misma), o None si es nueva.
def _comprobar_correo(correo, organizacion_id, persona=None):
    repetida = Persona.objects.filter(huella_del_correo=huella(correo)).exclude(pk=getattr(persona, "pk", None)).first()
    if repetida is not None:
        raise ValidationError({"correo_oficial": f"Ese correo ya está registrado ({repetida}). Una persona, una cuenta."})
    permitidos = dominios_de(organizacion_id) if organizacion_id else set()
    if permitidos and dominio_de(correo) not in permitidos:
        raise ValidationError(
            {"correo_oficial": f"Esta organización solo admite correos de: {', '.join(sorted(permitidos))}."}
        )


# Registra a una persona, pendiente de validar, con su correo oficial (y su huella). Devuelve la persona.
#   - nombre: nombre real.
#   - correo: correo oficial.
#   - organizacion_id: número de la organización de la plataforma en la que se da de alta.
@transaction.atomic(using=BASE)
def registrar_persona(nombre, correo, organizacion_id):
    _comprobar_correo(correo, organizacion_id)
    persona = Persona(nombre=nombre.strip(), correo_oficial=correo.strip().lower(), huella_del_correo=huella(correo), organizacion_id=organizacion_id)
    persona.full_clean()
    persona.save()
    return persona


# Cambia los datos de una persona. Si cambia el correo, se calcula su nueva huella; y si ya estaba
# validada, vuelve a quedar pendiente (hay que validarla otra vez con el correo nuevo). Su pase sigue
# contando como emitido: no puede conseguir otro.
#   - persona: la persona.
#   - nombre, organizacion_id: los datos nuevos.
#   - correo: el correo nuevo, o vacío para no cambiarlo.
@transaction.atomic(using=BASE)
def cambiar_datos(persona, nombre, organizacion_id, correo=""):
    persona.nombre = nombre.strip()
    persona.organizacion_id = organizacion_id
    correo = correo.strip().lower()
    if correo and correo != persona.correo_oficial:
        _comprobar_correo(correo, organizacion_id, persona)
        persona.correo_oficial = correo
        persona.huella_del_correo = huella(correo)
        if persona.estado == Persona.VALIDADA:
            persona.estado, persona.metodo, persona.validada_el = Persona.PENDIENTE, "", None
    persona.full_clean()
    persona.save()
    return persona


# Valida a una persona por el método «alta por el superadmin»: queda validada con el día de hoy, se
# borra su correo oficial (queda la huella) y su pase se marca como ya emitido, para que en el registro
# real no pueda conseguir un segundo alias. El alias se crea aparte, en la plataforma, sin ningún enlace.
#   - persona: la persona, pendiente.
@transaction.atomic(using=BASE)
def validar_por_superadmin(persona):
    if persona.estado == Persona.VALIDADA:
        raise ValidationError("Esta persona ya está validada.")
    persona.estado = Persona.VALIDADA
    persona.metodo = Persona.POR_SUPERADMIN
    persona.validada_el = timezone.localdate()
    persona.correo_oficial = ""
    persona.save()
    PaseEmitido.objects.get_or_create(persona=persona, ronda=0, defaults={"provisional": True})
    return persona


# Pone los dominios permitidos de una organización (sustituye a los que tuviera). Devuelve los dominios
# guardados, en orden.
#   - organizacion_id: número de la organización.
#   - dominios: lista de textos («educa.madrid.org», «@otra.org»…); se limpian y se quitan repetidos.
@transaction.atomic(using=BASE)
def poner_dominios(organizacion_id, dominios):
    limpios = sorted({dominio.strip().lower().lstrip("@") for dominio in dominios if dominio.strip()})
    for dominio in limpios:
        if "." not in dominio or " " in dominio or "@" in dominio:
            raise ValidationError(f"«{dominio}» no parece un dominio de correo (por ejemplo, «educa.madrid.org»).")
    DominioPermitido.objects.filter(organizacion_id=organizacion_id).exclude(dominio__in=limpios).delete()
    for dominio in limpios:
        DominioPermitido.objects.get_or_create(organizacion_id=organizacion_id, dominio=dominio)
    return limpios


# Dominios de todas las organizaciones, como {número de organización: [dominios]}. Una consulta. Lo usan
# las pantallas que muestran los dominios junto a las organizaciones.
def dominios_por_organizacion():
    resultado = {}
    for organizacion_id, dominio in DominioPermitido.objects.values_list("organizacion_id", "dominio"):
        resultado.setdefault(organizacion_id, []).append(dominio)
    return resultado
