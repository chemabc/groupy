"""
Datos comunes que reciben todas las plantillas («procesador de contexto» de Django).

Django llama a interfaz() en cada página que se pinta (está en TEMPLATES, en config/settings.py) y
añade lo que devuelve a los datos de la plantilla. Aquí se decide todo lo que la plantilla general solo
tiene que pintar: el menú, la sección y la vista en las que se está, su ayuda y si se manda la página
entera o solo la zona central. No hace ninguna consulta a la base de datos: todo sale del registro,
que está en memoria.
"""

from .registro import registro

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
    # Título de la pestaña: «Vista · Sección · Asambleas», con lo que haya.
    partes = [vista_activa.nombre if vista_activa else "", seccion.nombre if seccion else "", NOMBRE_DE_LA_APLICACION]
    return {
        "interfaz": {
            # Plantilla de la que heredan las páginas: la página entera, o solo la zona central si la
            # pide la navegación con htmx.
            "plantilla": "base/zona.html" if pide_solo_la_zona(request) else "base/pagina.html",
            "menu": registro.menu,
            "seccion": seccion,
            # Códigos de las entradas del camino, para marcarlas en el menú.
            "codigos": [entrada.codigo for entrada in camino],
            "vistas": vistas,
            "ayuda": registro.ayuda.get(seccion.codigo) if seccion else None,
            "titulo": " · ".join(parte for parte in partes if parte),
            # Alias de quien ha iniciado sesión. Hasta que exista «usuarios» (fase 1), no hay sesiones.
            "alias": "Sin sesión",
        }
    }


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
