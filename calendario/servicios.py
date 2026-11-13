"""
Operaciones del módulo «calendario»: juntar las fechas que aportan todos los módulos (sus
FuenteDeCalendario), moverlas al arrastrarlas, los recordatorios (crear, editar, borrar, quién los ve) y
la clave de la suscripción .ics. Las pantallas (calendario/views.py) llaman a estas funciones.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.module_loading import import_string

from audiencias.selector import audiencia_de, opciones
from audiencias.servicios import crear_privada, filtrar_visibles, puede_ver
from base.registro import registro
from grupos.models import Grupo, Pertenencia
from permisos.servicios import puede

from .models import ClaveDeCalendario, Recordatorio

# Permiso para abrir un recordatorio al grupo padre o al abuelo (lo tiene la administración del grupo).
AMPLIAR = "calendario.ampliar_recordatorios"


# ── Juntar las fuentes ───────────────────────────────────────────────────────────────────────────────


# Todas las fechas que una persona ve entre dos momentos, de todas las fuentes del calendario. Devuelve
# una lista de pares (fuente, FechaDeCalendario). Cada fuente hace siempre las mismas consultas.
#   - usuario: quién mira.
#   - desde, hasta: el trozo de calendario (fechas con zona horaria).
def fechas(usuario, desde, hasta):
    resultado = []
    for fuente in registro.fuentes_de_calendario.values():
        resultado += [(fuente, fecha) for fecha in import_string(fuente.funcion)(usuario, desde, hasta)]
    return resultado


# Cambia la fecha de algo al arrastrarlo en el calendario: se lo pide a la fuente de donde sale. Lanza
# ValidationError si no se puede.
#   - codigo: el código de la fuente («eventos.eventos»).
#   - id: el número de la cosa dentro de su fuente.
#   - inicio, fin: las fechas nuevas (fin puede ser None).
def mover(usuario, codigo, id, inicio, fin):
    fuente = registro.fuentes_de_calendario.get(codigo)
    if fuente is None or not fuente.mover:
        raise ValidationError("Esto no se puede mover desde el calendario.")
    with transaction.atomic():
        import_string(fuente.mover)(usuario, id, inicio, fin)


# ── Recordatorios ────────────────────────────────────────────────────────────────────────────────────


# Grupos en los que una persona puede apuntar recordatorios: aquellos de los que es miembro (todos, si es
# superadmin), en orden de árbol.
def grupos_para_recordar(usuario):
    consulta = Grupo.objects.en_orden_de_arbol().select_related("organizacion")
    if usuario.is_superuser:
        return list(consulta)
    return list(consulta.filter(pertenencias__usuario=usuario).distinct())


# Opciones de «¿Quién lo ve?» para un recordatorio en un grupo: solo yo y mi grupo; y, para quien tiene
# «calendario.ampliar_recordatorios» (la administración del grupo), hasta el padre y el abuelo, si la
# organización lo permite. Lista de (clave, explicación).
def opciones_de_recordatorio(usuario, grupo):
    permitidas = {"privado", "grupo:0"}
    if puede(usuario, AMPLIAR, grupo=grupo):
        permitidas |= {"grupo:1", "grupo:2"}
    resultado = []
    for clave, texto in opciones(grupo):
        if clave == "privado":
            resultado.append((clave, "Solo yo"))
        elif clave in permitidas:
            resultado.append((clave, texto))
    return resultado


# Dice si una persona ve un recordatorio: quien lo apuntó o alguien de su audiencia.
def ve(usuario, recordatorio):
    return recordatorio.autor_id == usuario.pk or puede_ver(usuario, recordatorio.audiencia_id)


# Dice si una persona puede cambiar o borrar un recordatorio: quien lo apuntó, la administración del
# grupo (con «calendario.ampliar_recordatorios») si lo ve, o el superadmin si lo ve.
#   - ya_lo_ve: True si ya se sabe que lo ve (en las listas de lo visible), para no volver a mirarlo.
def puede_gestionar(usuario, recordatorio, ya_lo_ve=False):
    if recordatorio.autor_id == usuario.pk:
        return True
    if not (usuario.is_superuser or puede(usuario, AMPLIAR, grupo=recordatorio.grupo_id)):
        return False
    return ya_lo_ve or ve(usuario, recordatorio)


# Comprueba que la visibilidad elegida está entre las que se ofrecen a esa persona en ese grupo.
def _comprobar_visibilidad(usuario, grupo, visibilidad):
    if visibilidad not in dict(opciones_de_recordatorio(usuario, grupo)):
        raise ValidationError("Esa visibilidad no está disponible para ti en ese grupo.")


# Audiencia de un recordatorio según la visibilidad elegida. «Solo yo» es contenido personal: ni el
# superadmin lo ve.
def _audiencia(visibilidad, grupo, autor):
    if visibilidad == "privado":
        return crear_privada([autor], personal=True)
    return audiencia_de(visibilidad, grupo)


# Apunta un recordatorio. Devuelve el recordatorio.
#   - usuario: quién lo apunta (debe ser miembro del grupo).
#   - grupo: el grupo.
#   - datos: titulo, notas, todo_el_dia, inicio, fin.
#   - visibilidad: la clave elegida («privado», «grupo:0»…).
@transaction.atomic
def crear_recordatorio(usuario, grupo, datos, visibilidad):
    if not usuario.is_superuser and not Pertenencia.objects.filter(usuario=usuario, grupo=grupo).exists():
        raise ValidationError("Solo puedes apuntar recordatorios en tus grupos.")
    _comprobar_visibilidad(usuario, grupo, visibilidad)
    recordatorio = Recordatorio(autor=usuario, grupo=grupo, visibilidad=visibilidad, audiencia=_audiencia(visibilidad, grupo, usuario), **datos)
    recordatorio.full_clean()
    recordatorio.save()
    return recordatorio


# Cambia un recordatorio (sus datos y, si se pasa, quién lo ve). Devuelve el recordatorio.
@transaction.atomic
def editar_recordatorio(usuario, recordatorio, datos, visibilidad=None):
    if not puede_gestionar(usuario, recordatorio):
        raise ValidationError("Solo quien lo apuntó o la administración del grupo pueden cambiarlo.")
    for campo, valor in datos.items():
        setattr(recordatorio, campo, valor)
    if visibilidad and visibilidad != recordatorio.visibilidad:
        _comprobar_visibilidad(usuario, recordatorio.grupo, visibilidad)
        recordatorio.audiencia = _audiencia(visibilidad, recordatorio.grupo, recordatorio.autor)
        recordatorio.visibilidad = visibilidad
    recordatorio.full_clean()
    recordatorio.save()
    return recordatorio


# Borra un recordatorio.
@transaction.atomic
def borrar_recordatorio(usuario, recordatorio):
    if not puede_gestionar(usuario, recordatorio):
        raise ValidationError("Solo quien lo apuntó o la administración del grupo pueden borrarlo.")
    recordatorio.delete()


# Consulta de los recordatorios que ve una persona (sin ejecutar).
def recordatorios_visibles(usuario):
    de_su_audiencia = filtrar_visibles(Recordatorio.objects.all(), usuario)
    return Recordatorio.objects.filter(Q(pk__in=de_su_audiencia.values("pk")) | Q(autor=usuario))


# ── Suscripción .ics ─────────────────────────────────────────────────────────────────────────────────


# La clave de la suscripción de una persona (se crea la primera vez que se pide).
def clave_de(usuario):
    return ClaveDeCalendario.objects.get_or_create(usuario=usuario)[0]


# Cambia la clave de una persona: la dirección anterior deja de funcionar. Devuelve la clave nueva.
def cambiar_clave(usuario):
    from .models import clave_nueva

    clave = clave_de(usuario)
    clave.clave = clave_nueva()
    clave.save(update_fields=["clave", "creada"])
    return clave
