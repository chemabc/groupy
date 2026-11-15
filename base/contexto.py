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
    menu = [entrada for entrada in menu if entrada.codigo not in ocultas]
    visibles = {entrada.codigo for entrada in menu}
    # Los bloques del menú con lo que puede ver; los que se quedan vacíos no se pintan.
    bloques = []
    for bloque, entradas in registro.bloques:
        suyas = [entrada for entrada in entradas if entrada.codigo in visibles]
        if suyas:
            bloques.append({"titulo": bloque.titulo, "tono": bloque.tono, "entradas": suyas})
    # Si la página es de una sección con pestañas (la más alta del camino que las tenga): la sección es la
    # madre, sus subsecciones son las pestañas de arriba y la elegida es la del camino. Si no, las pestañas
    # son las vistas de la sección, como siempre.
    madre, hija = _pestanas_del_camino(camino)
    if madre is not None:
        pestanas = [
            {"nombre": sub.nombre, "url": sub.url, "codigo": sub.codigo, "activa": sub.codigo == hija.codigo, "numero": contadores.get(sub.codigo)}
            for sub in madre.subsecciones if sub.codigo not in ocultas
        ]
        subvistas = [{"vista": vista, "activa": vista.url == ruta} for vista in hija.vistas] if len(hija.vistas) > 1 else []
        vistas_de_la_pagina = subvistas
        marcadas = camino[: camino.index(madre) + 1]
    else:
        pestanas = [{"nombre": vista.nombre, "url": vista.url, "codigo": "", "activa": vista.url == ruta, "numero": None} for vista in seccion.vistas] if seccion else []
        subvistas = []
        vistas_de_la_pagina = [{"vista": vista, "activa": vista.url == ruta} for vista in seccion.vistas] if seccion else []
        marcadas = camino
    vista_activa = next((elemento["vista"] for elemento in vistas_de_la_pagina if elemento["activa"]), None)
    nombre_de_la_seccion = (madre or seccion).nombre if seccion else ""
    ayuda = (registro.ayuda.get(seccion.codigo) or (registro.ayuda.get(madre.codigo) if madre else None)) if seccion else None
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
    partes = []
    for parte in (vista_activa.nombre if vista_activa else "", hija.nombre if madre is not None else "", nombre_de_la_seccion, NOMBRE_DE_LA_APLICACION):
        if parte and (not partes or partes[-1] != parte):
            partes.append(parte)
    return {
        "interfaz": {
            # Plantilla de la que heredan las páginas (ver arriba).
            "plantilla": plantilla,
            # Si se manda solo la zona central. Entonces la zona lleva también los contadores del menú,
            # para ponerlos al día sin volver a pintar el menú (ver base/zona.html).
            "solo_la_zona": solo_la_zona,
            # Secciones del menú que puede ver (las que piden un permiso, solo si lo tiene).
            "menu": menu,
            # Los mismos, por bloques: [{titulo, tono, entradas}] (ver base/disposicion.py).
            "bloques": bloques,
            # Banda de arriba si la sección es de un bloque con banda: {texto, tono}, o None.
            "banda": _banda(camino),
            # Códigos de las subsecciones que no puede ver (piden un permiso que no tiene).
            "ocultas": ocultas,
            # Número de cada entrada con contador: {código: número}.
            "contadores": contadores,
            "seccion": seccion,
            # Nombre que sale como título de la zona: el de la sección con pestañas, si la hay.
            "nombre_de_la_seccion": nombre_de_la_seccion,
            # Códigos de las entradas del camino que se ven en el menú izquierdo, para marcarlas (las que van
            # como pestañas no salen en él).
            "codigos": [entrada.codigo for entrada in marcadas],
            # Pestañas de arriba: [{nombre, url, codigo, activa, numero}] (las subsecciones de una sección
            # con pestañas, con su contador si lo tienen, o, si no, las vistas de la sección).
            "pestanas": pestanas,
            # Segunda fila, más pequeña: las vistas de la pestaña elegida, si tiene varias.
            "subvistas": subvistas,
            # Las vistas de la página (para el panel de ayuda, que pinta sus propias pestañas).
            "vistas": vistas_de_la_pagina,
            "ayuda": ayuda,
            # Subsecciones de la ayuda que puede ver, para el botón «?» rojo de la cabecera, que las abre
            # en el panel de la derecha. Lista vacía: no hay botón.
            "ayuda_lateral": _ayuda_lateral(menu, ocultas) if conectado else [],
            # Direcciones que se abren dentro del panel de ayuda al pulsarlas allí (las de la sección de
            # ayuda); las demás van a la zona principal. Es una función: solo se calcula si la plantilla
            # la usa (la página entera, no al navegar).
            "direcciones_de_la_ayuda": _direcciones_de_la_ayuda,
            "titulo": " · ".join(parte for parte in partes if parte),
            # Botones de la cabecera que declaran los módulos (EnlaceDeCabecera), con su número. Es una
            # función: solo se calcula si la plantilla la usa (la página entera, no al navegar).
            "cabecera": (lambda: _enlaces_de_cabecera(usuario)) if conectado else list,
            # Si hay alguien con la sesión iniciada, y su alias (arriba, en la cabecera).
            "conectado": conectado,
            "alias": usuario.get_username() if conectado else "",
            # Preferencias guardadas en su cuenta (tema, letra, densidad). La plantilla las pone en <html>
            # para que la página salga ya con ellas, sin destello. Las vacías no se ponen.
            "preferencias": {clave: getattr(usuario, clave, "") for clave in CLAVES} if conectado else {},
        }
    }


