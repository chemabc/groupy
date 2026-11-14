"""
Disposición de la portada, «Inicio»: el único sitio donde se decide qué recuadros (tarjetas) salen en
cada pantalla, en qué fila y en qué orden (ver docs/diseno.md, apartado 4, «Inicio»).

Cada módulo declara en su contrato (apps.py, «tarjetas_de_inicio») las tarjetas que aporta y la función
que hace su resumen. Aquí solo se colocan, por su código. Para cambiar el orden se mueve un código; para
pasar una tarjeta a otra fila, se mueve a otros paréntesis.

Cómo se escribe: un diccionario con una clave por pantalla («panel» y «mis_datos»); cada pantalla es una
lista de filas, y cada fila, una lista de códigos de tarjeta, de izquierda a derecha.

«python manage.py check» avisa si una tarjeta declarada no está aquí, si aquí se nombra una que nadie
declara o si una sale dos veces (base/comprobaciones.py). Lo lee base/inicio.py a través del ajuste
DISPOSICION_DEL_INICIO de config/settings.py.

Una tarjeta cuya función devuelve None (por ejemplo, porque a esa persona no le toca) no sale, y una fila
vacía tampoco.
"""

DISPOSICION = {
    # «Inicio → Panel»: lo pendiente y lo que está en marcha.
    "panel": (
        ("comunicaciones.pendientes", "solicitudes.pendientes"),
        ("proyectos.abiertos",),
    ),
    # «Inicio → Mis datos»: un resumen de la cuenta, con un botón «Editar» en cada recuadro.
    "mis_datos": (
        ("usuarios.datos_publicos",),
        ("talentos.mios",),
        ("usuarios.datos_privados", "lugares.mi_lugar"),
        ("grupos.mis_grupos",),
    ),
}
