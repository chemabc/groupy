#!/usr/bin/env python
# Punto de entrada de las órdenes de Django en la terminal: arrancar el servidor, crear tablas,
# lanzar las pruebas… Por ejemplo: python manage.py runserver 0.0.0.0:8000
import os
import sys


# Lee la orden escrita en la terminal y se la pasa a Django, después de indicarle dónde está la
# configuración del proyecto (config/settings.py).
def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


# Solo se ejecuta cuando se llama al fichero directamente («python manage.py …»).
if __name__ == "__main__":
    main()
