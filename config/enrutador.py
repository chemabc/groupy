"""
Enrutador de bases de datos: decide en qué base va cada tabla (ver docs/registro-y-validacion.md).

- Las tablas del módulo «boveda» (la identidad real) van solo a la base «boveda».
- Todas las demás van solo a la base de la plataforma («default»).
- Se prohíbe cualquier relación entre una tabla de la bóveda y una de la plataforma: así nadie puede
  crear por error una columna que una a una persona con su alias.

Django lo usa porque está en DATABASE_ROUTERS (config/settings.py).
"""

# Nombre del módulo cuyas tablas van a la bóveda, y nombre de esa base en DATABASES.
MODULO_DE_LA_BOVEDA = "boveda"
BASE_DE_LA_BOVEDA = "boveda"


class EnrutadorDeLaBoveda:
    """Manda las tablas de la bóveda a su base y las demás a la de la plataforma."""

    # Base de la que se leen las filas de un modelo.
    def db_for_read(self, model, **pistas):
        return BASE_DE_LA_BOVEDA if model._meta.app_label == MODULO_DE_LA_BOVEDA else "default"

    # Base en la que se escriben (la misma que para leer).
    def db_for_write(self, model, **pistas):
        return self.db_for_read(model)

    # Dos filas solo pueden relacionarse (clave ajena) si están en la misma base.
    def allow_relation(self, objeto1, objeto2, **pistas):
        return (objeto1._meta.app_label == MODULO_DE_LA_BOVEDA) == (objeto2._meta.app_label == MODULO_DE_LA_BOVEDA)

    # En qué base se crean las tablas de cada módulo al ejecutar «migrate».
    def allow_migrate(self, db, app_label, **pistas):
        if app_label == MODULO_DE_LA_BOVEDA:
            return db == BASE_DE_LA_BOVEDA
        return db == "default"
