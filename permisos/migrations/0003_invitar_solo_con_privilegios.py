"""
Migración de datos: «grupos.invitar» (invitar a un grupo de otra organización) pasa de ser de cualquier
miembro a ser solo de los admins del grupo y de la organización (13 de noviembre de 2026). Los permisos
por defecto solo se aplican la primera vez que aparece un permiso, así que en las bases donde ya estaba
repartido hay que cambiarlo aquí.
"""

from django.db import migrations

# Código del permiso que cambia.
PERMISO = "grupos.invitar"


# Si el permiso ya se había repartido: se le quita al rol «usuario» y se da a los dos roles de admin.
#   - apps: las tablas tal como están en este punto de las migraciones.
def solo_con_privilegios(apps, schema_editor):
    PermisoConocido = apps.get_model("permisos", "PermisoConocido")
    PermisoDeRol = apps.get_model("permisos", "PermisoDeRol")
    if not PermisoConocido.objects.filter(codigo=PERMISO).exists():
        return
    PermisoDeRol.objects.filter(rol_id="usuario", permiso=PERMISO).delete()
    for rol in ("admin_grupo", "admin_org"):
        PermisoDeRol.objects.get_or_create(rol_id=rol, permiso=PERMISO)


# Deshace la migración: vuelve a dárselo a cualquier miembro.
def como_antes(apps, schema_editor):
    PermisoDeRol = apps.get_model("permisos", "PermisoDeRol")
    if apps.get_model("permisos", "PermisoConocido").objects.filter(codigo=PERMISO).exists():
        PermisoDeRol.objects.get_or_create(rol_id="usuario", permiso=PERMISO)


class Migration(migrations.Migration):
    """Invitar a otra organización, solo con privilegios."""

    dependencies = [("permisos", "0002_roles_del_sistema")]

    operations = [migrations.RunPython(solo_con_privilegios, como_antes)]
