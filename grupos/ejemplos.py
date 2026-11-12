"""
Organizaciones y grupos de ejemplo. Las organizaciones son ríos ibéricos («ORG Tajo»). Su grupo general
es el propio río («GRU Tajo») y los grupos que contiene son sus afluentes, y los afluentes de estos, a
varios niveles: general (GRU Tajo) → zona (GRU Jarama) → centro (GRU Henares) → … (GRU Sorbe). Así el
árbol de grupos sigue al de los ríos (el Sorbe desemboca en el Henares, este en el Jarama y este en el
Tajo).

Los crea y borra la orden «python manage.py ejemplos» (módulo «ejemplos»), después de los usuarios de
ejemplo (usuarios/ejemplos.py), que reparte por los grupos.
"""

from django.contrib.auth import get_user_model

from .models import AdminDeOrganizacion, Grupo, Organizacion, Pertenencia
from .servicios import crear_grupo, crear_organizacion

# Árbol de ejemplo: cada organización con su grupo general, y cada grupo como (nombre, [subgrupos]).
ESTRUCTURA = {
    "ORG Tajo": (
        "GRU Tajo",
        [
            ("GRU Jarama", [
                ("GRU Henares", [("GRU Sorbe", []), ("GRU Badiel", [])]),
                ("GRU Manzanares", []),
                ("GRU Lozoya", []),
            ]),
            ("GRU Alberche", []),
            ("GRU Tiétar", []),
            ("GRU Alagón", []),
        ],
    ),
    "ORG Ebro": (
        "GRU Ebro",
        [
            ("GRU Aragón", [("GRU Arga", [])]),
            ("GRU Segre", [("GRU Cinca", [("GRU Ésera", [("GRU Isábena", [])])])]),
            ("GRU Jalón", []),
            ("GRU Gállego", []),
        ],
    ),
    "ORG Duero": (
        "GRU Duero",
        [
            ("GRU Pisuerga", [("GRU Carrión", []), ("GRU Arlanza", [("GRU Arlanzón", [])])]),
            ("GRU Adaja", [("GRU Eresma", [])]),
            ("GRU Esla", [("GRU Órbigo", [("GRU Tuerto", [])])]),
            ("GRU Tormes", []),
        ],
    ),
    "ORG Guadalquivir": (
        "GRU Guadalquivir",
        [
            ("GRU Genil", [("GRU Darro", [])]),
            ("GRU Guadalimar", []),
            ("GRU Guadiana Menor", []),
        ],
    ),
}

# Asamblea base de cada usuario de ejemplo y si es admin de ella. El superadmin (Águila) no está en
# ningún grupo: lo ve todo por ser superadmin.
ASAMBLEAS_BASE = [
    # ORG Tajo
    ("Lince", "GRU Henares", Pertenencia.ADMIN_GRUPO),
    ("Nutria", "GRU Henares", Pertenencia.USUARIO),
    ("Tejón", "GRU Manzanares", Pertenencia.ADMIN_GRUPO),
    ("Garza", "GRU Sorbe", Pertenencia.USUARIO),
    ("Búho", "GRU Alberche", Pertenencia.ADMIN_GRUPO),
    ("Ardilla", "GRU Tiétar", Pertenencia.USUARIO),
    # ORG Ebro
    ("Zorro", "GRU Arga", Pertenencia.ADMIN_GRUPO),
    ("Cigüeña", "GRU Arga", Pertenencia.USUARIO),
    ("Erizo", "GRU Ésera", Pertenencia.ADMIN_GRUPO),
    ("Jabalí", "GRU Jalón", Pertenencia.USUARIO),
    ("Lobo", "GRU Gállego", Pertenencia.USUARIO),
    ("Grulla", "GRU Aragón", Pertenencia.ADMIN_GRUPO),
    # ORG Duero
    ("Encina", "GRU Carrión", Pertenencia.ADMIN_GRUPO),
    ("Roble", "GRU Carrión", Pertenencia.USUARIO),
    ("Castaño", "GRU Arlanzón", Pertenencia.USUARIO),
    ("Abedul", "GRU Órbigo", Pertenencia.ADMIN_GRUPO),
    ("Fresno", "GRU Tormes", Pertenencia.USUARIO),
    ("Madroño", "GRU Eresma", Pertenencia.USUARIO),
    # ORG Guadalquivir
    ("Sauce", "GRU Darro", Pertenencia.ADMIN_GRUPO),
    ("Olmo", "GRU Darro", Pertenencia.USUARIO),
    ("Álamo", "GRU Genil", Pertenencia.USUARIO),
    ("Haya", "GRU Guadalimar", Pertenencia.ADMIN_GRUPO),
    ("Tilo", "GRU Guadiana Menor", Pertenencia.USUARIO),
    ("Pino", "GRU Guadiana Menor", Pertenencia.USUARIO),
]

