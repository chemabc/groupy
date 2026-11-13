"""
Pruebas del módulo «mantenimiento»: solo lo ve el superadmin (menú y pantallas), los documentos se
convierten bien y cada pantalla cuesta pocas consultas.
"""

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from mantenimiento.documentos import DOCUMENTOS


class PruebasComoSuperadmin(PruebaDePantalla):
    """Recorre «Desarrollo y mantenimiento» como superadmin."""

    # El usuario de la sesión es superadmin.
    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario_de_prueba("Águila", es_superadmin=True)

    # El superadmin ve la sección en el menú.
    def test_menu(self):
        self.assertContains(self.client.get("/"), "Desarrollo y mantenimiento")

    # Cada documento se ve con una sola consulta (la del usuario): no hay listas que crezcan.
    def test_consultas(self):
        for nombre, _fichero, _titulo in DOCUMENTOS:
            with self.subTest(documento=nombre):
                self.comprobar_consultas(f"/mantenimiento/documentacion/{nombre}/", 1, None)
        self.comprobar_consultas("/mantenimiento/trastienda/", 1, None)

    # El diseño se convierte en HTML con tablas e índice, y sus enlaces a otros documentos llevan a sus
    # páginas.
    def test_conversion(self):
        respuesta = self.client.get("/mantenimiento/documentacion/")
        self.assertContains(respuesta, "<table>")
        self.assertContains(respuesta, 'class="toc"')
        self.assertContains(respuesta, 'href="/mantenimiento/documentacion/registro-y-validacion/"')
        self.assertNotContains(respuesta, 'href="registro-y-validacion.md"')

    # Un documento que no está en la lista no existe (aunque haya un fichero con ese nombre).
    def test_documento_que_no_existe(self):
        self.assertEqual(self.client.get("/mantenimiento/documentacion/secreto/").status_code, 404)

    # La entrada a la trastienda es un enlace normal (sin htmx), que carga el panel entero.
    def test_boton_de_la_trastienda(self):
        self.assertContains(self.client.get("/mantenimiento/trastienda/"), 'href="/trastienda/" hx-boost="false"')


class PruebasComoUsuario(PruebaDePantalla):
    """Una persona sin el permiso no ve la sección ni puede entrar."""

    # No sale en su menú.
    def test_menu(self):
        self.assertNotContains(self.client.get("/"), "Desarrollo y mantenimiento")

    # Si escribe la dirección, sale la explicación de lo que falta.
    def test_sin_permiso(self):
        respuesta = self.client.get("/mantenimiento/documentacion/")
        self.assertContains(respuesta, "hace falta el permiso «mantenimiento.ver»", status_code=403)
        self.assertContains(respuesta, "De momento solo lo tiene el superadmin.", status_code=403)
