"""
Pantallas de mentira para probar comprobar_consultas(). Las pruebas las usan como lista de direcciones
(ROOT_URLCONF) en lugar de config/urls.py.

Simulan dos pantallas con una lista de «filas» (aquí, una lista de Python):
- /buena/: hace siempre 2 consultas, tenga las filas que tenga.
- /mala/: hace 1 consulta más por cada fila, el error típico que la prueba debe detectar.
- /cara/: hace 16 consultas, una más del presupuesto.
"""

from django.db import connection
from django.http import HttpResponse
from django.urls import path

# Filas que «muestran» las pantallas. Las pruebas añaden filas con más_filas().
filas = ["primera"]


# Hace una consulta muy simple a la base de datos («SELECT 1»), para que cuente como una consulta.
def consulta():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


# Pantalla bien hecha: 2 consultas fijas, como si trajera todas las filas de una vez.
def buena(request):
    consulta()
    consulta()
    return HttpResponse(f"{len(filas)} filas")


# Pantalla mal hecha: 1 consulta fija más 1 por cada fila.
def mala(request):
    consulta()
    for _fila in filas:
        consulta()
    return HttpResponse(f"{len(filas)} filas")


# Pantalla demasiado cara: 16 consultas.
def cara(request):
    for _ in range(16):
        consulta()
    return HttpResponse("cara")


# Añade dos filas más. Se pasa a comprobar_consultas() como crear_mas_datos.
def mas_filas():
    filas.extend(["segunda", "tercera"])


urlpatterns = [
    path("buena/", buena),
    path("mala/", mala),
    path("cara/", cara),
]
