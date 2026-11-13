"""
Migración: las etiquetas pasan a guardarse con la primera letra en mayúscula, el resto en minúsculas y
sin tildes (13 de noviembre de 2026). Cambia el texto de ayuda del nombre y pone en esa forma las
etiquetas que ya había, con sus palabras relacionadas.
"""

from django.db import migrations, models

from base.tablas import forma_de_frase


# Pone en la forma nueva el nombre y las palabras relacionadas de cada etiqueta que ya existe. La forma
# normalizada no cambia (ya iba sin tildes ni mayúsculas), así que no puede chocar con otra.
#   - apps: las tablas tal como estaban en este punto de las migraciones.
#   - editor: el que aplica la migración (no se usa).
def dar_forma(apps, editor):
    Etiqueta = apps.get_model("etiquetas", "Etiqueta")
    for etiqueta in Etiqueta.objects.all():
        etiqueta.nombre = forma_de_frase(etiqueta.nombre)
        palabras = [forma_de_frase(palabra) for palabra in etiqueta.relacionadas.split(",") if palabra.strip()]
        etiqueta.relacionadas = ", ".join(palabras)
        etiqueta.save(update_fields=["nombre", "relacionadas"])


class Migration(migrations.Migration):

    dependencies = [
        ("etiquetas", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="etiqueta",
            name="nombre",
            field=models.CharField(
                help_text="De una a tres palabras. Al guardar queda con la primera letra en mayúscula, el resto en minúsculas y sin tildes.",
                max_length=40,
                verbose_name="nombre",
            ),
        ),
        # Hacia atrás no hace nada: no se pueden recuperar las tildes quitadas.
        migrations.RunPython(dar_forma, migrations.RunPython.noop),
    ]
