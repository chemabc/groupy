"""
Pruebas del módulo «proximamente»: las herramientas pendientes salen en el menú, dicen que aún están vacías
y qué harán, y las de administrar solo las ve quien administra.
"""

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from proximamente.apps import PENDIENTES


class PruebasDeProximamente(PruebaDePantalla):
    """Las herramientas pendientes, como persona cualquiera y como superadmin."""

    # Una de lo propio: sale en el menú, dice que está vacía y qué hará, con una sola consulta.
    def test_herramienta_de_todos(self):
        respuesta = self.comprobar_consultas("/proximamente/con-grupos/", 1, None)
        self.assertContains(respuesta, "Aún está vacío")
        self.assertContains(respuesta, "Conversaciones con un grupo entero")
        self.assertContains(respuesta, 'data-codigo="proximamente.participacion"')

    # Una de administrar: una persona cualquiera ni la ve en el menú ni puede abrirla; el superadmin sí.
    def test_herramienta_de_administrar(self):
        self.assertNotContains(self.client.get("/"), 'data-codigo="proximamente.moderacion"')
        self.assertEqual(self.client.get("/proximamente/moderacion/").status_code, 403)
        self.client.force_login(crear_usuario_de_prueba("Jefa", es_superadmin=True))
        self.assertContains(self.client.get("/proximamente/moderacion/"), "Aún está vacío")

    # Todas se abren (como superadmin).
    def test_todas(self):
        self.client.force_login(crear_usuario_de_prueba("Jefa", es_superadmin=True))
        for pendiente in PENDIENTES:
            with self.subTest(pendiente=pendiente.clave):
                self.assertContains(self.client.get(f"/proximamente/{pendiente.clave.replace('_', '-')}/"), pendiente.descripcion)
