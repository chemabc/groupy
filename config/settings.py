"""
Ajustes generales del proyecto.

Django lee este fichero al arrancar. Aquí se dice qué módulos (apps) forman la aplicación, a qué bases
de datos se conecta, cómo se guardan las contraseñas, el idioma, etc. Los datos que cambian entre el
ordenador de desarrollo y el servidor real (contraseñas, direcciones) se leen de variables de entorno,
que en desarrollo define .devcontainer/docker-compose.yml.

Decisiones de rendimiento que se aplican desde el primer día (ver docs/diseno.md, apartado 3.6):
JIT de PostgreSQL apagado, conexiones persistentes y caché en Redis.
"""

import os
import sys
from pathlib import Path

import dj_database_url

# Carpeta raíz del proyecto (la que contiene manage.py). Sirve para construir otras rutas.
BASE_DIR = Path(__file__).resolve().parent.parent

# Clave secreta con la que Django firma las sesiones y los formularios. En producción debe venir de una
# variable de entorno; el valor de respaldo solo vale para desarrollo.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "solo-para-desarrollo-cambiar-en-produccion")

# Modo de desarrollo: muestra los errores con detalle. Nunca encendido en producción.
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

# Si se están pasando las pruebas («python manage.py test»). Algunas cosas cambian entonces: no se
# carga la barra de depuración y la caché va en memoria.
PROBANDO = sys.argv[1:2] == ["test"]

# Si se muestra la barra de depuración (django-debug-toolbar): en desarrollo sí, en las pruebas no.
USAR_BARRA_DE_DEPURACION = DEBUG and not PROBANDO

# Nombres de servidor desde los que se acepta la aplicación.
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")

# Nombres propios para las cookies de la sesión y de la protección CSRF. Los navegadores reparten las
# cookies por nombre de servidor (localhost), no por puerto, así que con los nombres de Django por
# defecto («sessionid», «csrftoken») la versión 2 recibiría las cookies de la versión 1: intentaría leer
# una sesión ajena y, al iniciar sesión en una versión, se cerraría la de la otra.
SESSION_COOKIE_NAME = "asambleas2_sesion"
CSRF_COOKIE_NAME = "asambleas2_csrf"

# Módulos que forman la aplicación: primero los de Django y después los del proyecto, que se irán
# añadiendo fase a fase, en el orden de docs/diseno.md, apartado 19.
# Los del proyecto se escriben con la ruta completa de su configuración («base.apps.BaseConfig»): como
# en su apps.py también está importada ModuloConfig, Django no sabría cuál de las dos clases elegir.
INSTALLED_APPS = [
    # El panel de Django (la trastienda), con las secciones ordenadas y explicadas (config/trastienda.py).
    "config.apps.TrastiendaConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Funciones propias de PostgreSQL; aquí, la búsqueda sin tildes (unaccent) de las tablas filtrables.
    "django.contrib.postgres",
    # Capa base
    "base.apps.BaseConfig",
    "eventos_sw.apps.EventosSwConfig",
    "ejemplos.apps.EjemplosConfig",
    # Capa de identidad
    "boveda.apps.BovedaConfig",
    "usuarios.apps.UsuariosConfig",
    # Capa de organización
    "grupos.apps.GruposConfig",
    "permisos.apps.PermisosConfig",
    "audiencias.apps.AudienciasConfig",
    # Capa funcional
    "mantenimiento.apps.MantenimientoConfig",
    "administracion.apps.AdministracionConfig",
]

# Modelo de usuario de la aplicación: la cuenta con seudónimo (alias), en lugar del usuario de Django,
# que trae nombre, apellidos y correo. Django exige fijarlo antes de crear las tablas por primera vez.
AUTH_USER_MODEL = "usuarios.Usuario"

# Páginas de entrada y salida: adónde se manda a quien no ha iniciado sesión, adónde va al entrar y
# adónde al salir. Son nombres de rutas (ver usuarios/urls.py y base/urls.py).
LOGIN_URL = "usuarios:entrar"
LOGIN_REDIRECT_URL = "base:inicio"
LOGOUT_REDIRECT_URL = "usuarios:entrar"

# Dónde se guardan las sesiones: en la caché (Redis) y, por si se vacía, también en la base de datos.
# Leer la sesión en cada petición no cuesta así ninguna consulta (premisa de rapidez).
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# Capas por las que pasa cada petición web antes y después de llegar a la vista (seguridad, sesión,
# usuario que ha iniciado sesión, mensajes…).
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Nada se ve sin iniciar sesión, salvo la pantalla de entrada (ver usuarios/middleware.py).
    "usuarios.middleware.EntradaObligatoria",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Avisa al navegador de que una misma dirección puede devolver la página entera o solo su zona
    # central (navegación con htmx). Ver base/middleware.py.
    "base.middleware.VariarSegunHtmx",
]

