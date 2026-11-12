"""
Pantallas del módulo «base». De momento, las de la sección «Inicio», que sirven para ver funcionando la
plantilla general (menús, vistas, ayuda y tema) mientras no hay otros módulos.
"""

from django.shortcuts import render

from .demostracion import FormularioDeDemostracion, tabla_de_demostracion


# Pantalla «Inicio → Estructura»: explica las partes de la plantilla. Se llega desde el menú izquierdo o
# desde el nombre de la aplicación, y es adonde se va al iniciar sesión.
def inicio(request):
    return render(request, "base/inicio.html")


# Pantalla «Inicio → Componentes»: escaparate de las piezas comunes de la interfaz, con datos inventados.
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
