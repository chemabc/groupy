"""
Usuarios de ejemplo, para probar y medir las pantallas. Los crea y los borra la orden
«python manage.py ejemplos» (módulo «ejemplos»), que solo funciona en desarrollo.

Todos tienen la misma contraseña, que está escrita aquí: por eso nunca deben existir en el servidor
real. Cada cual puede cambiarla desde «Mi cuenta → Contraseña». Los alias son nombres de animales y de
árboles; varios llevan tilde o ñ, para probar que se puede entrar escribiéndolos sin ellas.
"""

from django.contrib.auth.hashers import make_password

from .models import Usuario, normalizar_alias

# Contraseña común de todos los usuarios de ejemplo.
CONTRASENA_DE_EJEMPLO = "M3n0sL3ctiv4s"

# Alias del superadmin de ejemplo.
SUPERADMIN_DE_EJEMPLO = "Águila"

# Alias de los demás usuarios de ejemplo: animales y árboles.
ALIAS_DE_EJEMPLO = [
    # Animales
    "Lince", "Nutria", "Tejón", "Garza", "Búho", "Ardilla", "Zorro", "Cigüeña", "Erizo", "Jabalí",
    "Lobo", "Grulla",
    # Árboles
    "Encina", "Roble", "Castaño", "Abedul", "Fresno", "Madroño", "Sauce", "Olmo", "Álamo", "Haya",
    "Tilo", "Pino",
]


# Crea el superadmin y los usuarios de ejemplo que falten. Se puede ejecutar varias veces: los que ya
# existen no se tocan. La contraseña se cifra una sola vez y se comparte (cifrar con Argon2 es lento a
# propósito). Se guardan todos con una sola consulta.
def crear():
    cifrada = make_password(CONTRASENA_DE_EJEMPLO)
    existentes = set(Usuario.objects.values_list("alias_normalizado", flat=True))
    nuevos = [
        Usuario(
            alias=alias,
            alias_normalizado=normalizar_alias(alias),
            password=cifrada,
            es_superadmin=alias == SUPERADMIN_DE_EJEMPLO,
        )
        for alias in [SUPERADMIN_DE_EJEMPLO, *ALIAS_DE_EJEMPLO]
        if normalizar_alias(alias) not in existentes
    ]
    Usuario.objects.bulk_create(nuevos)


# Borra el superadmin y los usuarios de ejemplo (y solo esos), dejando la base como estaba.
def borrar():
    normalizados = [normalizar_alias(alias) for alias in [SUPERADMIN_DE_EJEMPLO, *ALIAS_DE_EJEMPLO]]
    Usuario.objects.filter(alias_normalizado__in=normalizados).delete()
