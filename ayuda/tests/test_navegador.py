"""
Pruebas de «ayuda» en un navegador de verdad (ver base/pruebas_navegador.py): los diagramas y las
casillas de los documentos, el índice plegable y el panel de ayuda de la derecha (abrirlo con el «?» rojo,
navegar por el menú sin que se vuelva a pintar, sus pestañas y enlaces, arrastrar la línea de
separación, cambiar el tamaño de la letra y recordar todo al recargar) y, aparte, la miniayuda «?» de cada
sección, que sigue siendo una ventana emergente.
"""

import re

from django.conf import settings
from django.test import override_settings

from base.pruebas_navegador import PruebaEnElNavegador


@override_settings(GUIAS_DE_DESARROLLO_PARA_TODOS=True)
class PruebasDeLosDocumentosEnElNavegador(PruebaEnElNavegador):
    """Los documentos de la ayuda, como una persona cualquiera (en desarrollo los ve todo el mundo)."""

    # «Arquitectura»: todos los bloques «mermaid» del documento son diagramas correctos (Mermaid los lee sin
    # error), el primero se dibuja al abrir y el último al bajar hasta él; los botones acercan (cambia la
    # transformación del dibujo).
    def test_diagramas(self):
        with open(settings.BASE_DIR / "docs" / "arquitectura.md", encoding="utf-8") as fichero:
            textos = re.findall(r"```mermaid\n(.*?)```", fichero.read(), re.DOTALL)
        self.assertGreater(len(textos), 20)
        self.abrir("/ayuda/arquitectura/")
        self.pagina.wait_for_function("window.mermaid !== undefined", timeout=60000)
        malos = self.pagina.evaluate(
            """async (textos) => {
                const malos = [];
                for (const [numero, texto] of textos.entries()) {
                    try { await window.mermaid.parse(texto); } catch (error) { malos.push(`${numero}: ${error.message}`); }
                }
                return malos;
            }""",
            textos,
        )
        self.assertEqual(malos, [])
        primero = self.pagina.locator(".diagrama").first
        primero.locator("svg").wait_for(timeout=60000)
        vista = primero.locator("svg g.svg-pan-zoom_viewport")
        antes = vista.get_attribute("transform")
        primero.get_by_role("button", name="Acercar").click()
        self.pagina.wait_for_timeout(300)
        self.assertNotEqual(vista.get_attribute("transform"), antes)
        primero.get_by_role("button", name="Ajustar a la caja").click()
        # Baja hasta el final de la parte central de la página: el último diagrama se dibuja al acercarse.
        self.pagina.evaluate("document.getElementById('desplazable').scrollTo(0, 1e9)")
        self.pagina.wait_for_function(
            "(() => { const todos = document.querySelectorAll('.documento > :is(pre, .diagrama)');"
            " return todos[todos.length - 1].matches('.diagrama'); })()", timeout=60000,
        )
        self.assertEqual(self.pagina.locator("text=Este diagrama tiene un error").count(), 0)
        self.assertEqual(self.errores, [])

    # «Comprobaciones pendientes»: las casillas se marcan, el recuento cambia y siguen marcadas al volver.
    def test_casillas(self):
        self.abrir("/ayuda/comprobaciones/")
        casillas = self.pagina.locator("input[data-casilla]")
        casillas.first.wait_for()
        total = casillas.count()
        self.assertGreater(total, 10)
        recuento = self.pagina.locator(".recuento-de-casillas")
        self.assertIn(f"0 de {total}", recuento.inner_text())
        casillas.nth(1).check()
        self.assertIn(f"1 de {total}", recuento.inner_text())
        self.pagina.reload()
        self.pagina.locator("input[data-casilla]").first.wait_for()
        self.assertTrue(self.pagina.locator("input[data-casilla]").nth(1).is_checked())
        self.assertFalse(self.pagina.locator("input[data-casilla]").first.is_checked())
        self.assertEqual(self.errores, [])


