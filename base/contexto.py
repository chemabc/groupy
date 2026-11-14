"""
Datos comunes que reciben todas las plantillas («procesador de contexto» de Django).

Django llama a interfaz() en cada página que se pinta (está en TEMPLATES, en config/settings.py) y
añade lo que devuelve a los datos de la plantilla. Aquí se decide todo lo que la plantilla general solo
tiene que pintar: el menú, la sección y la vista en las que se está, su ayuda y si se manda la página
entera, solo la zona central o una página para el panel de ayuda de la derecha. No hace ninguna consulta propia: el menú sale del registro, que está en
memoria, y el alias y las preferencias, del usuario que Django ya ha cargado para la petición.
"""

from django.urls import reverse
from django.utils.module_loading import import_string

from .preferencias import CLAVES
from .registro import puede_ver_entrada, registro

# Nombre de la aplicación, para el título de la pestaña del navegador.
NOMBRE_DE_LA_APLICACION = "Asambleas"


# Devuelve los datos de la interfaz para la plantilla, todos dentro de «interfaz».
#   - request: la petición web que se está respondiendo.
def interfaz(request):
    # Nombre de la ruta que ha atendido la petición, como «base:inicio». Vacío si no hay ninguna (un 404).
    ruta = request.resolver_match.view_name if request.resolver_match else ""
    # Camino del menú hasta la sección actual (sección principal, subsección…). Vacío si la página no
    # está en el menú.
    camino = registro.rutas.get(ruta, ())
    seccion = camino[-1] if camino else None
    vistas = [{"vista": vista, "activa": vista.url == ruta} for vista in seccion.vistas] if seccion else []
    vista_activa = next((elemento["vista"] for elemento in vistas if elemento["activa"]), None)
    # Quien ha iniciado sesión. Se usa el usuario de Django sin importar el módulo «usuarios» (que está en
    # una capa superior): basta con su alias (get_username) y sus preferencias.
    usuario = getattr(request, "user", None)
    conectado = usuario is not None and usuario.is_authenticated
    # Secciones principales que puede ver, y qué subsecciones hay que ocultarle y qué números lleva cada
    # entrada con contador.
    menu = [entrada for entrada in registro.menu if puede_ver_entrada(usuario, entrada)] if conectado else []
    ocultas, contadores = set(), {}
    for entrada in menu:
        _recorrer_subsecciones(usuario, entrada, ocultas, contadores)
    # Una sección cuyas subsecciones están todas ocultas tampoco se muestra (no habría nada que ver).
    menu = [
        entrada for entrada in menu
        if not entrada.subsecciones or any(sub.codigo not in ocultas for sub in entrada.subsecciones)
    ]
    solo_la_zona = pide_solo_la_zona(request)
    en_el_panel = pide_el_panel(request)
    # Plantilla de la que heredan las páginas: la página entera, solo la zona central (navegación con htmx)
    # o la página dentro del panel de ayuda.
    if en_el_panel:
        plantilla = "base/panel.html"
    elif solo_la_zona:
        plantilla = "base/zona.html"
    else:
        plantilla = "base/pagina.html"
    # Título de la pestaña: «Vista · Sección · Asambleas», con lo que haya.
    partes = [vista_activa.nombre if vista_activa else "", seccion.nombre if seccion else "", NOMBRE_DE_LA_APLICACION]
    return {
        "interfaz": {
            # Plantilla de la que heredan las páginas (ver arriba).
            "plantilla": plantilla,
            # Si se manda solo la zona central. Entonces la zona lleva también los contadores del menú,
            # para ponerlos al día sin volver a pintar el menú (ver base/zona.html).
            "solo_la_zona": solo_la_zona,
            # Secciones del menú que puede ver (las que piden un permiso, solo si lo tiene).
            "menu": menu,
            # Códigos de las subsecciones que no puede ver (piden un permiso que no tiene).
            "ocultas": ocultas,
            # Número de cada entrada con contador: {código: número}.
            "contadores": contadores,
            "seccion": seccion,
            # Códigos de las entradas del camino, para marcarlas en el menú.
            "codigos": [entrada.codigo for entrada in camino],
            "vistas": vistas,
            "ayuda": registro.ayuda.get(seccion.codigo) if seccion else None,
            # Subsecciones de la ayuda que puede ver, para el botón «?» rojo de la cabecera, que las abre
            # en el panel de la derecha. Lista vacía: no hay botón.
            "ayuda_lateral": _ayuda_lateral(menu, ocultas) if conectado else [],
            # Direcciones que se abren dentro del panel de ayuda al pulsarlas allí (las de la sección de
            # ayuda); las demás van a la zona principal. Es una función: solo se calcula si la plantilla
            # la usa (la página entera, no al navegar).
            "direcciones_de_la_ayuda": _direcciones_de_la_ayuda,
            "titulo": " · ".join(parte for parte in partes if parte),
            # Si hay alguien con la sesión iniciada, y su alias (arriba, en la cabecera).
            "conectado": conectado,
            "alias": usuario.get_username() if conectado else "",
            # Preferencias guardadas en su cuenta (tema, letra, densidad). La plantilla las pone en <html>
            # para que la página salga ya con ellas, sin destello. Las vacías no se ponen.
            "preferencias": {clave: getattr(usuario, clave, "") for clave in CLAVES} if conectado else {},
        }
    }


