"""
Pantallas del módulo «base»: la portada de cada cuenta («Inicio»: Panel y Mis datos, aún por hacer) y la
demostración de la plantilla general («Desarrollo y mantenimiento → Componentes»: Estructura y Componentes).
"""

from django.shortcuts import render

from .demostracion import FormularioDeDemostracion, tabla_de_demostracion


# Pantalla «Inicio → Panel»: la portada de cada cuenta, adonde se va al iniciar sesión y al pulsar el
# nombre de la aplicación. Aún por hacer: tendrá lo pendiente y los proyectos abiertos.
def inicio(request):
    descripcion = (
        "Tu panel: arriba, las comunicaciones y solicitudes pendientes (las que has enviado y las que has "
        "recibido); debajo, los proyectos en los que participas que siguen abiertos. Todo se podrá pulsar."
    )
    return render(request, "base/proximamente.html", {"descripcion": descripcion})


# Pantalla «Inicio → Mis datos»: resumen de los datos de la cuenta. Aún por hacer.
def mis_datos(request):
    descripcion = (
        "Tus datos de un vistazo: tu alias y lo que ven los demás, tus talentos, lo que solo ves tú (tu lugar…) "
        "y el árbol de tus grupos con tu rol en cada uno. Cada panel con un botón para editarlo."
    )
    return render(request, "base/proximamente.html", {"descripcion": descripcion})


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
