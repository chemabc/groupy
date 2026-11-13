"""
Servicios del módulo «eventos_sw»: emitir un aviso y procesar la bandeja de salida.

Uso desde cualquier módulo, dentro de la misma transacción que el cambio que se anuncia:

    from django.db import transaction
    from eventos_sw.servicios import emitir

    with transaction.atomic():
        consulta.cerrar()
        emitir("consultas.cerrada", consulta_id=consulta.id, grupo_id=consulta.grupo_id)

Cada función receptora recibe los datos como parámetros con nombre:

    def copiar_resultado(consulta_id, grupo_id, **resto): ...
"""

import json
import traceback
from datetime import timedelta

from django.db import connection, transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from base.contrato import Modo
from base.registro import registro

from .models import AvisoPendiente

# Número de fallos tras el que un aviso deja de reintentarse y queda marcado como fallido.
MAXIMO_DE_INTENTOS = 5


class EventoNoDeclarado(LookupError):
    """Se emite un eventos_sw que ningún módulo declara en el apartado «emite» de su contrato."""


class FueraDeTransaccion(RuntimeError):
    """Se emite un eventos_sw sin estar dentro de transaction.atomic()."""


# Anuncia que ha pasado algo. Ejecuta en el acto las escuchas síncronas y deja en la bandeja de salida
# una fila por cada escucha asíncrona. Lo llaman los servicios de los módulos justo después de guardar
# el cambio que anuncian.
#   - nombre: nombre del eventos_sw, declarado en el «emite» de algún contrato.
#   - datos: valores simples (números, textos, listas, diccionarios) que reciben los receptores.
def emitir(nombre, **datos):
    # Sin transacción, el cambio ya estaría guardado y un fallo de un receptor dejaría las cosas a medias.
    if not connection.in_atomic_block:
        raise FueraDeTransaccion(
            f"«{nombre}» se emite fuera de una transacción. Llama a emitir() dentro de "
            "«with transaction.atomic():», junto al cambio que anuncia."
        )
    if nombre not in registro.emite:
        raise EventoNoDeclarado(f"«{nombre}» no está en el «emite» del contrato de ningún módulo.")
    # Comprueba ya que los datos se pueden guardar como JSON, también si hoy solo hay escuchas síncronas:
    # así no falla el día que alguien añada una asíncrona.
    try:
        json.dumps(datos)
    except TypeError as error:
        raise TypeError(
            f"Los datos de «{nombre}» deben ser valores simples (números, textos, listas), no objetos: {error}"
        ) from error
    escuchas = registro.escuchas.get(nombre, [])
    # Primero las síncronas, en el orden en que se cargaron los módulos.
    for escucha in escuchas:
        if escucha.modo == Modo.SINCRONO:
            import_string(escucha.receptor)(**datos, **dict(escucha.extra))
    # Después, todas las asíncronas a la bandeja de una vez (una sola consulta).
    pendientes = [
        AvisoPendiente(evento=nombre, receptor=escucha.receptor, datos={**datos, **dict(escucha.extra)})
        for escucha in escuchas
        if escucha.modo == Modo.ASINCRONO
    ]
    if pendientes:
        AvisoPendiente.objects.bulk_create(pendientes)


# Procesa una tanda de avisos de la bandeja de salida y devuelve cuántos ha procesado (bien o mal). La
# llama la orden «procesar_bandeja» en bucle, y las pruebas cuando quieren ver el efecto de un aviso.
#   - limite: número máximo de avisos de la tanda.
def procesar_bandeja(limite=100):
    with transaction.atomic():
        # Bloquea las filas que va a procesar. «skip_locked» hace que otro proceso que trabaje a la vez
        # se salte esas filas en lugar de esperar, así que dos procesos nunca hacen el mismo aviso.
        avisos = list(
            AvisoPendiente.objects.select_for_update(skip_locked=True)
            .filter(fallido=False, proximo_intento__lte=timezone.now())
            .order_by("id")[:limite]
        )
        hechos = []
        for aviso in avisos:
            try:
                # Cada aviso en su propio punto de guardado: si falla, se deshace solo lo suyo.
                with transaction.atomic():
                    import_string(aviso.receptor)(**aviso.datos)
                hechos.append(aviso.id)
            except Exception:
                _apuntar_fallo(aviso, traceback.format_exc())
        # Los que han salido bien se borran todos juntos, con una sola consulta.
        AvisoPendiente.objects.filter(id__in=hechos).delete()
    return len(avisos)


# Apunta un fallo en un aviso: suma un intento, guarda el error y retrasa el siguiente intento (1, 2, 4,
# 8… minutos). Al llegar al máximo, lo marca como fallido. La usa procesar_bandeja.
def _apuntar_fallo(aviso, error):
    aviso.intentos += 1
    aviso.ultimo_error = error
    aviso.proximo_intento = timezone.now() + timedelta(minutes=2 ** (aviso.intentos - 1))
    aviso.fallido = aviso.intentos >= MAXIMO_DE_INTENTOS
    aviso.save(update_fields=["intentos", "ultimo_error", "proximo_intento", "fallido"])
