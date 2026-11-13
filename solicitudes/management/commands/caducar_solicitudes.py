"""
Orden «python manage.py caducar_solicitudes»: cierra como caducadas las solicitudes pendientes cuya fecha
ya ha pasado, y avisa a quien las pidió. Las pantallas de solicitudes ya lo hacen al abrirse; esta orden
es para ejecutarla una vez al día (con cron o con el trabajador de colas, cuando se elija).
"""

from django.core.management.base import BaseCommand

from solicitudes.servicios import caducar_vencidas


class Command(BaseCommand):
    """Caduca las solicitudes vencidas."""

    help = "Cierra como caducadas las solicitudes pendientes cuya fecha ya ha pasado."

    # Lo que hace la orden: caducar y decir cuántas.
    def handle(self, *args, **opciones):
        self.stdout.write(f"{caducar_vencidas()} solicitudes caducadas.")