@override_settings(GUIAS_DE_DESARROLLO_PARA_TODOS=True)
class PruebasDelPanelDeAyuda(PruebaEnElNavegador):
    """El panel de ayuda de la derecha y el índice plegable, como una persona cualquiera."""

    # Abre una página de la ayuda con el «?» rojo de la cabecera: primero se despliega su menú y, al
    # elegir, se carga en el panel.
    #   - nombre: el texto del elemento del menú («Tutorial», «How to?»…).
    def abrir_con_el_boton_rojo(self, nombre):
        self.pagina.locator("#boton-de-ayuda").click()
        self.pagina.get_by_role("menuitem", name=nombre, exact=True).click()
        self.pagina.locator("#panel-de-ayuda-contenido article.documento").wait_for()

    # Ancho de un elemento en la pantalla, en píxeles.
    def ancho(self, selector):
        return self.pagina.locator(selector).bounding_box()["width"]

    # El panel se abre con el «?» rojo y estrecha la zona principal. Al navegar con el menú de la
    # izquierda, el panel no se vuelve a pintar (lleva una marca puesta a mano que sigue ahí); sus
    # pestañas se abren dentro de él sin cambiar la dirección de la página; se cierra con ✕.
    def test_abrir_y_navegar(self):
        self.abrir("/componentes/")
        ancho_sin_panel = self.ancho("#zona")
        self.assertFalse(self.pagina.locator("#panel-de-ayuda").is_visible())
        self.abrir_con_el_boton_rojo("Tutorial")
        panel = self.pagina.locator("#panel-de-ayuda")
        self.assertTrue(panel.is_visible())
        self.assertLess(self.ancho("#zona"), ancho_sin_panel)
        self.assertIn("Tutorial", panel.locator('a[aria-current="page"]').inner_text())
        # Marca a mano el documento del panel y navega con el menú superior y con el izquierdo.
        self.pagina.evaluate("document.querySelector('#panel-de-ayuda-contenido article').dataset.marca = 'sigue'")
        self.pagina.locator("#zona nav a", has_text="Estructura").click()
        self.pagina.wait_for_url(re.compile(r"/$"))
        self.pagina.locator('nav[aria-label="Secciones"] a[data-codigo="usuarios.cuenta"]').first.click()
        self.pagina.wait_for_url(re.compile(r"/cuenta/preferencias/$"))
        self.assertEqual(self.pagina.locator("#panel-de-ayuda-contenido article").get_attribute("data-marca"), "sigue")
        # Una pestaña del panel se abre en el panel; la página principal no cambia.
        panel.get_by_role("link", name="Arquitectura", exact=True).click()
        self.pagina.wait_for_selector('#panel-de-ayuda a[aria-current="page"]:has-text("Arquitectura")')
        self.assertTrue(self.pagina.url.endswith("/cuenta/preferencias/"))
        panel.get_by_role("button", name="Cerrar el panel de ayuda").click()
        self.assertFalse(panel.is_visible())
        self.assertEqual(self.errores, [])

    # Al recargar, el panel sigue abierto con la misma página; cerrado, sigue cerrado.
    def test_se_recuerda_al_recargar(self):
        self.abrir("/")
        self.abrir_con_el_boton_rojo("How to?")
        self.pagina.reload()
        self.pagina.locator("#panel-de-ayuda-contenido article.documento").wait_for()
        self.assertIn("How to?", self.pagina.locator("#panel-de-ayuda h2.truncate").inner_text())
        self.pagina.get_by_role("button", name="Cerrar el panel de ayuda").click()
        self.pagina.reload()
        self.pagina.wait_for_load_state()
        self.assertFalse(self.pagina.locator("#panel-de-ayuda").is_visible())
        self.assertEqual(self.errores, [])

    # La línea de separación se arrastra: el panel se ensancha lo que se arrastra y el ancho se recuerda
    # al recargar. Con el panel muy ancho, la zona principal no baja de 32rem y sale la barra de abajo.
    def test_arrastrar_la_separacion(self):
        self.abrir("/componentes/")
        self.abrir_con_el_boton_rojo("How to?")
        antes = self.ancho("#panel-de-ayuda")
        linea = self.pagina.locator('#panel-de-ayuda [role="separator"]').bounding_box()
        x, y = linea["x"] + linea["width"] / 2, linea["y"] + linea["height"] / 2
        self.pagina.mouse.move(x, y)
        self.pagina.mouse.down()
        self.pagina.mouse.move(x - 150, y, steps=5)
        self.pagina.mouse.up()
        despues = self.ancho("#panel-de-ayuda")
        self.assertAlmostEqual(despues - antes, 150, delta=4)
        self.pagina.reload()
        self.pagina.locator("#panel-de-ayuda-contenido article.documento").wait_for()
        self.assertAlmostEqual(self.ancho("#panel-de-ayuda"), despues, delta=2)
        # Ensancha hasta el tope: la zona se queda en 32rem (512 px) y se desplaza de lado.
        linea = self.pagina.locator('#panel-de-ayuda [role="separator"]').bounding_box()
        self.pagina.mouse.move(linea["x"] + 2, y)
        self.pagina.mouse.down()
        self.pagina.mouse.move(0, y, steps=5)
        self.pagina.mouse.up()
        self.assertGreaterEqual(self.ancho("#zona"), 512)
        self.assertTrue(self.pagina.evaluate("(() => { const d = document.getElementById('desplazable'); return d.scrollWidth > d.clientWidth; })()"))
        self.assertEqual(self.errores, [])

    # El «?» gris de una sección abre su miniayuda en una ventana emergente, no en el panel; «Entendido»
    # la cierra.
    def test_miniayuda_de_la_seccion(self):
        self.abrir("/ayuda/como-se-hace/")
        self.pagina.locator("#zona").get_by_role("button", name="Ayuda de esta sección").click()
        ventana = self.pagina.get_by_role("dialog")
        ventana.get_by_text("No sabes cómo convocar una reunión").wait_for()
        self.assertFalse(self.pagina.locator("#panel-de-ayuda").is_visible())
        ventana.get_by_role("button", name="Entendido").click()
        self.pagina.wait_for_timeout(300)
        self.assertFalse(ventana.is_visible())
        self.assertEqual(self.errores, [])

    # «Abrir en grande» lleva la página del panel a la zona principal.
    def test_abrir_en_grande(self):
        self.abrir("/")
        self.abrir_con_el_boton_rojo("How to?")
        self.pagina.locator("#panel-de-ayuda").get_by_role("link", name="Abrir en grande ↗").click()
        self.pagina.wait_for_url(re.compile(r"/ayuda/como-se-hace/$"))
        self.pagina.locator("#zona article.documento").wait_for()
        self.assertEqual(self.errores, [])

    # Los botones − y + cambian el tamaño de la letra del panel (no el de la zona principal), sin que
    # nada se salga de lado, con un tope por cada lado, y se recuerda al recargar.
    def test_tamano_de_letra(self):
        self.abrir("/")
        self.abrir_con_el_boton_rojo("Tutorial")
        panel = self.pagina.locator("#panel-de-ayuda")
        titulo = panel.locator("article.documento h1")
        alto = titulo.bounding_box()["height"]
        zona = self.pagina.locator("#zona h1").bounding_box()["height"]
        mas = panel.get_by_role("button", name="Letra más grande")
        mas.click()
        mas.click()
        self.assertIn("125 %", panel.get_by_role("group").inner_text())
        self.assertGreater(titulo.bounding_box()["height"], alto)
        self.assertEqual(self.pagina.locator("#zona h1").bounding_box()["height"], zona)
        sobresale = "(() => { const d = document.getElementById('panel-de-ayuda-desplazable'); return d.scrollWidth - d.clientWidth; })()"
        self.assertEqual(self.pagina.evaluate(sobresale), 0)
        self.pagina.reload()
        self.pagina.locator("#panel-de-ayuda-contenido article.documento").wait_for()
        self.assertIn("125 %", panel.get_by_role("group").inner_text())
        menos = panel.get_by_role("button", name="Letra más pequeña")
        for _vez in range(10):
            if menos.is_enabled():
                menos.click()
        self.assertIn("70 %", panel.get_by_role("group").inner_text())
        self.assertTrue(menos.is_disabled())
        self.assertEqual(self.errores, [])

    # Las anclas del índice, dentro del panel, bajan hasta su título en el panel sin tocar la página.
    def test_indice_en_el_panel(self):
        self.abrir("/")
        self.abrir_con_el_boton_rojo("Diseño y decisiones")
        panel = self.pagina.locator("#panel-de-ayuda")
        # En el panel, el índice sale plegado de entrada.
        self.assertFalse(panel.locator(".toc").is_visible())
        panel.get_by_role("button", name="Índice").click()
        enlace = panel.locator(".toc a").nth(5)
        destino = enlace.get_attribute("href")
        enlace.click()
        self.pagina.wait_for_timeout(300)
        self.assertGreater(self.pagina.evaluate("document.getElementById('panel-de-ayuda-desplazable').scrollTop"), 0)
        self.assertNotIn(destino, self.pagina.url)
        self.assertEqual(self.errores, [])

    # En la zona principal, el índice está a la izquierda y desplegado; su botón lo pliega (el texto se
    # ensancha) y se recuerda al recargar.
    def test_indice_plegable(self):
        self.abrir("/ayuda/diseno/")
        indice = self.pagina.locator("#zona .toc")
        self.assertTrue(indice.is_visible())
        ancho = self.ancho("#zona article.documento")
        self.pagina.locator("#zona").get_by_role("button", name="Índice").click()
        self.assertFalse(indice.is_visible())
        self.assertGreater(self.ancho("#zona article.documento"), ancho)
        self.pagina.reload()
        self.pagina.locator("#zona article.documento").wait_for()
        self.assertFalse(self.pagina.locator("#zona .toc").is_visible())
        self.assertEqual(self.errores, [])
