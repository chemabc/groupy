"""
Pruebas de «mantenimiento» en un navegador de verdad (ver base/pruebas_navegador.py): el menú de tres
niveles y las importaciones de grupos y usuarios de principio a fin (subir el fichero con htmx, ver la
vista previa y confirmar).
"""

import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings

from base.hojas import Hoja, crear_ods
from base.pruebas_navegador import PruebaEnElNavegador
from grupos.models import Grupo, Pertenencia
from grupos.servicios import crear_organizacion


class PruebasDeMantenimientoEnElNavegador(PruebaEnElNavegador):
    """Desarrollo y mantenimiento en Chromium, como superadmin."""

    # El usuario de la prueba pasa a ser superadmin.
    def setUp(self):
        super().setUp()
        get_user_model().objects.filter(pk=self.usuario.pk).update(es_superadmin=True)

    # Al entrar en «Pruebas», su sección se abre sola en el menú izquierdo y arriba salen las dos
    # importaciones; la pestaña «Importar usuarios» lleva a su pantalla sin recargar.
    def test_menu_de_tres_niveles(self):
        self.abrir("/mantenimiento/pruebas/grupos/")
        menu = self.pagina.locator('nav[aria-label="Secciones"]').first
        self.assertTrue(menu.get_by_text("Pruebas", exact=True).is_visible())
        self.assertTrue(menu.get_by_text("Ayuda y documentación").is_visible())
        self.pagina.locator("#zona nav a", has_text="Importar usuarios").click()
        self.pagina.wait_for_selector("text=Alta masiva de usuarios")
        self.assertTrue(self.pagina.url.endswith("/mantenimiento/pruebas/usuarios/"))
        self.assertEqual(self.errores, [])

    # Importar grupos: subir el .ods, ver la vista previa y confirmar.
    def test_importar_grupos(self):
        hoja = crear_ods([Hoja("Datos", [
            ["Organización", "Grupo", "Grupo padre", "Localización"],
            ["ORG Miño", "GRU Sil", "GRU Miño", "Ourense"],
            ["ORG Miño", "GRU Miño", "", ""],
        ])])
        self.abrir("/mantenimiento/pruebas/grupos/")
        self.pagina.locator('input[name="fichero"]').set_input_files(
            {"name": "grupos.ods", "mimeType": "application/vnd.oasis.opendocument.spreadsheet", "buffer": hoja}
        )
        self.pagina.get_by_role("button", name="Revisar").click()
        self.pagina.wait_for_selector("text=ORG Miño › GRU Miño › GRU Sil")
        self.pagina.get_by_role("button", name="Confirmar e importar").click()
        self.pagina.wait_for_selector("text=Importación hecha")
        self.assertEqual(Grupo.objects.get(nombre="GRU Sil").padre.nombre, "GRU Miño")
        self.assertEqual(self.errores, [])

    # Importar usuarios: activar el alta masiva, subir un .csv, confirmar y entrar con el alias nuevo.
    def test_importar_usuarios(self):
        crear_organizacion("ORG Miño", "GRU Miño")
        self.abrir("/mantenimiento/pruebas/usuarios/")
        self.pagina.get_by_role("button", name="Activar").click()
        self.pagina.wait_for_selector("text=Alta masiva de usuarios: activada.")
        texto = "Alias;Contraseña;Organización;Grupo\nCorzo;Clave-Larga-2026;ORG Miño;GRU Miño\n"
        self.pagina.locator('input[name="fichero"]').set_input_files(
            {"name": "usuarios.csv", "mimeType": "text/csv", "buffer": texto.encode("utf-8")}
        )
        self.pagina.get_by_role("button", name="Revisar").click()
        self.pagina.wait_for_selector("text=Será su asamblea base")
        self.pagina.get_by_role("button", name="Confirmar e importar").click()
        self.pagina.wait_for_selector("text=Importación hecha")
        self.assertTrue(Pertenencia.objects.filter(usuario__alias="Corzo", es_base=True).exists())
        self.pagina = self.pestana_nueva()
        self.entrar("corzo", "Clave-Larga-2026")
        self.assertEqual(self.pagina.locator('header a[title="Mi cuenta"]').inner_text(), "Corzo")
        self.assertEqual(self.errores, [])

    # Datos de ejemplo: crear; al borrar, se pide confirmación (si se cancela, no se borra nada). Las
    # pruebas van con DEBUG apagado, y sin él los botones no salen: aquí se enciende.
    @override_settings(DEBUG=True)
    def test_datos_de_ejemplo(self):
        self.abrir("/mantenimiento/pruebas/ejemplos/")
        self.pagina.get_by_role("button", name="Crear los datos de ejemplo").click()
        self.pagina.wait_for_selector("text=Creados los datos de ejemplo")
        self.assertTrue(Grupo.objects.filter(nombre="GRU Henares").exists())
        self.pagina.once("dialog", lambda dialogo: dialogo.dismiss())
        self.pagina.get_by_role("button", name="Borrar los datos de ejemplo").click()
        self.pagina.wait_for_timeout(300)
        self.assertTrue(Grupo.objects.filter(nombre="GRU Henares").exists())
        self.pagina.once("dialog", lambda dialogo: dialogo.accept())
        self.pagina.get_by_role("button", name="Borrar los datos de ejemplo").click()
        self.pagina.wait_for_selector("text=Borrados los datos de ejemplo")
        self.assertFalse(Grupo.objects.exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.usuario.pk).exists())
        self.assertEqual(self.errores, [])

    # El resaltado del menú: la subsección activa con fondo; su sección, solo con el texto en color.
    def test_resaltado_del_menu(self):
        self.abrir("/mantenimiento/pruebas/grupos/")
        menu = self.pagina.locator('nav[aria-label="Secciones"]').first
        seccion = menu.locator('a[data-codigo="mantenimiento.desarrollo"]')
        subseccion = menu.locator('a[data-codigo="mantenimiento.pruebas"]')
        self.assertIn("bg-marca/10", subseccion.get_attribute("class"))
        self.assertNotIn("bg-marca/10", seccion.get_attribute("class"))
        self.assertIn("text-marca", seccion.get_attribute("class"))



@override_settings(GUIAS_DE_DESARROLLO_PARA_TODOS=True)
class PruebasDeLasGuiasEnElNavegador(PruebaEnElNavegador):
    """Las guías de desarrollo, como una persona cualquiera (en desarrollo las ve todo el mundo)."""

    # «Arquitectura»: todos los bloques «mermaid» del documento son diagramas correctos (Mermaid los lee sin
    # error), el primero se dibuja al abrir y el último al bajar hasta él; los botones acercan (cambia la
    # transformación del dibujo).
    def test_diagramas(self):
        with open(settings.BASE_DIR / "docs" / "arquitectura.md", encoding="utf-8") as fichero:
            textos = re.findall(r"```mermaid\n(.*?)```", fichero.read(), re.DOTALL)
        self.assertGreater(len(textos), 20)
        self.abrir("/mantenimiento/guias/arquitectura/")
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
        self.abrir("/mantenimiento/guias/comprobaciones/")
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
