"""
Pruebas de «usuarios» en un navegador de verdad (ver base/pruebas_navegador.py): entrar, salir y que las
preferencias se guarden en la cuenta.
"""

from base.pruebas_navegador import PruebaEnElNavegador


class PruebasDeUsuariosEnElNavegador(PruebaEnElNavegador):
    """Entrada, salida y preferencias en Chromium."""

    # Tras entrar (lo hace setUp), la cabecera muestra el alias; «Salir» lleva a la entrada.
    def test_entrar_y_salir(self):
        self.assertEqual(self.pagina.locator('header a[title="Mi cuenta"]').inner_text(), "Prueba")
        self.pagina.locator("header button", has_text="Salir").click()
        self.pagina.wait_for_url("**/cuenta/entrar/")
        self.abrir("/")
        self.assertIn("/cuenta/entrar/", self.pagina.url)
        self.assertEqual(self.errores, [])

    # Un tema elegido en «Mi cuenta» se guarda en la cuenta: en otro navegador (sin nada guardado),
    # al entrar, la página sale ya con ese tema.
    def test_preferencias_en_otro_navegador(self):
        self.abrir("/cuenta/preferencias/")
        with self.pagina.expect_response("**/cuenta/preferencias/guardar/") as respuesta:
            self.pagina.locator('button[data-clave="tema"][data-valor="dia"]').click()
        self.assertEqual(respuesta.value.status, 204)
        self.assertEqual(self.pagina.evaluate("document.documentElement.dataset.tema"), "dia")
        self.pagina = self.pestana_nueva()
        self.entrar("prueba")
        self.assertEqual(self.pagina.evaluate("document.documentElement.dataset.tema"), "dia")
        self.assertEqual(self.errores, [])

    # Navegar a «Mi cuenta → Contraseña» con el menú superior y cambiarla sin salir de la zona central.
    def test_cambiar_contrasena(self):
        self.abrir("/cuenta/preferencias/")
        self.pagina.locator("#zona nav a", has_text="Contraseña").click()
        self.pagina.wait_for_selector('input[name="old_password"]')
        self.pagina.locator('input[name="old_password"]').fill("contraseña-de-prueba")
        self.pagina.locator('input[name="new_password1"]').fill("Otra-Contraseña-Larga-7")
        self.pagina.locator('input[name="new_password2"]').fill("Otra-Contraseña-Larga-7")
        self.pagina.locator("#zona button[type=submit]").click()
        self.pagina.wait_for_selector("text=Contraseña cambiada")
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("Otra-Contraseña-Larga-7"))
        self.assertEqual(self.errores, [])
