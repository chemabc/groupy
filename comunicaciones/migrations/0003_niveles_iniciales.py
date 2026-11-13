"""
Crea los tres niveles de aviso iniciales (Información, Atención y Problema), que el superadmin puede
cambiar después en «Configuración → Niveles de aviso».
"""

from django.db import migrations

# Niveles iniciales: (nombre, descripción, color, orden).
NIVELES = [
    ("Información", "Para que se sepa; no hace falta hacer nada.", "#2563eb", 10),
    ("Atención", "Hay que tenerlo en cuenta o hacer algo pronto.", "#d97706", 20),
    ("Problema", "Algo va mal y hay que atenderlo cuanto antes.", "#dc2626", 30),
]


# Crea los niveles que falten (por su nombre).
def crear(apps, schema_editor):
    NivelDeAviso = apps.get_model("comunicaciones", "NivelDeAviso")
    for nombre, descripcion, color, orden in NIVELES:
        NivelDeAviso.objects.get_or_create(nombre=nombre, defaults={"descripcion": descripcion, "color": color, "orden": orden})


# Al deshacer la migración no se borra nada (podrían estar en uso).
def nada(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("comunicaciones", "0002_avisos_de_administracion")]
    operations = [migrations.RunPython(crear, nada)]
