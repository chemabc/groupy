"""
Operaciones del módulo «eventos»: convocar (una reunión, con su solicitud de apoyos), editar, cancelar,
responder a «¿Vas a ir?» y los cometidos de cada evento (facilitación, logística…). Las pantallas
(eventos/views.py) llaman a estas funciones.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from audiencias.selector import audiencia_de
from audiencias.servicios import anadir_personas, filtrar_visibles, puede_ver
from eventos_sw.servicios import emitir
from grupos.acceso import grupos_que_administra
from grupos.models import Contencion
from permisos.models import Cometido
from permisos.servicios import asignar_cometido, exigir, puede, quitar_cometido
from solicitudes.servicios import pedir
from tipologias.servicios import cadena

from .models import Asistencia, Evento

# Tipo de ancla de los eventos (para los cometidos, las invitaciones…).
ANCLA = "eventos.evento"
# Nombre de la tipología común de las reuniones: las suyas (y sus subtipos) necesitan una solicitud con
# apoyos para convocarse (docs/diseno.md, apartados 6 y 10.3).
REUNION = "Reunión"


# Dice si una tipología es de reunión: ella o la principal de su rama es la «Reunión» común.
def es_reunion(tipologia):
    principal = cadena(tipologia)[0]
    return principal.nombre == REUNION and principal.organizacion_id is None


# ── Convocar ─────────────────────────────────────────────────────────────────────────────────────────


# Convoca un evento. Si es una reunión, queda pendiente y se pide la solicitud con apoyos al grupo al que
# llega (2 apoyos en el propio grupo, 5 en el padre, 10 en el abuelo); al aceptarse, se convoca sola. Si
# no, se convoca ya y se avisa a quien lo ve. Devuelve el evento.
#   - usuario: quien convoca (necesita «eventos.convocar» en el grupo).
#   - grupo: el grupo que convoca.
#   - tipologia: su tipo.
#   - datos: los campos del evento (titulo, descripcion, modalidad, lugar, direccion, url, inicio,
#     duracion, coste, coste_detalle, cartel, texto_para_redes).
#   - visibilidad: la clave elegida en el selector («privado», «grupo:1»…).
#   - campos: los valores de los campos de su tipología (ya en JSON).
#   - justificacion: para la solicitud de una reunión.
@transaction.atomic
def convocar(usuario, grupo, tipologia, datos, visibilidad, campos=None, justificacion=""):
    exigir(usuario, "eventos.convocar", grupo=grupo)
    reunion = es_reunion(tipologia)
    if reunion:
        # Mientras no tiene apoyos, solo la ve quien la convoca.
        audiencia = audiencia_de("privado", grupo, personas=[usuario])
    else:
        audiencia = audiencia_de(visibilidad, grupo, personas=[usuario])
    evento = Evento(
        grupo=grupo, convocante=usuario, tipologia=tipologia, audiencia=audiencia, visibilidad=visibilidad, campos=campos or {},
        estado=Evento.PENDIENTE if reunion else Evento.CONVOCADO, **datos,
    )
    evento.full_clean()
    evento.save()
    if reunion:
        destino, altura = _grupo_que_apoya(grupo, visibilidad)
        pedir(
            usuario, "eventos.reunion", destino, f"Reunión «{evento.titulo}» el {timezone.localtime(evento.inicio):%d/%m/%Y a las %H:%M}",
            justificacion, datos={"evento_id": evento.pk}, altura=altura,
        )
    else:
        emitir("eventos.convocado", evento_id=evento.pk)
    return evento


# Grupo al que se pide la solicitud de una reunión y a qué altura está: el grupo al que llega según la
# visibilidad elegida (su grupo, el padre, el abuelo…; para toda la organización o lo público, el grupo
# más alto). Devuelve (grupo, altura).
def _grupo_que_apoya(grupo, visibilidad):
    encima = list(Contencion.objects.filter(descendiente=grupo).select_related("antecesor").order_by("distancia"))
    if visibilidad.startswith("grupo:"):
        altura = min(int(visibilidad.split(":")[1]), len(encima) - 1)
    elif visibilidad in ("organizacion", "publico"):
        altura = len(encima) - 1
    else:
        altura = 0
    return encima[altura].antecesor, altura


# Convoca la reunión cuando su solicitud consigue los apoyos (la llama «solicitudes»; ver el
# TipoDeSolicitud «eventos.reunion» en eventos/apps.py). Le pone la visibilidad elegida y avisa.
# Devuelve el ancla del evento.
#   - solicitud: la solicitud aceptada (sus datos llevan «evento_id»).
def convocar_reunion(solicitud):
    evento = Evento.objects.select_related("grupo__organizacion").get(pk=solicitud.datos["evento_id"])
    evento.audiencia = audiencia_de(evento.visibilidad, evento.grupo, personas=[evento.convocante] if evento.convocante else [])
    evento.estado = Evento.CONVOCADO
    evento.save(update_fields=["audiencia", "estado"])
    emitir("eventos.convocado", evento_id=evento.pk)
    return (ANCLA, evento.pk)


# ── Editar y cancelar ────────────────────────────────────────────────────────────────────────────────


# Consulta de los eventos de los grupos que una persona administra y de sus subgrupos (todos, si es
# superadmin), en cualquier estado: también los que esperan apoyos y los cancelados. Sin ejecutar. Es lo que
# sale en «Administrar → Eventos de mis grupos».
def de_grupos_administrados(usuario):
    if usuario.is_superuser:
        return Evento.objects.all()
    return Evento.objects.filter(grupo_id__in=grupos_que_administra(usuario))


# Dice si una persona administra el grupo de un evento (o uno que lo contiene). Una consulta, o ninguna si
# no administra nada.
def administra(usuario, evento):
    return usuario.is_superuser or evento.grupo_id in grupos_que_administra(usuario)


# Dice si una persona puede editar o cancelar un evento: quien lo convocó, la administración del grupo
# (con «grupos.editar_grupo» en él, o porque administra un grupo que lo contiene) o el superadmin.
def puede_gestionar(usuario, evento):
    if usuario.is_superuser or evento.convocante_id == usuario.pk:
        return True
    return puede(usuario, "grupos.editar_grupo", grupo=evento.grupo_id) or administra(usuario, evento)


# Cambia los datos de un evento. La visibilidad de una reunión ya convocada no cambia (se pidieron apoyos
# para esa). Si es una vez de una serie, queda «cambiada a mano»: los cambios de la serie ya no le
# afectan. Devuelve el evento.
@transaction.atomic
def editar(usuario, evento, datos, visibilidad=None, campos=None):
    if not puede_gestionar(usuario, evento):
        raise ValidationError("Solo quien lo convocó o la administración del grupo pueden cambiarlo.")
    for campo, valor in datos.items():
        setattr(evento, campo, valor)
    if campos is not None:
        evento.campos = campos
    if evento.serie_id:
        evento.tocado = True
    if visibilidad and visibilidad != evento.visibilidad and evento.estado == Evento.CONVOCADO and not es_reunion(evento.tipologia):
        evento.audiencia = audiencia_de(visibilidad, evento.grupo, personas=[evento.convocante] if evento.convocante else [])
        evento.visibilidad = visibilidad
    evento.full_clean()
    evento.save()
    return evento


# Cancela un evento y avisa a quienes iban (o dudaban). Si es una vez de una serie, solo se cancela esa
# (queda «cambiada a mano»: la serie no la vuelve a convocar).
@transaction.atomic
def cancelar(usuario, evento):
    if not puede_gestionar(usuario, evento):
        raise ValidationError("Solo quien lo convocó o la administración del grupo pueden cancelarlo.")
    evento.estado = Evento.CANCELADO
    evento.tocado = bool(evento.serie_id)
    evento.save(update_fields=["estado", "tocado"])
    emitir("eventos.cancelado", evento_id=evento.pk)


# ── Ver, asistencia y cometidos ──────────────────────────────────────────────────────────────────────


# Consulta de los eventos que ve una persona: los convocados de sus audiencias y los suyos (también los
# pendientes de apoyos). Sin ejecutar.
def visibles(usuario):
    convocados = filtrar_visibles(Evento.objects.filter(estado__in=[Evento.CONVOCADO, Evento.CANCELADO]), usuario)
    return Evento.objects.filter(Q(pk__in=convocados.values("pk")) | Q(convocante=usuario))


# Dice si una persona ve un evento: quien lo convocó y la administración de su grupo siempre (también
# mientras espera apoyos); las demás, si está convocado (o cancelado) y les llega.
def ve(usuario, evento):
    if evento.convocante_id == usuario.pk:
        return True
    if evento.estado != Evento.PENDIENTE and puede_ver(usuario, evento.audiencia):
        return True
    return administra(usuario, evento)


# Responde a «¿Vas a ir?» (o cambia la respuesta). Hace falta ver el evento y que esté convocado.
#   - respuesta: Asistencia.SI, NO o NO_SE.
@transaction.atomic
def responder(usuario, evento, respuesta):
    if evento.estado != Evento.CONVOCADO or not ve(usuario, evento):
        raise ValidationError("No puedes responder a este evento.")
    if respuesta not in dict(Asistencia.RESPUESTAS):
        raise ValidationError("Respuesta desconocida.")
    Asistencia.objects.update_or_create(evento=evento, usuario=usuario, defaults={"respuesta": respuesta})


# Cuántas personas han respondido cada cosa: {«si»: 3, «no»: 1, «no_se»: 2}. Una consulta.
def recuento(evento):
    cuentas = dict(evento.asistencias.values("respuesta").annotate(n=Count("pk")).values_list("respuesta", "n"))
    return {codigo: cuentas.get(codigo, 0) for codigo, _nombre in Asistencia.RESPUESTAS}


# Cometidos de un evento: lista de Cometido (con su usuario). Una consulta.
def cometidos(evento):
    return list(Cometido.objects.filter(ancla_tipo=ANCLA, ancla_id=evento.pk).select_related("usuario").order_by("codigo", "usuario__alias"))


# Dice si una persona ve los alias de quien va: quien convoca, quien tiene un cometido en el evento y el
# superadmin (decisión 3A).
#   - de_cometidos: la lista de cometidos() ya cargada.
def ve_quien_va(usuario, evento, de_cometidos):
    return usuario.is_superuser or evento.convocante_id == usuario.pk or any(c.usuario_id == usuario.pk for c in de_cometidos)


# Apunta a una persona a un cometido del evento (ella misma, o quien gestiona el evento a otra). Si el
# evento es privado, la persona pasa a verlo.
#   - quien: quien lo hace.
#   - persona: a quién se apunta.
#   - codigo: código del cometido («eventos.logistica»).
@transaction.atomic
def apuntar(quien, evento, persona, codigo):
    if quien.pk != persona.pk and not puede_gestionar(quien, evento):
        raise ValidationError("Solo quien gestiona el evento puede apuntar a otras personas.")
    if quien.pk == persona.pk and not ve(quien, evento):
        raise ValidationError("No puedes apuntarte a este evento.")
    if Cometido.objects.filter(usuario=persona, codigo=codigo, ancla_tipo=ANCLA, ancla_id=evento.pk).exists():
        return
    asignar_cometido(persona, codigo, ANCLA, evento.pk, grupo=evento.grupo)
    if evento.audiencia.tipo == "privada":
        anadir_personas(evento.audiencia, [persona])


# Quita a una persona de un cometido del evento (ella misma o quien gestiona el evento).
@transaction.atomic
def desapuntar(quien, evento, persona, codigo):
    if quien.pk != persona.pk and not puede_gestionar(quien, evento):
        raise ValidationError("Solo quien gestiona el evento puede quitar a otras personas.")
    quitar_cometido(persona, codigo, ANCLA, evento.pk)
