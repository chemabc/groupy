# Activa en PostgreSQL la extensión «unaccent», que quita las tildes al comparar textos. La usan las
# tablas filtrables cuando buscan en el servidor (base/tablas.py), para que «reunion» encuentre «reunión».
# Escrita a mano: no crea ninguna tabla, solo activa la extensión.

from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Activa la extensión unaccent en la base de datos de la plataforma."""

    # Es la primera migración de «base»: no depende de ninguna otra.
    dependencies = []

    # Lo que hace: crear la extensión si no existe (y quitarla si se deshace la migración).
    operations = [UnaccentExtension()]
