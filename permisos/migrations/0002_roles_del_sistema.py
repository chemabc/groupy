"""
Migración de datos: crea los tres roles del sistema (usuario, admin del grupo y admin de la
organización), que deben existir siempre. Qué permisos tiene cada uno lo pone después
sincronizar_permisos(), con lo que dice cada contrato.
"""

from django.db import migrations

# Roles del sistema: código, nombre visible, descripción y nivel.
ROLES = [
    ("usuario", "Usuario", "Cualquier miembro de un grupo. Sus permisos valen en su grupo y en todos los que lo contienen.", "grupo"),
    ("admin_grupo", "Admin del grupo", "Cuida la estructura del grupo; no filtra. Sus permisos valen solo en ese grupo.", "grupo"),
    ("admin_org", "Admin de la organización", "Administra una organización. Sus permisos valen en ella y en todos sus grupos.", "organizacion"),
]


# Crea los roles del sistema si no existen.
#   - apps: las tablas tal como están en este punto de las migraciones.
def crear_roles(apps, schema_editor):
    Rol = apps.get_model("permisos", "Rol")
    for codigo, nombre, descripcion, nivel in ROLES:
        Rol.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre, "descripcion": descripcion, "nivel": nivel, "del_sistema": True}
        )


# Deshace la migración: borra los roles del sistema.
def borrar_roles(apps, schema_editor):
    apps.get_model("permisos", "Rol").objects.filter(codigo__in=[rol[0] for rol in ROLES]).delete()


class Migration(migrations.Migration):
    """Crea los roles del sistema."""

    dependencies = [("permisos", "0001_initial")]

    operations = [migrations.RunPython(crear_roles, borrar_roles)]
