"""
Pruebas de las webs en un navegador de verdad (ver base/pruebas_navegador.py): el botón «🌐 Webs» de la
cabecera abre el visor como página entera (sin el menú de la izquierda), los desplegables de la barra de
camino llevan a otro grupo, y la pestaña «Jerarquía» dibuja el grafo (isla «documento», Mermaid) con sus
nodos que se pulsan.
"""

from base.pruebas import crear_usuario_de_prueba
from base.pruebas_navegador import PruebaEnElNavegador
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion
from publico import servicios


class PruebasDeLasWebsEnElNavegador(PruebaEnElNavegador):
    """El usuario de la prueba está en GRU Henares (su asamblea base); Lince lo administra."""

    # GRU Tajo ⊃ GRU Henares y GRU Jarama, cada uno con una página publicada; el usuario de la prueba está en
    # los dos subgrupos (su base, GRU Henares). Devuelve (henares, jarama).
    def preparar(self):
        tajo, general = crear_organizacion("ORG Tajo", "GRU Tajo")
        henares = crear_grupo(tajo, "GRU Henares", padre=general)
        jarama = crear_grupo(tajo, "GRU Jarama", padre=general)
        lince = crear_usuario_de_prueba("Lince", es_superadmin=True)
        admitir(self.usuario, henares, es_base=True)
        admitir(self.usuario, jarama)
        for grupo, titulo, texto in ((henares, "Calendario de la huerta", "## Habas en noviembre"), (jarama, "Asambleas de zona", "## El primer sábado")):
            pagina = servicios.crear(lince, f"g{grupo.pk}", titulo)
            servicios.guardar(lince, pagina, texto, pagina.version)
            servicios.publicar(lince, pagina)
        admitir(lince, henares, rol=Pertenencia.ADMIN_GRUPO)
        return henares, jarama

    # «🌐 Webs» abre la web de la asamblea base, sin el menú de la izquierda; el desplegable de GRU Henares
    # lleva a su hermano GRU Jarama.
    def test_visor_y_desplegables(self):
        self.preparar()
        self.abrir("/")
        self.pagina.locator('a[data-cabecera="publico.webs"]').click()
        self.pagina.get_by_text("Habas en noviembre").wait_for()
        self.assertEqual(self.pagina.locator('nav[aria-label="Secciones"]').count(), 0)
        self.pagina.get_by_text("GRU Henares ▾").click()
        with self.pagina.expect_navigation():
            self.pagina.get_by_role("link", name="GRU Jarama").click()
        self.pagina.get_by_text("El primer sábado").wait_for()
        self.assertEqual(self.errores, [])

    # «Jerarquía» dibuja el grafo con los dos grupos con web; al pulsar GRU Jarama se va a su web.
    def test_jerarquia(self):
        _henares, jarama = self.preparar()
        self.abrir("/webs/jerarquia/")
        nodo = self.pagina.locator("g.node", has_text="GRU Jarama")
        nodo.wait_for()
        self.assertEqual(self.pagina.locator("g.node", has_text="GRU Henares").count(), 1)
        with self.pagina.expect_navigation():
            nodo.click()
        self.assertTrue(self.pagina.url.endswith(f"/webs/grupo/{jarama.pk}/"))
        self.assertEqual(self.errores, [])
