"""
Etiquetas de ejemplo: unas comunes a todas las organizaciones y otras propias de «ORG Tajo». Las crea y
las borra la orden «python manage.py ejemplos» (después de las organizaciones de ejemplo).
"""

from grupos.models import Organizacion

from base.tablas import normalizar

from .models import Etiqueta

# Etiquetas comunes: nombre y palabras relacionadas.
COMUNES = [
    ("asamblea", "reunión general"),
    ("huelga", "paro, parón"),
    ("difusión", "carteles, redes"),
    ("acogida", "bienvenida, personas nuevas"),
]
# Etiquetas propias de ORG Tajo.
DE_TAJO = [("local nuevo", "sede"), ("cuidados", "conciliación")]


# Crea las etiquetas de ejemplo que falten.
def crear():
    for nombre, relacionadas in COMUNES:
        if not Etiqueta.objects.filter(organizacion__isnull=True, normalizada=normalizar(nombre)).exists():
            Etiqueta.objects.create(nombre=nombre, relacionadas=relacionadas)
    tajo = Organizacion.objects.filter(nombre="ORG Tajo").first()
    for nombre, relacionadas in DE_TAJO if tajo else []:
        if not Etiqueta.objects.filter(organizacion=tajo, normalizada=normalizar(nombre)).exists():
            Etiqueta.objects.create(organizacion=tajo, nombre=nombre, relacionadas=relacionadas)


# Borra las etiquetas de ejemplo (las de ORG Tajo se van con la organización). Se buscan por su forma
# normalizada, porque al guardarse cambian de forma («difusión» queda «Difusion»).
def borrar():
    comunes = [normalizar(nombre) for nombre, _ in COMUNES]
    de_tajo = [normalizar(nombre) for nombre, _ in DE_TAJO]
    Etiqueta.objects.filter(organizacion__isnull=True, normalizada__in=comunes).delete()
    Etiqueta.objects.filter(organizacion__nombre="ORG Tajo", normalizada__in=de_tajo).delete()
