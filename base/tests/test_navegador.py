"""
Pruebas de pantalla con un navegador de verdad (Chromium sin interfaz, mediante Playwright).

Las demás pruebas comprueban el HTML que manda el servidor, pero no ejecutan el JavaScript. Estas abren
la página en Chromium, escriben, pulsan y miran el resultado, como lo haría una persona. Así se detectan
fallos como el de la tabla filtrable que no filtraba al escribir (el filtro buscaba las filas desde el
cuadro de texto en lugar de desde la tabla).

La preparación común (Chromium, servidor, sesión iniciada) está en base/pruebas_navegador.py. Si
Playwright o su Chromium no están instalados, estas pruebas se saltan (ver docs/arranque.md).
"""

from base.pruebas_navegador import PruebaEnElNavegador


class PruebasEnElNavegador(PruebaEnElNavegador):
    """Tabla filtrable, navegación y menú plegable en Chromium, con la sesión iniciada."""

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
