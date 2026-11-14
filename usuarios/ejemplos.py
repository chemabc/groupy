"""
Usuarios de ejemplo, para probar y medir las pantallas. Los crea y los borra la orden
«python manage.py ejemplos» (módulo «ejemplos»), que solo funciona en desarrollo.

Todos tienen la misma contraseña, que está escrita aquí: por eso nunca deben existir en el servidor
real. Cada cual puede cambiarla desde «Configuración de mi cuenta → Contraseña». Los alias son nombres de animales y de
árboles; varios llevan tilde o ñ, para probar que se puede entrar escribiéndolos sin ellas.

El superadmin de ejemplo se llama «superadmin». Se crea si no existe, pero borrar los datos de ejemplo
no lo toca (ni a él ni a su contraseña): así siempre se puede volver a entrar.
"""

from django.contrib.auth.hashers import make_password

from .models import Usuario, normalizar_alias

# Contraseña común de todos los usuarios de ejemplo.
CONTRASENA_DE_EJEMPLO = "M3n0sL3ctiv4s"

# Alias del superadmin de ejemplo (no lo borra borrar()).
SUPERADMIN_DE_EJEMPLO = "superadmin"

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


# Borra los usuarios de ejemplo (y solo esos), dejando la base como estaba. El superadmin no se toca.
def borrar():
    usuarios_de_ejemplo().delete()


# Los usuarios de ejemplo (sin el superadmin), como consulta. La usan este borrar() y el de los módulos de
# encima (calendario, proyectos), que antes quitan lo que esas personas hayan creado al probar.
def usuarios_de_ejemplo():
    normalizados = [normalizar_alias(alias) for alias in ALIAS_DE_EJEMPLO]
    return Usuario.objects.filter(alias_normalizado__in=normalizados)
