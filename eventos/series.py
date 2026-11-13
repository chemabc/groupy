"""
Series de eventos (docs/diseno.md, apartado 10.2): un evento que se repite («todos los lunes a las
18:00»). Cada vez es un evento propio (con su asistencia y sus cometidos) que se crea con antelación
(90 días vista por defecto); la tarea diaria «eventos.generar_series» va añadiendo las siguientes. Cambiar
la serie cambia las veces futuras que no se hayan tocado a mano. Una serie de reuniones pide una sola
solicitud con apoyos para toda la serie.

Las pantallas (eventos/views.py) llaman a estas funciones.
"""

import calendar
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from audiencias.selector import audiencia_de
from audiencias.servicios import puede_ver
from eventos_sw.servicios import emitir
from permisos.servicios import exigir, puede
from solicitudes.servicios import pedir

from .models import Evento, Serie
from .servicios import ANCLA, _grupo_que_apoya, es_reunion

# Datos que cada vez copia de su serie.
COMUNES = [
    "grupo", "convocante", "tipologia", "titulo", "descripcion", "visibilidad", "modalidad", "lugar", "direccion", "url",
    "duracion", "coste", "coste_detalle", "cartel", "texto_para_redes", "campos",
]
# Nombres de los días de la semana y de las posiciones en el mes, para describir la serie.
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
POSICIONES = ["primer", "segundo", "tercer", "cuarto"]


# ── Las fechas de una serie ──────────────────────────────────────────────────────────────────────────


# Suma meses a una fecha y devuelve (año, mes).
def _mas_meses(dia, meses):
    total = dia.year * 12 + dia.month - 1 + meses
    return total // 12, total % 12 + 1


# Si el día de la primera vez cae en la última semana de su mes (para «el último viernes»).
def _es_el_ultimo(dia):
    return dia.day + 7 > calendar.monthrange(dia.year, dia.month)[1]


