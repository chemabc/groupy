"""
Pruebas de «Organizaciones y grupos» en un navegador de verdad (ver base/pruebas_navegador.py): el número
de «Invitaciones (N)» del menú se pone al día al navegar con htmx, sin recargar la página ni volver a
pintar el menú (base/zona.html manda el número aparte, con hx-swap-oob).
"""

from base.contrato import Ancla
from base.pruebas import contratos_de_prueba, crear_usuario_de_prueba, modulo_falso
from base.pruebas_navegador import PruebaEnElNavegador
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion, invitar, relacionar

# Módulo de mentira con un ancla, para poder invitar a algo.
ALFA = modulo_falso("alfa", anclas=(Ancla("alfa.proyecto", "auth.Group", "Un proyecto de mentira"),))


class PruebasDeGruposEnElNavegador(PruebaEnElNavegador):
    """El usuario de la prueba es admin de GRU Segre (ORG Ebro), que recibe una invitación de GRU Henares."""

    # Al aceptar la invitación, el menú pasa de «(1)» a «(0)» sin recargar; la sección sigue abierta.
    def test_contador_del_menu(self):
        tajo, general = crear_organizacion("ORG Tajo", "GRU Tajo")
        henares = crear_grupo(tajo, "GRU Henares", padre=general)
        ebro, segre = crear_organizacion("ORG Ebro", "GRU Segre")
        lince = crear_usuario_de_prueba("Lince")
        admitir(lince, henares, rol=Pertenencia.ADMIN_GRUPO)
        admitir(self.usuario, segre, rol=Pertenencia.ADMIN_GRUPO)
        with contratos_de_prueba(ALFA):
            invitar("alfa.proyecto", 7, henares, segre, lince, "Hagamos algo juntos")

            self.abrir("/organizaciones/")
            # El número sale en la sección de administrar que lleva «Invitaciones entre grupos» como pestaña.
            contador = self.pagina.locator("#contador-administraciongrupos")
            self.assertEqual(contador.inner_text(), "(1)")
            # Se entra con el menú (htmx), se pasa a la pestaña y se acepta.
            self.pagina.locator('nav[aria-label="Secciones"] a[data-codigo="administracion.grupos"]').first.click()
            self.pagina.locator("#zona nav a", has_text="Invitaciones entre grupos").click()
            self.pagina.locator('button[value="aceptar"]').click()
            self.pagina.wait_for_selector("text=Aceptada")
            self.assertEqual(contador.inner_text(), "(0)")
            # Solo hay un contador de invitaciones en la página (htmx lo ha sustituido, no duplicado).
            self.assertEqual(self.pagina.locator("#contador-administraciongrupos").count(), 1)
        self.assertEqual(self.errores, [])


class PruebasDelGrafoEnElNavegador(PruebaEnElNavegador):
    """«Mis grupos → Grafo»: ORG Tajo (GRU Tajo ⊃ GRU Henares); el usuario de la prueba está en GRU Henares, que
    colabora con GRU Jarama (que no ve)."""

    # El grafo se dibuja (Mermaid, sin errores), con la relación, y al pulsar GRU Henares se va a su ficha.
    def test_grafo(self):
        tajo, general = crear_organizacion("ORG Tajo", "GRU Tajo")
        henares = crear_grupo(tajo, "GRU Henares", padre=general)
        jarama = crear_grupo(tajo, "GRU Jarama", padre=general)
        admitir(self.usuario, henares, es_base=True)
        relacionar(henares, jarama, "colabora")
        self.abrir("/organizaciones/grafo/")
        nodo = self.pagina.locator("g.node", has_text="GRU Henares")
        nodo.wait_for()
        self.assertEqual(self.pagina.locator("g.node", has_text="GRU Jarama").count(), 1)
        self.assertIn("colabora", self.pagina.locator(".diagrama").inner_text())
        with self.pagina.expect_navigation():
            nodo.click()
        self.assertTrue(self.pagina.url.endswith(f"/organizaciones/grupo/{henares.pk}/"))
        self.assertEqual(self.errores, [])


class PruebasDeMiembrosEnElNavegador(PruebaEnElNavegador):
    """«Administrar → Miembros»: el usuario de la prueba administra GRU Henares (ORG Tajo)."""

    # Se marcan dos filas y se sacan del grupo de una vez, aceptando la confirmación; sale el aviso. Hacer
    # admins no se ofrece (es admin de grupo, no de la organización). La fila de un grupo que no es la base de
    # la persona sale tenue.
    def test_en_bloque(self):
        tajo, general = crear_organizacion("ORG Tajo", "GRU Tajo")
        henares = crear_grupo(tajo, "GRU Henares", padre=general)
        jarama = crear_grupo(tajo, "GRU Jarama", padre=general)
        admitir(self.usuario, henares, rol=Pertenencia.ADMIN_GRUPO)
        nutria, garza = crear_usuario_de_prueba("Nutria"), crear_usuario_de_prueba("Garza")
        admitir(nutria, jarama, es_base=True)
        admitir(nutria, henares)
        admitir(garza, henares, es_base=True)
        self.abrir("/organizaciones/miembros/")
        pagina = self.pagina
        self.assertIn("opacity-60", pagina.locator("tr", has_text="Nutria").get_attribute("class"))
        pagina.get_by_label("Marcar a Nutria", exact=False).check()
        pagina.get_by_label("Marcar a Garza", exact=False).check()
        operacion = pagina.get_by_label("Con las filas marcadas:")
        self.assertNotIn("Admin del grupo", operacion.inner_text())
        operacion.select_option(label="Sacar del grupo")
        pagina.once("dialog", lambda dialogo: dialogo.accept())
        pagina.get_by_role("button", name="Aplicar a las marcadas").click()
        pagina.get_by_text("Hecho con 2 filas.").wait_for()
        self.assertEqual(list(Pertenencia.objects.filter(grupo=henares).values_list("usuario__alias", flat=True)), [self.usuario.alias])
        self.assertEqual(self.errores, [])
