"""
Orden «python manage.py ejemplos crear» (o «borrar»): crea o borra los datos de ejemplo de todos los
módulos. Solo funciona con DEBUG encendido, porque los usuarios de ejemplo tienen una contraseña
conocida y nunca deben llegar al servidor real.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ejemplos.servicios import borrar_todos, crear_todos


class Command(BaseCommand):
    """Crea o borra los datos de ejemplo de todos los módulos."""

    help = "Crea o borra los datos de ejemplo de todos los módulos (solo en desarrollo)."

    # Declara los parámetros que acepta la orden.
    def add_arguments(self, parser):
        # accion: «crear» o «borrar».
        parser.add_argument("accion", choices=["crear", "borrar"], help="Qué hacer con los datos de ejemplo.")

    # Ejecuta la orden: comprueba que se está en desarrollo, crea o borra y dice qué módulos ha tocado.
    def handle(self, *args, accion, **opciones):
        if not settings.DEBUG:
            raise CommandError("Los datos de ejemplo solo se crean en desarrollo (DEBUG encendido).")
        etiquetas = crear_todos() if accion == "crear" else borrar_todos()
        hecho = "Creados" if accion == "crear" else "Borrados"
        self.stdout.write(self.style.SUCCESS(f"{hecho} los datos de ejemplo de: {', '.join(etiquetas)}."))
