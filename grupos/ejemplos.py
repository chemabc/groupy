"""
Organizaciones y grupos de ejemplo. Las organizaciones son ríos ibéricos («ORG Tajo») y sus grupos, sus
afluentes («GRU Jarama»). Los subgrupos son afluentes de los afluentes (el Henares desemboca en el
Jarama), así que el árbol de grupos sigue al de los ríos.

Los crea y borra la orden «python manage.py ejemplos» (módulo «ejemplos»), después de los usuarios de
ejemplo (usuarios/ejemplos.py), que reparte por los grupos.
"""

from django.contrib.auth import get_user_model

from .models import AdminDeOrganizacion, Grupo, Organizacion, Pertenencia
from .servicios import crear_grupo, crear_organizacion

# Árbol de ejemplo: organización → [(grupo, [subgrupos])].
ESTRUCTURA = {
    "ORG Tajo": [
        ("GRU Jarama", ["GRU Henares", "GRU Manzanares", "GRU Lozoya"]),
        ("GRU Alberche", []),
        ("GRU Tiétar", []),
        ("GRU Alagón", []),
    ],
    "ORG Ebro": [
        ("GRU Aragón", ["GRU Arga"]),
        ("GRU Segre", ["GRU Cinca"]),
        ("GRU Jalón", []),
        ("GRU Gállego", []),
    ],
    "ORG Duero": [
        ("GRU Pisuerga", ["GRU Carrión", "GRU Arlanza"]),
        ("GRU Adaja", ["GRU Eresma"]),
        ("GRU Esla", []),
        ("GRU Tormes", []),
    ],
    "ORG Guadalquivir": [
        ("GRU Genil", ["GRU Darro"]),
        ("GRU Guadalimar", []),
        ("GRU Guadiana Menor", []),
    ],
}

# Asamblea base de cada usuario de ejemplo y si es admin de ella. El superadmin (Águila) no está en
# ningún grupo: lo ve todo por ser superadmin.
ASAMBLEAS_BASE = [
    # ORG Tajo
    ("Lince", "GRU Henares", Pertenencia.ADMIN_GRUPO),
    ("Nutria", "GRU Henares", Pertenencia.USUARIO),
    ("Tejón", "GRU Manzanares", Pertenencia.ADMIN_GRUPO),
    ("Garza", "GRU Lozoya", Pertenencia.USUARIO),
    ("Búho", "GRU Alberche", Pertenencia.ADMIN_GRUPO),
    ("Ardilla", "GRU Tiétar", Pertenencia.USUARIO),
    # ORG Ebro
    ("Zorro", "GRU Arga", Pertenencia.ADMIN_GRUPO),
    ("Cigüeña", "GRU Arga", Pertenencia.USUARIO),
    ("Erizo", "GRU Cinca", Pertenencia.ADMIN_GRUPO),
    ("Jabalí", "GRU Jalón", Pertenencia.USUARIO),
    ("Lobo", "GRU Gállego", Pertenencia.USUARIO),
    ("Grulla", "GRU Aragón", Pertenencia.ADMIN_GRUPO),
    # ORG Duero
    ("Encina", "GRU Carrión", Pertenencia.ADMIN_GRUPO),
    ("Roble", "GRU Carrión", Pertenencia.USUARIO),
    ("Castaño", "GRU Arlanza", Pertenencia.USUARIO),
    ("Abedul", "GRU Esla", Pertenencia.ADMIN_GRUPO),
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
        principales = ESTRUCTURA[nombre]
        organizacion, primero = crear_organizacion(nombre, principales[0][0])
        for nombre_del_grupo, subgrupos in principales:
            grupo = primero if nombre_del_grupo == primero.nombre else crear_grupo(organizacion, nombre_del_grupo)
            grupos[nombre_del_grupo] = grupo
            for nombre_del_subgrupo in subgrupos:
                grupos[nombre_del_subgrupo] = crear_grupo(organizacion, nombre_del_subgrupo, padre=grupo)
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
