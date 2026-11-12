"""
Ayuda común para las pruebas de pantalla con un navegador de verdad (Chromium sin interfaz, mediante
Playwright). La usan los ficheros test_navegador.py de cada módulo.

Las demás pruebas comprueban el HTML que manda el servidor, pero no ejecutan el JavaScript. Estas abren
la página en Chromium, escriben, pulsan y miran el resultado, como lo haría una persona.

Si Playwright o su Chromium no están instalados, estas pruebas se saltan (ver docs/arranque.md).
"""

import os
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from .pruebas import CONTRASENA_DE_PRUEBA, crear_usuario_de_prueba

try:
    from playwright.sync_api import Error as ErrorDePlaywright
    from playwright.sync_api import sync_playwright
except ImportError:  # Playwright no está instalado.
    sync_playwright = None


class PruebaEnElNavegador(StaticLiveServerTestCase):
    """
    Abre la aplicación en Chromium. StaticLiveServerTestCase arranca un servidor de verdad en un puerto
    libre, que también sirve los ficheros estáticos (CSS, htmx, Alpine). Cada prueba empieza con una
    pestaña nueva y con un usuario (self.usuario) que ya ha iniciado sesión por la pantalla de entrada.
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

    # Antes de cada prueba: crea el usuario, abre una pestaña nueva que apunta los errores de JavaScript
    # que aparezcan e inicia sesión.
    def setUp(self):
        self.usuario = crear_usuario_de_prueba()
        self.pagina = self.pestana_nueva()
        self.entrar(self.usuario.get_username())

    # Abre una pestaña en un contexto nuevo (como otro navegador: sin cookies ni nada guardado) y la
    # devuelve. Los errores de JavaScript se apuntan en self.errores.
    def pestana_nueva(self):
        contexto = self.navegador.new_context(viewport={"width": 1400, "height": 900})
        self.addCleanup(contexto.close)
        pagina = contexto.new_page()
        self.errores = []
        pagina.on("pageerror", lambda error: self.errores.append(str(error)))
        return pagina

    # Inicia sesión en la pestaña actual escribiendo el alias y la contraseña, como haría una persona.
    #   - alias: lo que se escribe en el cuadro «Alias».
    #   - contrasena: la contraseña.
    def entrar(self, alias, contrasena=CONTRASENA_DE_PRUEBA):
        self.abrir("/cuenta/entrar/")
        self.pagina.locator('input[name="username"]').fill(alias)
        self.pagina.locator('input[name="password"]').fill(contrasena)
        self.pagina.locator('button[type="submit"]').click()
        self.pagina.wait_for_load_state()

    # Abre una dirección de la aplicación.
    def abrir(self, direccion):
        self.pagina.goto(f"{self.live_server_url}{direccion}")

    # Escribe en un cuadro (por su atributo name) y espera a que la página reaccione.
    def escribir(self, nombre, texto, espera=150):
        self.pagina.locator(f'input[name="{nombre}"]').fill(texto)
        self.pagina.wait_for_timeout(espera)