# Los botones de la cabecera de todos los módulos, listos para pintar: [{nombre, url, icono, titulo,
# numero}]. El número sale de su contador, que debe ser barato (normalmente, de la caché).
#   - usuario: quien tiene la sesión.
def _enlaces_de_cabecera(usuario):
    return [
        {
            "codigo": enlace.codigo, "nombre": enlace.nombre, "url": reverse(enlace.url), "icono": enlace.icono, "titulo": enlace.titulo,
            "numero": import_string(enlace.contador)(usuario) if enlace.contador else None,
        }
        for enlace in registro.enlaces_de_cabecera.values()
    ]


# Busca en el camino la sección más alta cuyas subsecciones van como pestañas y devuelve (madre, hija): la
# sección y la pestaña elegida (la siguiente del camino o, si la página es la de la propia madre, su
# primera subsección). Sin ninguna, (None, None).
#   - camino: las entradas desde la sección principal hasta la de la página.
def _pestanas_del_camino(camino):
    for posicion, entrada in enumerate(camino):
        if entrada.en_pestanas and entrada.subsecciones:
            hija = camino[posicion + 1] if posicion + 1 < len(camino) else entrada.subsecciones[0]
            return entrada, hija
    return None, None


# Banda de la zona central ({texto, tono}) si la sección principal del camino es de un bloque con banda;
# None si no.
#   - camino: las entradas desde la sección principal.
def _banda(camino):
    if not camino:
        return None
    for bloque, entradas in registro.bloques:
        if bloque.banda and any(entrada.codigo == camino[0].codigo for entrada in entradas):
            return {"texto": bloque.banda, "tono": bloque.tono}
    return None


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
#   Además: una entrada con subsecciones que tiene todas ocultas también se oculta (no habría nada que
#   ver), y una con pestañas lleva la suma de los números de sus pestañas (para verlo desde el menú).
def _recorrer_subsecciones(usuario, entrada, ocultas, contadores):
    if entrada.contador:
        contadores[entrada.codigo] = import_string(entrada.contador)(usuario)
    for subseccion in entrada.subsecciones:
        if puede_ver_entrada(usuario, subseccion):
            _recorrer_subsecciones(usuario, subseccion, ocultas, contadores)
        else:
            ocultas.add(subseccion.codigo)
    if entrada.subsecciones and all(subseccion.codigo in ocultas for subseccion in entrada.subsecciones):
        ocultas.add(entrada.codigo)
    if entrada.en_pestanas:
        numeros = [contadores[sub.codigo] for sub in entrada.subsecciones if sub.codigo in contadores and sub.codigo not in ocultas]
        if numeros:
            contadores[entrada.codigo] = sum(numeros)


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
