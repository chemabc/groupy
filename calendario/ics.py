"""
Escribe el calendario de una persona en formato iCalendar (.ics, norma RFC 5545), el que entienden los
programas de calendario (el del móvil, Thunderbird, Google Calendar…) para suscribirse a él. Lo usa la
dirección de suscripción (calendario/views.py, ics). Se escribe a mano: es texto sencillo y así no hace
falta ninguna librería.
"""

from datetime import timedelta, timezone as zona_utc

from django.utils import timezone

# Cuánto calendario se manda: desde hace 2 meses hasta dentro de un año.
ATRAS = timedelta(days=60)
ADELANTE = timedelta(days=365)


# Escapa un texto para un campo de iCalendar: la barra invertida, el punto y coma y la coma llevan una
# barra delante, y los saltos de línea se escriben «\n».
def _escapar(texto):
    return str(texto).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n")


# Parte una línea larga como pide la norma: como mucho 75 bytes por línea; las siguientes empiezan con
# un espacio. Se corta sin partir ninguna letra (las tildes ocupan 2 bytes).
def _plegar(linea):
    trozos, actual = [], ""
    for letra in linea:
        if len((actual + letra).encode()) > (75 if not trozos else 74):
            trozos.append(actual)
            actual = ""
        actual += letra
    trozos.append(actual)
    return "\r\n ".join(trozos)


# Fecha y hora en UTC, como la pide iCalendar: «20261120T170000Z».
def _hora(momento):
    return momento.astimezone(zona_utc.utc).strftime("%Y%m%dT%H%M%SZ")


# Solo la fecha (para lo que ocupa días enteros), en la hora de aquí: «20261120».
def _dia(momento):
    return timezone.localtime(momento).strftime("%Y%m%d")


# Escribe el texto .ics con las fechas dadas. Devuelve el texto.
#   - fechas: lista de pares (fuente, FechaDeCalendario), como los da calendario.servicios.fechas.
#   - nombre: nombre del calendario que verá el programa («Asambleas: Nutria»).
#   - dominio: para los identificadores únicos de cada fecha y los enlaces (el de la petición).
#   - esquema: «https» o «http», para los enlaces.
def escribir(fechas, nombre, dominio, esquema="https"):
    ahora = _hora(timezone.now())
    lineas = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Asambleas//Calendario//ES", "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_escapar(nombre)}", "X-WR-TIMEZONE:Europe/Madrid",
    ]
    for fuente, fecha in fechas:
        lineas += ["BEGIN:VEVENT", f"UID:{fuente.codigo}-{fecha.id}@{dominio}", f"DTSTAMP:{ahora}"]
        if fecha.todo_el_dia:
            # En iCalendar, el final de lo que ocupa días enteros es el día siguiente al último.
            ultimo = fecha.fin or fecha.inicio
            lineas += [f"DTSTART;VALUE=DATE:{_dia(fecha.inicio)}", f"DTEND;VALUE=DATE:{_dia(ultimo + timedelta(days=1))}"]
        else:
            lineas.append(f"DTSTART:{_hora(fecha.inicio)}")
            if fecha.fin:
                lineas.append(f"DTEND:{_hora(fecha.fin)}")
        lineas.append(f"SUMMARY:{_escapar(fecha.titulo)}")
        lineas.append(f"CATEGORIES:{_escapar(fecha.categoria or fuente.nombre)}")
        if fecha.lugar:
            lineas.append(f"LOCATION:{_escapar(fecha.lugar)}")
        if fecha.enlace:
            lineas.append(f"URL:{esquema}://{dominio}{fecha.enlace}")
        lineas.append("END:VEVENT")
    lineas.append("END:VCALENDAR")
    return "\r\n".join(_plegar(linea) for linea in lineas) + "\r\n"
