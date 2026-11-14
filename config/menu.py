"""
Disposición del menú izquierdo: el único sitio donde se decide en qué orden sale cada entrada y dentro de
qué sección va (ver docs/diseno.md, apartado 4, «Disposición del menú»).

Cada módulo declara en su contrato (apps.py) las entradas que aporta: nombre, dirección, icono, color,
permiso, vistas… Aquí solo se colocan, por su código. Para reordenar el menú se mueve una línea; para
llevar una subsección a otra sección se mueve dentro de los paréntesis de esa sección.

Cómo se escribe cada elemento:
  - «"usuarios.cuenta"»: una entrada sin subsecciones.
  - «("ayuda.ayuda", ("ayuda.como_se_hace", …))»: una entrada con sus subsecciones, en este orden (y
    cada una puede tener las suyas, igual, a cualquier profundidad).

Al arrancar (y con «python manage.py check»), el registro avisa si una entrada declarada no está aquí,
si aquí se nombra una que nadie declara o si una sale dos veces. Lo lee base/apps.py a través del ajuste
DISPOSICION_DEL_MENU de config/settings.py.

Quién ve cada entrada no se decide aquí, sino en su contrato (permiso): una sección cuyas subsecciones
están todas ocultas tampoco se muestra.
"""

DISPOSICION = (
    "base.inicio",
    ("comunicaciones.comunicaciones", (
        "comunicaciones.notificaciones",
        "comunicaciones.conversaciones",
        "comunicaciones.avisos",
        "comunicaciones.preferencias",
    )),
    ("proyectos.seccion", (
        "proyectos.proyectos",
        "proyectos.tareas",
    )),
    ("eventos.eventos", (
        "eventos.lista",
        "eventos.mios",
    )),
    ("calendario.calendario", (
        "calendario.ver",
        "calendario.recordatorios",
        "calendario.suscripcion",
    )),
    ("solicitudes.solicitudes", (
        "solicitudes.pendientes",
        "solicitudes.pasadas",
        "solicitudes.mias",
    )),
    ("limpieza.archivo", (
        "limpieza.archivados",
        "limpieza.borrados",
    )),
    ("grupos.organizaciones", (
        "grupos.mis_grupos",
        "grupos.arbol",
        "grupos.relaciones",
        "grupos.invitaciones",
    )),
    ("lugares.lugares", (
        "lugares.mi_lugar",
        "lugares.mapa",
        "lugares.gestion",
    )),
    ("talentos.talentos", (
        "talentos.mios",
        "talentos.peticiones",
        "talentos.del_grupo",
        "talentos.catalogo",
    )),
    ("administracion.usuarios", (
        "administracion.boveda",
        "administracion.alias",
        "administracion.roles",
    )),
    ("tipologias.configuracion", (
        "tipologias.tipologias",
        "audiencias.visibilidad",
        "etiquetas.etiquetas",
        "comunicaciones.niveles",
        "solicitudes.ajustes",
        "lugares.configuracion",
        "limpieza.plazos",
    )),
    # Las tres últimas, a petición de la persona usuaria (14 de noviembre de 2026): «Ayuda» siempre antes
    # que «Configuración de mi cuenta», y «Desarrollo y mantenimiento» (solo superadmin) al final.
    ("ayuda.ayuda", (
        "ayuda.como_se_hace",
        "ayuda.plataforma",
        "ayuda.guias",
    )),
    "usuarios.cuenta",
    ("mantenimiento.desarrollo", (
        "mantenimiento.pruebas",
        "mantenimiento.trastienda",
    )),
)
