"""
Talentos de ejemplo: un pequeño catálogo y los talentos de algunos usuarios de ejemplo, compartidos con su
asamblea base. Los crea y borra la orden «python manage.py ejemplos».
"""

from django.contrib.auth import get_user_model
from django.db.models import Q

from grupos.ejemplos import organizaciones_de_ejemplo
from grupos.models import Pertenencia

from .models import Compartido, PeticionDeTalentos, Talento, TalentoDePersona

# Catálogo de ejemplo: (nombre, tipo, palabras relacionadas).
CATALOGO = [
    ("Furgoneta", Talento.RECURSO, "Camioneta, Transporte"),
    ("Local", Talento.RECURSO, "Sala, Espacio"),
    ("Equipo de sonido", Talento.RECURSO, "Altavoces, Megafonia"),
    ("Trabajos verticales", Talento.HABILIDAD, "Escalada, Altura"),
    ("Diseño grafico", Talento.HABILIDAD, "Carteles, Ilustracion"),
    ("Traduccion", Talento.HABILIDAD, "Idiomas"),
]

# Talentos de algunos usuarios de ejemplo: (alias, nombre del talento).
TALENTOS = [
    ("Nutria", "Furgoneta"), ("Garza", "Furgoneta"), ("Lince", "Diseño grafico"), ("Búho", "Local"),
    ("Ardilla", "Trabajos verticales"), ("Tejón", "Equipo de sonido"), ("Zorro", "Traduccion"), ("Encina", "Furgoneta"),
]


# Crea el catálogo que falte y los talentos de los usuarios de ejemplo, compartidos con su asamblea base.
def crear():
    for nombre, tipo, relacionadas in CATALOGO:
        if not Talento.objects.filter(nombre=nombre).exists():
            Talento(nombre=nombre, tipo=tipo, relacionadas=relacionadas).save()
    talentos = {talento.nombre: talento for talento in Talento.objects.filter(nombre__in=[fila[0] for fila in CATALOGO])}
    usuarios = {usuario.alias: usuario for usuario in get_user_model().objects.filter(alias__in=[alias for alias, _ in TALENTOS])}
    bases = dict(Pertenencia.objects.filter(es_base=True, usuario__in=usuarios.values()).values_list("usuario_id", "grupo_id"))
    for alias, nombre in TALENTOS:
        if alias not in usuarios:
            continue
        suyo, nuevo = TalentoDePersona.objects.get_or_create(usuario=usuarios[alias], talento=talentos[nombre])
        if nuevo and usuarios[alias].pk in bases:
            Compartido.objects.create(talento_de_persona=suyo, grupo_id=bases[usuarios[alias].pk])


# Borra el catálogo de ejemplo (y, con él, los talentos de las personas y lo compartido). Antes quita las
# peticiones de talentos hechas al probar en los grupos de ejemplo o que piden un talento del catálogo de
# ejemplo: cada cosa pedida protege su talento, y sin esto no se podría borrar.
def borrar():
    nombres = [fila[0] for fila in CATALOGO]
    PeticionDeTalentos.objects.filter(
        Q(grupo__organizacion__in=organizaciones_de_ejemplo()) | Q(necesidades__talento__nombre__in=nombres)
    ).delete()
    Talento.objects.filter(nombre__in=nombres).delete()
