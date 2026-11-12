"""
Orden «python manage.py sincronizar_permisos»: da a los permisos nuevos de los contratos sus roles por
defecto. Se hace sola después de cada «migrate»; esta orden sirve para hacerlo a mano.
"""

from django.core.management.base import BaseCommand

from permisos.servicios import sincronizar_permisos


class Command(BaseCommand):
    """Da sus roles por defecto a los permisos que no se habían visto nunca."""

    help = "Da sus roles por defecto a los permisos nuevos declarados en los contratos."

    # Ejecuta la sincronización y dice qué permisos eran nuevos.
    def handle(self, *args, **opciones):
        nuevos = sincronizar_permisos()
        texto = ", ".join(nuevos) if nuevos else "ninguno"
        self.stdout.write(self.style.SUCCESS(f"Permisos nuevos: {texto}."))
