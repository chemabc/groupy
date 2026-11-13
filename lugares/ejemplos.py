"""
Lugares de ejemplo: unos cuantos centros con su enlace de OpenStreetMap (del que salen las coordenadas),
y el lugar de algunos usuarios de ejemplo. Seis personas comparten el IES Complutense, para que se vea un
recuento (solo se muestran a partir de 5). Los crea y borra la orden «python manage.py ejemplos».
"""

from django.contrib.auth import get_user_model

from .models import Lugar, LugarDePersona

# Lugares de ejemplo: (nombre, dirección, URL de localización, teléfonos, notas).
LUGARES = [
    ("IES Complutense", "Vía Complutense 19, 28805 Alcalá de Henares", "https://www.openstreetmap.org/#map=18/40.4896/-3.3700", "918 890 000", "Entrada por el patio."),
    ("Hospital del Henares", "Av. de Marie Curie s/n, 28822 Coslada", "https://www.openstreetmap.org/#map=18/40.4310/-3.5350", "", ""),
    ("CEIP Manzanares", "C/ del Río 3, 28005 Madrid", "https://www.openstreetmap.org/#map=18/40.4100/-3.7200", "", ""),
    ("IES Ebro", "Av. de Cataluña 3, 50014 Zaragoza", "https://www.openstreetmap.org/#map=18/41.6600/-0.8700", "", ""),
    ("Centro de Salud Arga", "C/ Arga 2, 31014 Pamplona", "https://www.openstreetmap.org/#map=18/42.8300/-1.6500", "", ""),
    ("IES Pisuerga", "Paseo de Zorrilla 50, 47006 Valladolid", "https://www.openstreetmap.org/#map=18/41.6400/-4.7400", "", ""),
    ("Hospital del Darro", "Carrera del Darro 10, 18010 Granada", "https://www.openstreetmap.org/#map=18/37.1780/-3.5930", "", ""),
]

# Lugar de algunos usuarios de ejemplo: (alias, nombre del lugar).
ELECCIONES = [
    ("Lince", "IES Complutense"), ("Nutria", "IES Complutense"), ("Garza", "IES Complutense"),
    ("Búho", "IES Complutense"), ("Ardilla", "IES Complutense"), ("Tejón", "IES Complutense"),
    ("Zorro", "Centro de Salud Arga"), ("Encina", "IES Pisuerga"), ("Sauce", "Hospital del Darro"),
]


# Crea los lugares que falten y el lugar de los usuarios de ejemplo que aún no tienen.
def crear():
    for nombre, direccion, url, telefonos, notas in LUGARES:
        if not Lugar.objects.filter(nombre=nombre).exists():
            Lugar(nombre=nombre, direccion=direccion, url_localizacion=url, telefonos=telefonos, notas=notas).save()
    lugares = {lugar.nombre: lugar for lugar in Lugar.objects.filter(nombre__in=[fila[0] for fila in LUGARES])}
    usuarios = {usuario.alias: usuario for usuario in get_user_model().objects.filter(alias__in=[alias for alias, _ in ELECCIONES])}
    for alias, nombre in ELECCIONES:
        if alias in usuarios and not LugarDePersona.objects.filter(usuario=usuarios[alias]).exists():
            LugarDePersona.objects.create(usuario=usuarios[alias], lugar=lugares[nombre])


# Borra los lugares de ejemplo (y el lugar elegido de quien los tenía).
def borrar():
    nombres = [fila[0] for fila in LUGARES]
    LugarDePersona.objects.filter(lugar__nombre__in=nombres).delete()
    Lugar.objects.filter(nombre__in=nombres).delete()
