"""
Pruebas del módulo «proximamente»: las herramientas pendientes salen en el menú, dicen que aún están vacías
y qué harán, y las de administrar solo las ve quien administra. (Ya no queda ninguna de lo propio: las
conversaciones con grupos y con personas se hicieron en [A-56].)
"""

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from proximamente.apps import PENDIENTES


class PruebasDeProximamente(PruebaDePantalla):
    """Las herramientas pendientes, como persona cualquiera y como superadmin."""

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
