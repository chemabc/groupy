"""
Pruebas del módulo «ayuda»: el menú con sus tres subsecciones, los documentos convertidos en páginas
(con índice plegable, tablas y enlaces entre ellos), la versión para el panel de ayuda, el número de
consultas y quién ve qué (en desarrollo, todo el mundo; en producción, «How to?» todo el mundo y el resto
solo el superadmin).
"""

from django.test import override_settings

from ayuda.documentos import DOCUMENTOS
from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba

# Cabeceras que manda htmx al pedir una página para el panel de ayuda (ver panelDeAyuda en interfaz.js).
CABECERAS_DEL_PANEL = {"HX-Request": "true", "HX-Target": "panel-de-ayuda-contenido"}


class PruebasComoSuperadmin(PruebaDePantalla):
    """Recorre «Ayuda» como superadmin, que lo ve todo."""

    # El usuario de la sesión es superadmin.
    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario_de_prueba("Águila", es_superadmin=True)

    # El menú tiene «Ayuda» con sus tres subsecciones; en «Documentación de la plataforma», arriba, sus
    # cuatro documentos. El botón «?» rojo ofrece las tres subsecciones.
    def test_menu(self):
        respuesta = self.client.get("/ayuda/tutorial/")
        for texto in ["How to?", "Documentación de la plataforma", "Guía de desarrollo", "Arquitectura", "Arranque y tests", "Registro y validación"]:
            self.assertContains(respuesta, texto)
        self.assertContains(respuesta, 'aria-current="page">Tutorial</a>')
        self.assertEqual(respuesta.context["interfaz"]["codigos"], ["ayuda.ayuda", "ayuda.plataforma"])
        lateral = [subseccion.codigo for subseccion in respuesta.context["interfaz"]["ayuda_lateral"]]
        self.assertEqual(lateral, ["ayuda.como_se_hace", "ayuda.plataforma", "ayuda.guias"])

    # Cada documento cuesta una consulta (la del usuario de la sesión) y no tiene listas que crezcan.
    def test_consultas(self):
        for documento in DOCUMENTOS:
            with self.subTest(documento=documento.clave):
                self.comprobar_consultas(f"/ayuda/{documento.clave}/", 1, None)

    # Los documentos se convierten con tablas e índice (plegable), y sus enlaces llevan a sus páginas;
    # cada uno es una pestaña del menú superior y recuerda sus casillas por su propia dirección.
    def test_documentos(self):
        respuesta = self.client.get("/ayuda/diseno/")
        self.assertContains(respuesta, "<table>")
        self.assertContains(respuesta, 'class="toc"')
        self.assertContains(respuesta, 'title="Plegar o desplegar el índice"')
        self.assertContains(respuesta, 'href="/ayuda/registro-y-validacion/"')
        self.assertContains(respuesta, 'aria-current="page">Diseño y decisiones</a>')
        self.assertContains(respuesta, 'data-direccion="/ayuda/diseno/"')

    # Para el panel de ayuda: sin título de pestaña ni zona central, con sus pestañas y «Abrir en
    # grande», y con las mismas consultas.
    def test_en_el_panel(self):
        self.client.get("/ayuda/tutorial/", headers=CABECERAS_DEL_PANEL)
        with self.assertNumQueries(1):
            respuesta = self.client.get("/ayuda/tutorial/", headers=CABECERAS_DEL_PANEL)
        self.assertNotContains(respuesta, "<title>")
        self.assertNotContains(respuesta, 'id="zona"')
        self.assertContains(respuesta, "Abrir en grande")
        self.assertContains(respuesta, 'aria-current="page">Tutorial</a>')
        self.assertContains(respuesta, 'class="toc"')

    # El HTML escrito a mano en un documento se ve como texto: el «<script>» que menciona el tutorial no
    # llega a la página como etiqueta (se ejecutaría).
    def test_html_escapado(self):
        respuesta = self.client.get("/ayuda/tutorial/")
        self.assertContains(respuesta, "«&lt;script&gt;»")
        self.assertNotContains(respuesta, "«<script>»")

    # La miniayuda «?» de la sección (ventana emergente) lleva su ejemplo aparte.
    def test_miniayuda_con_ejemplo(self):
        respuesta = self.client.get("/ayuda/como-se-hace/")
        self.assertContains(respuesta, 'role="dialog"')
        self.assertContains(respuesta, ">Ejemplo</p>")
        self.assertContains(respuesta, "No sabes cómo convocar una reunión")

    # Un documento que no está en la lista no existe.
    def test_documento_desconocido(self):
        self.assertEqual(self.client.get("/ayuda/nada/").status_code, 404)


@override_settings(GUIAS_DE_DESARROLLO_PARA_TODOS=False)
class PruebasEnProduccion(PruebaDePantalla):
    """En producción, una persona cualquiera solo ve «How to?»."""

    # El menú y el botón «?» rojo solo ofrecen «How to?»; la documentación explica qué permiso falta.
    def test_solo_how_to(self):
        respuesta = self.comprobar_consultas("/ayuda/como-se-hace/", 1, None)
        lateral = [subseccion.codigo for subseccion in respuesta.context["interfaz"]["ayuda_lateral"]]
        self.assertEqual(lateral, ["ayuda.como_se_hace"])
        self.assertTrue({"ayuda.plataforma", "ayuda.guias"} <= respuesta.context["interfaz"]["ocultas"])
        for direccion in ["/ayuda/tutorial/", "/ayuda/comprobaciones/"]:
            with self.subTest(direccion=direccion):
                self.assertContains(self.client.get(direccion), "hace falta el permiso «ayuda.ver_documentacion»", status_code=403)


@override_settings(GUIAS_DE_DESARROLLO_PARA_TODOS=True)
class PruebasEnDesarrollo(PruebaDePantalla):
    """En desarrollo, cualquiera ve toda la ayuda, pero no «Desarrollo y mantenimiento»."""

    # Las tres subsecciones a la vista; las casillas y los diagramas, en sus documentos.
    def test_todo_abierto(self):
        respuesta = self.client.get("/ayuda/comprobaciones/")
        lateral = [subseccion.codigo for subseccion in respuesta.context["interfaz"]["ayuda_lateral"]]
        self.assertEqual(lateral, ["ayuda.como_se_hace", "ayuda.plataforma", "ayuda.guias"])
        self.assertContains(respuesta, 'data-casilla disabled aria-label="Hecho"')
        self.assertNotContains(respuesta, 'data-codigo="mantenimiento.desarrollo"')
        self.assertContains(self.client.get("/ayuda/arquitectura/"), 'class="language-mermaid"')
