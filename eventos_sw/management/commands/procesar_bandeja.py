"""
Orden «python manage.py procesar_bandeja»: el trabajador que entrega los avisos asíncronos.

Se deja funcionando en un proceso aparte. Mira la bandeja de salida, ejecuta los avisos pendientes y,
cuando no queda ninguno, espera un poco y vuelve a mirar. Se para con Ctrl+C. Además, la primera vuelta
de cada día ejecuta las tareas diarias de los módulos (base/tareas.py).

Es provisional: cuando se decida entre Celery y RQ (docs/diseno.md, apartado 20), cambiará quién llama
a procesar_bandeja, pero la bandeja seguirá igual.
"""

import time

from django.core.management.base import BaseCommand

from base.tareas import ejecutar_las_de_hoy
from eventos_sw.servicios import procesar_bandeja


class Command(BaseCommand):
    """Procesa la bandeja de salida de eventos_sw, en bucle o una sola vez."""

    help = "Entrega los avisos asíncronos de eventos_sw pendientes en la bandeja de salida."

    # Declara los parámetros que acepta la orden.
    def add_arguments(self, parser):
        # --una-vez: procesa lo que haya en ese momento y termina (útil para probar a mano).
        parser.add_argument(
            "--una-vez",
            action="store_true",
            help="Procesa lo pendiente y termina, en lugar de quedarse esperando.",
        )
        # --espera: segundos que espera antes de volver a mirar cuando la bandeja está vacía.
        parser.add_argument(
            "--espera",
            type=float,
            default=1.0,
            help="Segundos de espera cuando no hay nada pendiente (1 por defecto).",
        )

    # Lo que hace la orden: en cada vuelta, las tareas diarias (si hoy aún no se han hecho) y una tanda de
    # avisos; si no hay avisos, esperar y volver a mirar.
    def handle(self, *args, una_vez, espera, **opciones):
        self.stdout.write("Procesando la bandeja de eventos_sw. Ctrl+C para parar.")
        try:
            while True:
                for codigo, resultado in ejecutar_las_de_hoy() or ():
                    self.stdout.write(f"Tarea diaria {codigo}: {resultado}")
                procesados = procesar_bandeja()
                if procesados:
                    self.stdout.write(f"{procesados} avisos procesados.")
                elif una_vez:
                    break
                else:
                    time.sleep(espera)
        except KeyboardInterrupt:
            self.stdout.write("Parado.")
