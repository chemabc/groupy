# Punto de entrada para servir la aplicación con un servidor web clásico (por ejemplo, gunicorn en
# producción). Django lo usa a través del ajuste WSGI_APPLICATION de config/settings.py.
import os

from django.core.wsgi import get_wsgi_application

# Indica dónde está la configuración del proyecto antes de crear la aplicación.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Objeto que el servidor web llama en cada petición.
application = get_wsgi_application()
