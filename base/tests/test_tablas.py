"""
Pruebas de la tabla filtrable (base/tablas.py), de la pantalla «Componentes» y del botón «copiar».

Para la fuente de base de datos se usa la tabla de grupos de Django (auth.Group), que existe en la base
de pruebas: así se comprueban de verdad la búsqueda sin tildes de PostgreSQL y el número de consultas.
"""

from django.contrib.auth.models import Group
from django.test import RequestFactory, SimpleTestCase, TestCase

from base.demostracion import FormularioDeDemostracion, filas_inventadas, tabla_de_demostracion
from base.pruebas import PruebaDePantalla
from base.tablas import Columna, FuenteDeConsulta, Tabla, normalizar

# Crea peticiones de mentira sin pasar por las direcciones de la aplicación.
peticiones = RequestFactory()


# Petición de htmx que pide solo una parte de una tabla.
#   - parametros: los de la dirección.
#   - objetivo: id del elemento que se sustituye.
def peticion_de_htmx(parametros, objetivo):
    return peticiones.get("/", parametros, headers={"HX-Request": "true", "HX-Target": objetivo})


class PruebasDeTablaEnMemoria(SimpleTestCase):
    """Comprueba la tabla con filas en memoria (FuenteDeLista): modo, filtros, orden y «Mostrar más»."""

    # Con 200 filas, todas van a la página y se filtra en el navegador.
    def test_pocas_filas_en_el_navegador(self):
        tabla = tabla_de_demostracion(peticiones.get("/"), "t", 200)
        self.assertTrue(tabla.en_navegador)
        self.assertEqual(len(tabla.filas), 200)
        self.assertFalse(tabla.hay_mas)

    # Con 2.000 filas se filtra en el servidor: se cargan 100 y queda «Mostrar más».
    def test_muchas_filas_en_el_servidor(self):
        tabla = tabla_de_demostracion(peticiones.get("/"), "t", 2000)
        self.assertFalse(tabla.en_navegador)
        self.assertEqual(len(tabla.filas), 100)
        self.assertEqual(tabla.total, 2000)
        self.assertTrue(tabla.hay_mas)

    # La búsqueda no distingue tildes ni mayúsculas, y todas las palabras deben aparecer.
    def test_busqueda_sin_tildes(self):
        tabla = tabla_de_demostracion(peticiones.get("/", {"t-q": "MALAGA reunion"}), "t", 2000)
        self.assertGreater(tabla.total, 0)
        for fila in tabla.filas:
            self.assertIn("Málaga", fila["grupo"])
            self.assertTrue(fila["titulo"].startswith("Reunión"))

    # El desplegable de categoría filtra por su valor.
    def test_filtro_de_categoria(self):
        tabla = tabla_de_demostracion(peticiones.get("/", {"t-tipologia": "accion"}), "t", 2000)
        self.assertTrue(all(fila["tipologia"] == "accion" for fila in tabla.filas))

    # Una categoría que no está entre las opciones o un orden por una columna que no existe se ignoran.
    def test_parametros_no_previstos(self):
        tabla = tabla_de_demostracion(peticiones.get("/", {"t-tipologia": "nada", "t-orden": "secreto"}), "t", 2000)
        self.assertEqual(tabla.categorias, {})
        self.assertEqual(tabla.orden, "")
        self.assertEqual(tabla.total, 2000)

    # El orden descendente por fecha deja las fechas de mayor a menor.
    def test_orden_descendente(self):
        tabla = tabla_de_demostracion(peticiones.get("/", {"t-orden": "-fecha"}), "t", 2000)
        fechas = [fila["fecha"] for fila in tabla.filas]
        self.assertEqual(fechas, sorted(fechas, reverse=True))

    # «Mostrar más» carga las 100 siguientes, sin repetir.
    def test_mostrar_mas(self):
        primera = tabla_de_demostracion(peticiones.get("/", {"t-orden": "titulo"}), "t", 2000)
        segunda = tabla_de_demostracion(peticion_de_htmx({"t-orden": "titulo", "t-desde": "100"}, "tabla-t-mas"), "t", 2000)
        ordenadas = sorted(filas_inventadas(2000), key=lambda fila: fila["titulo"])
        self.assertEqual(segunda.plantilla_parcial(), "base/tabla_filas.html")
        self.assertEqual(primera.filas, ordenadas[:100])
        self.assertEqual(segunda.filas, ordenadas[100:200])

    # Al pulsar una columna: primero ascendente, luego descendente.
    def test_cabeceras(self):
        tabla = tabla_de_demostracion(peticiones.get("/", {"t-orden": "fecha"}), "t", 200)
        fecha = next(cabecera for cabecera in tabla.cabeceras() if cabecera["columna"].campo == "fecha")
        self.assertEqual(fecha["flecha"], "▲")
        self.assertIn('"-fecha"', fecha["valores_al_pulsar"])

    # normalizar quita tildes, diéresis y mayúsculas.
    def test_normalizar(self):
        self.assertEqual(normalizar("Reunión ÑANDÚ pingüino"), "reunion nandu pinguino")


