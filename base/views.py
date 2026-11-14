"""
Pantallas del módulo «base»: la portada de cada cuenta («Inicio»: Panel y Mis datos, con las tarjetas de los módulos) y la
demostración de la plantilla general («Desarrollo y mantenimiento → Componentes»: Estructura y Componentes).
"""

from django.shortcuts import render

from .demostracion import FormularioDeDemostracion, tabla_de_demostracion
from .inicio import filas_de


# Pantalla «Inicio → Panel»: la portada de cada cuenta, adonde se va al iniciar sesión y al pulsar el
# nombre de la aplicación. Un dashboard que resume otras secciones: arriba, las comunicaciones y las
# solicitudes pendientes (recibidas y enviadas); debajo, los proyectos abiertos en los que participas.
# Cada recuadro lo aporta su módulo (TarjetaDeInicio) y su sitio lo decide config/inicio.py. Cuesta la
# suma de las consultas de sus tarjetas (unas 13), haya lo que haya.
def inicio(request):
    contexto = {"filas": filas_de("panel", request), "pantalla": "panel"}
    return render(request, "base/portada.html", contexto)


# Pantalla «Inicio → Mis datos»: los datos de la cuenta de un vistazo, cada recuadro con su botón
# «Editar» (que lleva a «Configuración de mi cuenta → Mis datos» o a la sección de cada cosa): datos
# públicos, talentos, datos privados y lugar, y el árbol de tus grupos con tu rol en cada uno.
def mis_datos(request):
    contexto = {"filas": filas_de("mis_datos", request), "pantalla": "mis_datos"}
    return render(request, "base/portada.html", contexto)


# Pantalla «Desarrollo y mantenimiento → Componentes → Estructura»: explica las partes de la plantilla.
def estructura(request):
    return render(request, "base/inicio.html")


# Pantalla «Desarrollo y mantenimiento → Componentes → Componentes»: escaparate de las piezas comunes de la interfaz, con datos inventados.
# Muestra dos tablas filtrables (una pequeña, que se filtra en el navegador, y otra grande, que se filtra
# en el servidor) y un formulario para probar el botón «copiar». Si htmx pide solo una parte de una de las
# tablas (al filtrar en el servidor o con «Mostrar más»), devuelve solo esa parte.
def componentes(request):
    tablas = [
        tabla_de_demostracion(request, "pequena", 200),
        tabla_de_demostracion(request, "grande", 2000),
    ]
    for tabla in tablas:
        plantilla = tabla.plantilla_parcial()
        if plantilla:
            return render(request, plantilla, {"tabla": tabla})
    contexto = {"tabla_pequena": tablas[0], "tabla_grande": tablas[1], "formulario": FormularioDeDemostracion()}
    return render(request, "base/componentes.html", contexto)
