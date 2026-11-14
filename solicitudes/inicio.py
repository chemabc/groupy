"""
Tarjeta «Solicitudes» de «Inicio → Panel» (declarada en solicitudes/apps.py; dónde sale lo decide
config/inicio.py). Resume las solicitudes pendientes:

- Recibidas: las de tus grupos (y de los que los contienen) que puedes apoyar o rechazar y aún no has
  respondido.
- Enviadas: las que has pedido tú y siguen pendientes.

Lo que espera el sí de la administración no sale aquí: está en «Administrar → Por aprobar».
"""

from django.urls import reverse
from base.contrato import ApartadoDeTarjeta, FilaDeResumen, ResumenDeTarjeta
from base.registro import registro
from grupos.models import Contencion

from .models import Apoyo, Solicitud
from .servicios import para_apoyar_para

# Cuántas líneas enseña cada apartado como mucho (las más recientes).
FILAS = 5


# Pasa una solicitud a una línea de la tarjeta: qué se pide y en qué grupo, con sus apoyos.
#   - solicitud: la Solicitud, con su grupo cargado.
#   - destacada: si espera algo de quien mira.
def _fila(solicitud, destacada=False):
    tipo = registro.solicitudes.get(solicitud.tipo)
    nombre = tipo.nombre if tipo else solicitud.tipo
    return FilaDeResumen(
        f"{nombre}: {solicitud.grupo.nombre}",
        reverse("solicitudes:solicitud", args=[solicitud.pk]),
        f"{solicitud.apoyos} de {solicitud.apoyos_necesarios} apoyos",
        solicitud.creada,
        destacada,
    )


# Hace el resumen de la tarjeta para una persona. Cuesta 3 consultas, haya lo que haya: el total de lo
# recibido es el número del menú («Para apoyar (N)»), que ya está en la caché.
#   - usuario: quien mira.
def pendientes(usuario):
    vivas = Solicitud.objects.filter(estado=Solicitud.PENDIENTE).select_related("grupo").order_by("-creada")
    respondidas = Apoyo.objects.filter(usuario=usuario).values("solicitud_id")
    # Sus grupos y los que los contienen, como subconsulta (sin una consulta aparte).
    mios = Contencion.objects.filter(descendiente__pertenencias__usuario=usuario).values("antecesor_id")
    para_apoyar = vivas.filter(grupo_id__in=mios).exclude(solicitante=usuario).exclude(pk__in=respondidas)
    mias = vivas.filter(solicitante=usuario)
    return ResumenDeTarjeta(
        apartados=(
            ApartadoDeTarjeta(
                "Recibidas, para apoyar",
                tuple(_fila(solicitud, destacada=True) for solicitud in para_apoyar[:FILAS]),
                total=para_apoyar_para(usuario),
                enlace=reverse("solicitudes:pendientes"),
                vacio="Nada que apoyar.",
            ),
            ApartadoDeTarjeta(
                "Enviadas",
                tuple(_fila(solicitud) for solicitud in mias[:FILAS]),
                total=mias.count(),
                enlace=reverse("solicitudes:mias"),
                vacio="No tienes ninguna pendiente.",
            ),
        ),
        enlace=reverse("solicitudes:mias"),
        boton="Ir a solicitudes",
    )