# Barra de depuración, solo en desarrollo: se añade su app y su capa, la primera de la lista para que
# mida todo lo que hacen las demás.
if USAR_BARRA_DE_DEPURACION:
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    DEBUG_TOOLBAR_CONFIG = {
        # Normalmente la barra solo sale si el navegador llega desde 127.0.0.1. Desde el contenedor,
        # tu navegador llega desde otra dirección (la de la red de Docker), así que se muestra siempre
        # que esté activada.
        "SHOW_TOOLBAR_CALLBACK": lambda peticion: True,
    }

# Fichero con la lista de direcciones web de la aplicación.
ROOT_URLCONF = "config.urls"

# Dónde busca Django las plantillas HTML: en la carpeta común «plantillas» y dentro de cada app.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "plantillas"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Menú, sección actual, ayuda y plantilla de la interfaz (ver base/contexto.py).
                "base.contexto.interfaz",
            ],
        },
    },
]

# Cómo se pintan los formularios: cada campo con su etiqueta, su botón «copiar», su explicación y sus
# errores (ver base/formularios.py).
FORM_RENDERER = "base.formularios.Renderizador"

# Programa que sirve la aplicación en un servidor web clásico.
WSGI_APPLICATION = "config.wsgi.application"


# Prepara la configuración de una base de datos a partir de su dirección y le aplica las decisiones de
# rendimiento comunes. Se usa justo debajo, para la base de la plataforma y la de la bóveda.
def base_de_datos(direccion):
    configuracion = dj_database_url.parse(
        direccion,
        # Mantiene abierta la conexión 60 segundos para reutilizarla en las siguientes peticiones.
        conn_max_age=60,
        # Antes de reutilizar una conexión, comprueba que sigue viva.
        conn_health_checks=True,
    )
    # Apaga el JIT de PostgreSQL: en la versión 1 gastaba 370 de 440 ms compilando consultas pequeñas.
    configuracion.setdefault("OPTIONS", {})["options"] = "-c jit=off"
    return configuracion


# Las dos bases de datos, sin ninguna columna que las una (ver docs/registro-y-validacion.md):
#   - default: la plataforma (usuarios, grupos, eventos, proyectos…)
#   - boveda: la identidad real. El enrutador que manda allí solo las tablas de la bóveda llegará con
#     la app «boveda» (fase 1); hasta entonces nadie escribe en ella.
DATABASES = {
    "default": base_de_datos(
        os.environ.get("DATABASE_URL", "postgres://asambleas:asambleas@db:5432/asambleas")
    ),
    "boveda": base_de_datos(
        os.environ.get("BOVEDA_DATABASE_URL", "postgres://boveda:boveda@db:5432/boveda")
    ),
}

# Quién decide en qué base va cada tabla: las de la bóveda, en la suya; las demás, en la de la plataforma
# (ver config/enrutador.py).
DATABASE_ROUTERS = ["config.enrutador.EnrutadorDeLaBoveda"]

# Clave secreta con la que la bóveda calcula las huellas (del correo, del DNI). Va fuera de las bases de
# datos, en una variable de entorno: sin ella, una huella no sirve para nada. El valor de respaldo solo
# vale para desarrollo.
BOVEDA_CLAVE_HMAC = os.environ.get("BOVEDA_CLAVE_HMAC", "solo-para-desarrollo-cambiar-en-produccion")

# Tipo de número que usan por defecto las claves primarias de las tablas.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Caché en Redis: guarda los cálculos por persona (permisos, audiencias) para no repetirlos.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    }
}

# En las pruebas, la caché va en la memoria del propio proceso: cada ejecución empieza limpia y no
# mezcla datos con el Redis de desarrollo.
if PROBANDO:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Cómo se guardan las contraseñas: primero Argon2 (el recomendado); los demás, por compatibilidad.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# En las pruebas, un cifrado de contraseñas rápido (y nada seguro): Argon2 es lento a propósito y
# multiplicaría el tiempo de las pruebas que crean usuarios (ver docs/diseno.md, apartado 3.6).
if PROBANDO:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Reglas mínimas para las contraseñas nuevas: que no se parezcan al alias, longitud mínima, que no
# sean de las más comunes y que no sean solo números.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Idioma y zona horaria: castellano y hora de Madrid. USE_TZ guarda las horas en UTC por dentro.
LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

# Ficheros estáticos (CSS, JavaScript, imágenes): dirección pública y carpeta donde se reúnen para
# publicarlos en producción.
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Carpetas comunes de ficheros estáticos, además de las «static/» de cada módulo. En static/generado/
# deja «npm run construir» el CSS de Tailwind, htmx y Alpine.
STATICFILES_DIRS = [BASE_DIR / "static"]