class PruebasDeTablaEnBaseDeDatos(TestCase):
    """Comprueba FuenteDeConsulta con PostgreSQL: búsqueda con unaccent y número de consultas."""

    # Crea 12 grupos de Django con nombres con tilde.
    @classmethod
    def setUpTestData(cls):
        Group.objects.bulk_create([Group(name=f"Asamblea de Málaga {numero}") for numero in range(10)])
        Group.objects.bulk_create([Group(name="Comisión de Ávila"), Group(name="Comisión de Cádiz")])

    # Crea la tabla de grupos con un límite pequeño, para probar los dos modos con pocas filas.
    #   - request: la petición.
    #   - limite: máximo de filas para filtrar en el navegador.
    def tabla(self, request, limite):
        return Tabla(
            request,
            identificador="grupos",
            columnas=[Columna("name", "Nombre")],
            fuente=FuenteDeConsulta(Group.objects.all(), campos_de_busqueda=["name"]),
            limite=limite,
            tamano_de_pagina=5,
        )

    # En el navegador cuesta una sola consulta.
    def test_una_consulta_en_el_navegador(self):
        with self.assertNumQueries(1):
            tabla = self.tabla(peticiones.get("/"), limite=500)
            tabla.filas_pintadas()
        self.assertTrue(tabla.en_navegador)

    # En el servidor, la página entera cuesta 3 consultas (tanteo, recuento y filas), con 5 filas o con 12.
    def test_tres_consultas_en_el_servidor(self):
        with self.assertNumQueries(3):
            tabla = self.tabla(peticiones.get("/"), limite=4)
            tabla.filas_pintadas()
        self.assertFalse(tabla.en_navegador)
        self.assertEqual(len(tabla.filas), 5)

    # Una petición de htmx se ahorra el tanteo: 2 consultas.
    def test_dos_consultas_en_una_peticion_de_htmx(self):
        with self.assertNumQueries(2):
            self.tabla(peticion_de_htmx({"grupos-q": "comision"}, "tabla-grupos-resultado"), limite=4)

    # PostgreSQL busca sin tildes gracias a unaccent: «avila» encuentra «Ávila» y «malaga», «Málaga».
    def test_unaccent(self):
        tabla = self.tabla(peticion_de_htmx({"grupos-q": "avila"}, "tabla-grupos-resultado"), limite=4)
        self.assertEqual([grupo.name for grupo in tabla.filas], ["Comisión de Ávila"])
        tabla = self.tabla(peticion_de_htmx({"grupos-q": "MALAGA"}, "tabla-grupos-resultado"), limite=4)
        self.assertEqual(tabla.total, 10)


class PruebasDeLaPantallaDeComponentes(PruebaDePantalla):
    """Comprueba la pantalla «Inicio → Componentes» y sus respuestas parciales."""

    # No hace ninguna consulta: los datos son inventados y están en memoria.
    def test_consultas(self):
        self.comprobar_consultas("/componentes/", 0, None)

    # La página lleva las dos tablas, cada una en su modo, y el formulario.
    def test_contenido(self):
        respuesta = self.client.get("/componentes/")
        self.assertContains(respuesta, 'x-data="tablaLocal"', count=1)
        self.assertContains(respuesta, 'id="tabla-grande-mas"', count=1)
        self.assertContains(respuesta, "Mostrando 100 de 2000")

    # Al filtrar en el servidor, htmx recibe solo el resultado de esa tabla.
    def test_resultado_parcial(self):
        cabeceras = {"HX-Request": "true", "HX-Target": "tabla-grande-resultado"}
        respuesta = self.client.get("/componentes/?grande-q=cordoba", headers=cabeceras)
        self.assertNotContains(respuesta, "<html")
        self.assertNotContains(respuesta, "tabla-pequena")
        self.assertContains(respuesta, 'id="tabla-grande-resultado"')
        self.assertContains(respuesta, "Córdoba")
        self.assertNotContains(respuesta, "Málaga")


class PruebasDelBotonCopiar(SimpleTestCase):
    """Comprueba que todos los campos de texto llevan botón «copiar» y su explicación visible."""

    # Los 5 campos con texto llevan botón; la casilla «Pública», no. Las explicaciones se ven.
    def test_botones_y_explicaciones(self):
        html = str(FormularioDeDemostracion())
        self.assertEqual(html.count('x-data="copiar"'), 5)
        self.assertIn('data-objetivo="id_titulo"', html)
        self.assertNotIn('data-objetivo="id_publica"', html)
        self.assertIn("Número máximo de personas que pueden inscribirse.", html)