# Devuelve las subsecciones de la entrada de la ayuda (registro.entrada_de_ayuda) que la persona puede
# ver, o una lista vacía si no puede ver la propia entrada. La usa interfaz() para el botón «?» rojo.
#   - menu: las secciones principales que puede ver.
#   - ocultas: códigos de las subsecciones que no puede ver (ya calculados).
def _ayuda_lateral(menu, ocultas):
    entrada = registro.entrada_de_ayuda
    if entrada is None or not _a_la_vista(menu, ocultas, entrada.codigo):
        return []
    return [subseccion for subseccion in entrada.subsecciones if subseccion.codigo not in ocultas]


# Dice si una entrada está en el menú que ve la persona (en las secciones principales visibles o en
# alguna subsección no oculta, a cualquier profundidad). La usa _ayuda_lateral.
#   - entradas: las entradas por las que se busca.
#   - ocultas: códigos de las subsecciones que no puede ver.
#   - codigo: el código buscado.
def _a_la_vista(entradas, ocultas, codigo):
    for entrada in entradas:
        if entrada.codigo in ocultas:
            continue
        if entrada.codigo == codigo or _a_la_vista(entrada.subsecciones, ocultas, codigo):
            return True
    return False


# Devuelve, separadas por espacios, las direcciones de la sección de ayuda (la de cada subsección y las
# de sus pestañas), como «/ayuda/como-se-hace/ /ayuda/tutorial/ …». El panel de ayuda las usa para saber
# qué enlaces abrir dentro de él (ver panelDeAyuda en interfaz.js).
def _direcciones_de_la_ayuda():
    entrada = registro.entrada_de_ayuda
    if entrada is None:
        return ""
    rutas = {entrada.url}
    pendientes = [entrada]
    while pendientes:
        actual = pendientes.pop()
        rutas.update([actual.url, *(vista.url for vista in actual.vistas)])
        pendientes.extend(actual.subsecciones)
    return " ".join(sorted(reverse(ruta) for ruta in rutas))


# Recorre una entrada del menú y sus subsecciones: apunta en «ocultas» las subsecciones que la persona
# no puede ver (y ya no baja por ellas) y en «contadores» el número de las que lo llevan. Lo usa interfaz().
#   - usuario: quien mira.
#   - entrada: la EntradaDeMenu (ya se sabe que la puede ver).
#   - ocultas: conjunto que se va rellenando con códigos.
#   - contadores: diccionario que se va rellenando con {código: número}.
def _recorrer_subsecciones(usuario, entrada, ocultas, contadores):
    if entrada.contador:
        contadores[entrada.codigo] = import_string(entrada.contador)(usuario)
    for subseccion in entrada.subsecciones:
        if puede_ver_entrada(usuario, subseccion):
            _recorrer_subsecciones(usuario, subseccion, ocultas, contadores)
        else:
            ocultas.add(subseccion.codigo)


# Dice si la petición la ha hecho la navegación con htmx del menú y, por tanto, basta con mandar la zona
# central. htmx lo indica con sus cabeceras:
#   - HX-Request: la petición la hace htmx.
#   - HX-Target: el elemento que se va a sustituir; la navegación sustituye el de id «zona».
#   - HX-History-Restore-Request: htmx pide la página para el botón «atrás»; entonces hace falta entera.
def pide_solo_la_zona(request):
    cabeceras = request.headers
    return (
        cabeceras.get("HX-Request") == "true"
        and cabeceras.get("HX-Target") == "zona"
        and "HX-History-Restore-Request" not in cabeceras
    )


# Identificador del elemento del panel de ayuda (en base/pagina.html) donde se ponen las páginas que se
# abren en él. htmx lo manda en la cabecera HX-Target al pedirlas.
DESTINO_DEL_PANEL = "panel-de-ayuda-contenido"


# Dice si la petición es para el panel de ayuda de la derecha: entonces la página se pinta sin cabecera
# de sección ni menús, con base/panel.html. La hace el componente panelDeAyuda de interfaz.js con htmx,
# que manda HX-Target con el identificador del panel.
def pide_el_panel(request):
    cabeceras = request.headers
    return cabeceras.get("HX-Request") == "true" and cabeceras.get("HX-Target") == DESTINO_DEL_PANEL
