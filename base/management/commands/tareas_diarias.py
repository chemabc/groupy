"""
Orden «python manage.py tareas_diarias»: ejecuta ahora las tareas diarias de todos los módulos (las
TareaDiaria de sus contratos), aunque hoy ya se hayan hecho. Normalmente no hace falta: el trabajador las
ejecuta solo una vez al día (ver base/tareas.py).
"""

from django.core.management.base import BaseCommand

from base.tareas import ejecutar_todas


class Command(BaseCommand):
    """Ejecuta las tareas diarias de los módulos."""

    help = "Ejecuta ahora las tareas diarias de todos los módulos (caducar solicitudes, series de eventos…)."

    # Lo que hace la orden: ejecutarlas y decir qué ha devuelto cada una.
    def handle(self, *args, **opciones):
        for codigo, resultado in ejecutar_todas():
            self.stdout.write(f"{codigo}: {resultado}")