# El día de la vez número «n» (0 es la primera), o None si ese mes no tiene ese día (un día 31, o un
# quinto lunes): entonces esa vez se salta.
#   - serie: la serie (su frecuencia).
#   - primero: el día de la primera vez.
def _dia_numero(serie, primero, n):
    if serie.frecuencia == Serie.SEMANAL:
        return primero + timedelta(days=7 * n)
    if serie.frecuencia == Serie.QUINCENAL:
        return primero + timedelta(days=14 * n)
    anio, mes = _mas_meses(primero, n)
    dias_del_mes = calendar.monthrange(anio, mes)[1]
    if serie.frecuencia == Serie.MENSUAL_DIA:
        return date(anio, mes, primero.day) if primero.day <= dias_del_mes else None
    # Mismo día de la semana en la misma posición («el segundo martes») o el último del mes.
    if _es_el_ultimo(primero):
        ultimo = date(anio, mes, dias_del_mes)
        return ultimo - timedelta(days=(ultimo.weekday() - primero.weekday()) % 7)
    uno = date(anio, mes, 1)
    dia = uno + timedelta(days=(primero.weekday() - uno.weekday()) % 7 + 7 * ((primero.day - 1) // 7))
    return dia if dia.month == mes else None


# Las fechas (con hora y zona) de las veces de una serie, desde la primera hasta «limite» (y hasta su
# último día, si tiene). La hora es la de aquí: «a las 18:00» sigue siendo a las 18:00 al cambiar al
# horario de verano.
#   - limite: fecha con hora hasta la que se calcula.
def veces(serie, limite):
    primera = timezone.localtime(serie.inicio)
    hora = primera.time().replace(tzinfo=None)
    n = 0
    while True:
        dia = _dia_numero(serie, primera.date(), n)
        n += 1
        if dia is None:
            continue
        momento = timezone.make_aware(datetime.combine(dia, hora))
        if momento > limite or (serie.hasta and dia > serie.hasta):
            return
        yield momento


# Explica en una frase cuándo se repite: «Cada semana, los martes a las 18:00, hasta el 30/06/2027».
def describir(serie):
    primera = timezone.localtime(serie.inicio)
    dia = DIAS[primera.weekday()]
    if serie.frecuencia == Serie.SEMANAL:
        texto = f"Cada semana, los {dia}"
    elif serie.frecuencia == Serie.QUINCENAL:
        texto = f"Cada dos semanas, los {dia}"
    elif serie.frecuencia == Serie.MENSUAL_DIA:
        texto = f"Cada mes, el día {primera.day}"
    else:
        posicion = "último" if _es_el_ultimo(primera.date()) else POSICIONES[(primera.day - 1) // 7]
        texto = f"Cada mes, el {posicion} {dia}"
    texto += f" a las {primera:%H:%M}"
    if serie.hasta:
        texto += f", hasta el {serie.hasta:%d/%m/%Y}"
    return texto


# ── Crear y activar ──────────────────────────────────────────────────────────────────────────────────


# Crea una serie. Si es de reuniones, queda pendiente y se pide una sola solicitud con apoyos (como una
# reunión suelta: 2 en el propio grupo, 5 en el padre, 10 en el abuelo); al aceptarse, se activa. Si no,
# se activa ya: se crean las veces de los próximos 90 días y se avisa de la primera. Devuelve la serie.
#   - usuario: quien convoca (necesita «eventos.convocar» en el grupo).
#   - datos: los campos comunes (titulo, inicio de la primera vez, duracion…) más «frecuencia» y «hasta».
#   - visibilidad, campos, justificacion: como en servicios.convocar.
@transaction.atomic
def crear_serie(usuario, grupo, tipologia, datos, visibilidad, campos=None, justificacion=""):
    exigir(usuario, "eventos.convocar", grupo=grupo)
    reunion = es_reunion(tipologia)
    audiencia = audiencia_de("privado" if reunion else visibilidad, grupo, personas=[usuario])
    serie = Serie(
        grupo=grupo, convocante=usuario, tipologia=tipologia, audiencia=audiencia, visibilidad=visibilidad, campos=campos or {},
        estado=Serie.PENDIENTE if reunion else Serie.ACTIVA, **datos,
    )
    serie.full_clean()
    serie.save()
    if reunion:
        destino, altura = _grupo_que_apoya(grupo, visibilidad)
        pedir(
            usuario, "eventos.serie_de_reuniones", destino, f"Serie de reuniones «{serie.titulo}»: {describir(serie).lower()}",
            justificacion, datos={"serie_id": serie.pk}, altura=altura,
        )
    else:
        generar(serie, avisar=True)
    return serie


# Activa una serie de reuniones cuando su solicitud consigue los apoyos (la llama «solicitudes»; ver el
# TipoDeSolicitud «eventos.serie_de_reuniones»). Le pone la visibilidad elegida, crea sus veces y avisa.
# Devuelve el ancla de la primera vez (o None si no hay ninguna aún).
#   - solicitud: la solicitud aceptada (sus datos llevan «serie_id»).
def activar_serie(solicitud):
    serie = Serie.objects.select_related("grupo__organizacion", "convocante").get(pk=solicitud.datos["serie_id"])
    serie.audiencia = audiencia_de(serie.visibilidad, serie.grupo, personas=[serie.convocante] if serie.convocante else [])
    serie.estado = Serie.ACTIVA
    serie.save(update_fields=["audiencia", "estado"])
    generar(serie, avisar=True)
    primera = serie.veces.order_by("inicio").first()
    return (ANCLA, primera.pk) if primera else None


# ── Crear las veces ──────────────────────────────────────────────────────────────────────────────────


# Copia los datos de la serie en una vez (nueva o ya existente que no se ha tocado a mano). La audiencia
# se calcula para cada vez: si es privada, cada vez tiene la suya (quien se apunta a un cometido en una
# no pasa a ver las demás).
#   - nueva_audiencia: si hay que calcularla (al crear la vez o al cambiar quién lo ve).
def _copiar(serie, evento, nueva_audiencia):
    for campo in COMUNES:
        setattr(evento, campo, getattr(serie, campo))
    if nueva_audiencia:
        evento.audiencia = audiencia_de(serie.visibilidad, serie.grupo, personas=[serie.convocante] if serie.convocante else [])


# Crea las veces que faltan de una serie activa, desde ahora hasta su antelación (no crea veces pasadas
# ni repite las que ya existen). Devuelve cuántas ha creado.
#   - avisar: si se avisa de la primera vez nueva (al crear o activar la serie; no cada día).
@transaction.atomic
def generar(serie, avisar=False):
    if serie.estado != Serie.ACTIVA:
        return 0
    ahora = timezone.now()
    ya = set(Evento.objects.filter(serie=serie).values_list("en_la_serie", flat=True))
    nuevas = []
    for momento in veces(serie, ahora + timedelta(days=serie.antelacion)):
        if momento < ahora or momento in ya:
            continue
        evento = Evento(serie=serie, en_la_serie=momento, inicio=momento, estado=Evento.CONVOCADO)
        _copiar(serie, evento, nueva_audiencia=True)
        evento.save()
        nuevas.append(evento)
    if avisar and nuevas:
        emitir("eventos.convocado", evento_id=nuevas[0].pk)
    return len(nuevas)


# Tarea diaria «eventos.generar_series»: termina las series cuyo último día ya pasó y crea las veces que
# toquen en las activas. Devuelve cuántas veces ha creado en total.
def generar_todas():
    Serie.objects.filter(estado=Serie.ACTIVA, hasta__lt=timezone.localdate()).update(estado=Serie.TERMINADA)
    series = Serie.objects.filter(estado=Serie.ACTIVA).select_related("grupo__organizacion", "convocante")
    return sum(generar(serie) for serie in series)


# ── Ver, cambiar y terminar ──────────────────────────────────────────────────────────────────────────


# Dice si una persona puede cambiar o terminar una serie: quien la convocó, la administración del grupo
# (con «grupos.editar_grupo») o el superadmin.
def puede_gestionar(usuario, serie):
    if usuario.is_superuser or serie.convocante_id == usuario.pk:
        return True
    return puede(usuario, "grupos.editar_grupo", grupo=serie.grupo_id)


# Dice si una persona ve una serie: quien la convocó o, si no está pendiente de apoyos, su audiencia.
def ve(usuario, serie):
    if serie.convocante_id == usuario.pk:
        return True
    return serie.estado != Serie.PENDIENTE and puede_ver(usuario, serie.audiencia_id)


# Quita una vez futura que ya no encaja con la serie: si alguien había respondido, se cancela (y se
# avisa); si no, se borra. En los dos casos deja de ocupar su fecha en la serie.
def _quitar(evento):
    if evento.asistencias.exists():
        evento.estado = Evento.CANCELADO
        evento.en_la_serie = None
        evento.save(update_fields=["estado", "en_la_serie"])
        emitir("eventos.cancelado", evento_id=evento.pk)
    else:
        evento.delete()


# Cambia una serie y sus veces futuras que no se hayan tocado a mano. Si cambia cuándo se repite (la
# primera vez, la frecuencia o el último día), las veces que ya no encajan se quitan (ver _quitar) y se
# crean las nuevas. La visibilidad de una serie de reuniones no cambia (se pidieron apoyos para esa).
# Devuelve la serie.
#   - datos: los campos comunes, «frecuencia» y «hasta».
#   - visibilidad: la nueva, o None.
#   - campos: los de su tipología, o None.
@transaction.atomic
def editar_serie(usuario, serie, datos, visibilidad=None, campos=None):
    if not puede_gestionar(usuario, serie):
        raise ValidationError("Solo quien la convocó o la administración del grupo pueden cambiarla.")
    if serie.estado == Serie.TERMINADA:
        raise ValidationError("La serie ya ha terminado.")
    regla_antes = (serie.inicio, serie.frecuencia, serie.hasta)
    for campo, valor in datos.items():
        setattr(serie, campo, valor)
    if campos is not None:
        serie.campos = campos
    otra_audiencia = bool(visibilidad) and visibilidad != serie.visibilidad and not es_reunion(serie.tipologia)
    if otra_audiencia:
        serie.audiencia = audiencia_de(visibilidad, serie.grupo, personas=[serie.convocante] if serie.convocante else [])
        serie.visibilidad = visibilidad
    serie.full_clean()
    serie.save()
    if serie.estado != Serie.ACTIVA:
        return serie
    ahora = timezone.now()
    futuras = list(serie.veces.filter(inicio__gte=ahora, tocado=False).exclude(estado=Evento.CANCELADO))
    if regla_antes != (serie.inicio, serie.frecuencia, serie.hasta):
        siguen = set(veces(serie, ahora + timedelta(days=serie.antelacion)))
        for evento in futuras:
            if evento.en_la_serie not in siguen:
                _quitar(evento)
        futuras = [evento for evento in futuras if evento.en_la_serie in siguen]
    for evento in futuras:
        _copiar(serie, evento, nueva_audiencia=otra_audiencia)
        evento.save()
    generar(serie)
    return serie


# Termina una serie: ya no se crean más veces y las futuras que no se hayan tocado a mano se cancelan
# (se avisa a quienes iban). Las tocadas a mano se quedan como están.
@transaction.atomic
def terminar_serie(usuario, serie):
    if not puede_gestionar(usuario, serie):
        raise ValidationError("Solo quien la convocó o la administración del grupo pueden terminarla.")
    serie.estado = Serie.TERMINADA
    serie.hasta = timezone.localdate()
    serie.save(update_fields=["estado", "hasta"])
    for evento in serie.veces.filter(inicio__gte=timezone.now(), tocado=False).exclude(estado=Evento.CANCELADO):
        evento.estado = Evento.CANCELADO
        evento.save(update_fields=["estado"])
        emitir("eventos.cancelado", evento_id=evento.pk)
