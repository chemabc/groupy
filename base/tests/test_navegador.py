"""
Pruebas de pantalla con un navegador de verdad (Chromium sin interfaz, mediante Playwright).

Las demás pruebas comprueban el HTML que manda el servidor, pero no ejecutan el JavaScript. Estas abren
la página en Chromium, escriben, pulsan y miran el resultado, como lo haría una persona. Así se detectan
fallos como el de la tabla filtrable que no filtraba al escribir (el filtro buscaba las filas desde el
cuadro de texto en lugar de desde la tabla).

Si Playwright o su Chromium no están instalados, estas pruebas se saltan (ver docs/arranque.md).
"""

import os
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

try:
    from playwright.sync_api import Error as ErrorDePlaywright
    from playwright.sync_api import sync_playwright
except ImportError:  # Playwright no está instalado.
    sync_playwright = None


class PruebasEnElNavegador(StaticLiveServerTestCase):
    """
    Abre la aplicación en Chromium. StaticLiveServerTestCase arranca un servidor de verdad en un puerto
    libre, que también sirve los ficheros estáticos (CSS, htmx, Alpine).
    """

    # Una vez para toda la clase: arranca el servidor y Chromium.
    @classmethod
    def setUpClass(cls):
        if sync_playwright is None:
            raise unittest.SkipTest("Playwright no está instalado.")
        # Playwright mantiene un bucle asíncrono abierto en este hilo; Django lo toma por código asíncrono
        # y no deja usar la base de datos. Esta variable le dice que aquí es seguro.
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        try:
            cls.navegador = cls.playwright.chromium.launch()
        except ErrorDePlaywright as error:
            cls.playwright.stop()
            super().tearDownClass()
            raise unittest.SkipTest(f"Chromium no está instalado: {error}") from error

    # Una vez al final: cierra Chromium y el servidor.
    @classmethod
    def tearDownClass(cls):
        cls.navegador.close()
        cls.playwright.stop()
        super().tearDownClass()

    # Antes de cada prueba: una pestaña nueva que apunta los errores de JavaScript que aparezcan.
    def setUp(self):
        self.pagina = self.navegador.new_page(viewport={"width": 1400, "height": 900})
        self.errores = []
        self.pagina.on("pageerror", lambda error: self.errores.append(str(error)))
        self.addCleanup(self.pagina.close)

    # Abre una dirección de la aplicación.
    def abrir(self, direccion):
        self.pagina.goto(f"{self.live_server_url}{direccion}")

    # Escribe en un cuadro (por su atributo name) y espera a que la página reaccione.
    def escribir(self, nombre, texto, espera=150):
        self.pagina.locator(f'input[name="{nombre}"]').fill(texto)
        self.pagina.wait_for_timeout(espera)

    # Cuántas filas se ven en una tabla.
    def filas_visibles(self, identificador):
        return self.pagina.locator(f"#tabla-{identificador} tbody tr[data-texto]:visible").count()

    # Tabla pequeña: el buscador y los filtros de columna filtran al escribir, sin importar las tildes.
    def test_tabla_en_el_navegador(self):
        self.abrir("/componentes/")
        self.assertEqual(self.filas_visibles("pequena"), 200)
        self.escribir("pequena-q", "malaga")
        sin_tilde = self.filas_visibles("pequena")
        self.assertTrue(0 < sin_tilde < 200)
        self.escribir("pequena-q", "MÁLAGA")
        self.assertEqual(self.filas_visibles("pequena"), sin_tilde)
        self.escribir("pequena-q", "")
        self.escribir("pequena-c-grupo", "Córdoba")
        con_tilde = self.filas_visibles("pequena")
        self.escribir("pequena-c-grupo", "cordoba")
        self.assertEqual(self.filas_visibles("pequena"), con_tilde)
        self.assertIn("pequena-c-grupo=cordoba", self.pagina.url)
        self.assertEqual(self.errores, [])

    # Tabla pequeña: pulsar el título de una columna ordena las filas.
    def test_ordenar_en_el_navegador(self):
        self.abrir("/componentes/")
        self.pagina.locator('#tabla-pequena button[data-campo="plazas"]').click()
        plazas = [int(texto) for texto in self.pagina.locator("#tabla-pequena tbody td:nth-child(5)").all_inner_texts()]
        self.assertEqual(plazas, sorted(plazas))

    # Tabla grande: el filtro de columna se hace en el servidor y no se pierde el cuadro donde se escribe.
    def test_tabla_en_el_servidor(self):
        self.abrir("/componentes/")
        cuadro = self.pagina.locator('input[name="grande-c-grupo"]')
        cuadro.click()
        cuadro.press_sequentially("Ávila", delay=30)
        self.pagina.wait_for_selector("#tabla-grande-recuento:has-text('de 3')")
        grupos = set(self.pagina.locator("#tabla-grande tbody tr[data-texto] td:nth-child(3)").all_inner_texts())
        self.assertEqual(grupos, {"Asamblea de Ávila"})
        self.assertEqual(self.pagina.evaluate("document.activeElement.name"), "grande-c-grupo")
        self.assertEqual(self.errores, [])

    # Navegar con el menú superior cambia solo la zona central, y el botón ☰ estrecha el menú izquierdo.
    def test_navegacion_y_menu_plegable(self):
        self.abrir("/")
        menu = self.pagina.locator('nav[aria-label="Secciones"]').first
        ancho_inicial = menu.bounding_box()["width"]
        self.pagina.locator('button[title="Plegar o desplegar el menú"]').click()
        self.pagina.wait_for_timeout(100)
        self.assertLess(menu.bounding_box()["width"], ancho_inicial)
        self.pagina.locator("#zona nav a", has_text="Componentes").click()
        self.pagina.wait_for_selector("#tabla-pequena")
        self.assertTrue(self.pagina.url.endswith("/componentes/"))
        self.assertEqual(self.errores, [])