# Pertenencias de más (no son su asamblea base): personas que están también en otro grupo, incluso de
# otra organización.
OTRAS_PERTENENCIAS = [
    ("Lince", "GRU Segre"),
    ("Encina", "GRU Jarama"),
    ("Nutria", "GRU Lozoya"),
    ("Búho", "GRU Tajo"),
]

# Admin de cada organización.
ADMINS_DE_ORGANIZACION = [
    ("Lince", "ORG Tajo"),
    ("Zorro", "ORG Ebro"),
    ("Encina", "ORG Duero"),
    ("Sauce", "ORG Guadalquivir"),
]


# Crea las organizaciones, grupos, pertenencias y admins de ejemplo que falten. Una organización que ya
# existe no se toca. Los grupos se crean con los servicios (para que se rellene la tabla de cierre); las
# pertenencias, todas de una vez (bulk_create), sin avisos: nadie tiene nada calculado todavía.
def crear():
    nuevas = [nombre for nombre in ESTRUCTURA if not Organizacion.objects.filter(nombre=nombre).exists()]
    grupos = {}
    for nombre in nuevas:
        general, subgrupos = ESTRUCTURA[nombre]
        organizacion, grupo_general = crear_organizacion(nombre, general)
        grupos[general] = grupo_general
        _crear_subgrupos(organizacion, grupo_general, subgrupos, grupos)
    usuarios = {usuario.alias: usuario for usuario in get_user_model().objects.all()}
    Pertenencia.objects.bulk_create(
        [
            Pertenencia(usuario=usuarios[alias], grupo=grupos[grupo], rol=rol, es_base=True)
            for alias, grupo, rol in ASAMBLEAS_BASE
            if grupo in grupos and alias in usuarios
        ]
        + [
            Pertenencia(usuario=usuarios[alias], grupo=grupos[grupo])
            for alias, grupo in OTRAS_PERTENENCIAS
            if grupo in grupos and alias in usuarios
        ]
    )
    AdminDeOrganizacion.objects.bulk_create(
        AdminDeOrganizacion(usuario=usuarios[alias], organizacion=_organizacion_llamada(nombre, grupos))
        for alias, nombre in ADMINS_DE_ORGANIZACION
        if nombre in nuevas and alias in usuarios
    )


# Crea los subgrupos de un grupo y, dentro de cada uno, los suyos, a cualquier profundidad (se llama a
# sí misma para cada nivel). Apunta cada grupo creado en «grupos», por su nombre.
#   - organizacion: la organización de todos ellos.
#   - padre: el grupo que los contiene.
#   - subgrupos: lista de (nombre, [subgrupos]).
#   - grupos: diccionario de nombre a grupo, que se va rellenando.
def _crear_subgrupos(organizacion, padre, subgrupos, grupos):
    for nombre, debajo in subgrupos:
        grupos[nombre] = crear_grupo(organizacion, nombre, padre=padre)
        _crear_subgrupos(organizacion, grupos[nombre], debajo, grupos)


# Devuelve la organización llamada «nombre» a partir de cualquiera de sus grupos recién creados. La usa
# crear() para no volver a buscarla en la base.
def _organizacion_llamada(nombre, grupos):
    return next(grupo.organizacion for grupo in grupos.values() if grupo.organizacion.nombre == nombre)


# Borra las organizaciones de ejemplo con todo lo suyo (grupos, pertenencias, admins…). Los grupos se
# protegen entre sí (un grupo con subgrupos no se puede borrar), así que primero se sueltan de su padre
# y después se borran todos juntos.
def borrar():
    organizaciones = Organizacion.objects.filter(nombre__in=list(ESTRUCTURA))
    grupos = Grupo.objects.filter(organizacion__in=organizaciones)
    grupos.update(padre=None)
    grupos.delete()
    organizaciones.delete()
