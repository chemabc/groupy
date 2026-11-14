"""
Tarjeta «Comunicaciones» de «Inicio → Panel» (declarada en comunicaciones/apps.py; dónde sale lo decide
config/inicio.py). Resume lo que está pendiente:

- Recibidas: las notificaciones sin ver y las conversaciones con la administración que tienen una
  respuesta sin leer.
- Enviadas: las conversaciones que has empezado tú con la administración y siguen sin resolver (abiertas o
  en proceso), salvo las que tienen una respuesta sin leer, que ya salen en «Recibidas».

Lo que se atiende como admin no sale aquí: está en «Administrar → Buzón de la administración».
"""

from django.urls import reverse

from base.contrato import ApartadoDeTarjeta, FilaDeResumen, ResumenDeTarjeta

from .models import Conversacion, Notificacion
from .servicios import conversaciones_sin_leer, sin_ver as notificaciones_sin_ver

# Cuántas líneas enseña cada apartado como mucho (las más recientes).
FILAS = 5


# Hace el resumen de la tarjeta para una persona. Cuesta 4 consultas, haya lo que haya: los totales de lo
# recibido son los números del menú, que ya están en la caché.
#   - usuario: quien mira.
def pendientes(usuario):
    sin_ver = Notificacion.objects.filter(usuario=usuario, vista_el__isnull=True).order_by("-creada")
    con_respuesta = Conversacion.objects.filter(persona=usuario, pendiente_persona=True).order_by("-actualizada")
    esperando = (
        Conversacion.objects.filter(persona=usuario, pendiente_persona=False)
        .exclude(estado=Conversacion.SOLUCIONADA)
        .order_by("-actualizada")
    )
    recibidas = [
        FilaDeResumen(notificacion.texto, reverse("comunicaciones:abrir", args=[notificacion.pk]), "notificación", notificacion.creada, True)
        for notificacion in sin_ver[:FILAS]
    ] + [
        FilaDeResumen(conversacion.asunto, reverse("comunicaciones:conversacion", args=[conversacion.pk]), "respuesta de la administración", conversacion.actualizada, True)
        for conversacion in con_respuesta[:FILAS]
    ]
    recibidas.sort(key=lambda fila: fila.fecha, reverse=True)
    enviadas = [
        FilaDeResumen(conversacion.asunto, reverse("comunicaciones:conversacion", args=[conversacion.pk]), conversacion.get_estado_display().lower(), conversacion.actualizada)
        for conversacion in esperando[:FILAS]
    ]
    return ResumenDeTarjeta(
        apartados=(
            ApartadoDeTarjeta(
                "Recibidas",
                tuple(recibidas[:FILAS]),
                total=notificaciones_sin_ver(usuario) + conversaciones_sin_leer(usuario),
                enlace=reverse("comunicaciones:notificaciones"),
                vacio="Nada sin ver.",
            ),
            ApartadoDeTarjeta(
                "Enviadas, sin resolver",
                tuple(enviadas),
                total=esperando.count(),
                enlace=reverse("comunicaciones:conversaciones"),
                vacio="Nada sin resolver.",
            ),
        ),
        enlace=reverse("comunicaciones:notificaciones"),
        boton="Ir a comunicaciones",
    )
