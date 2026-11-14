"""
Pruebas de «Administrar → Mi organización → Etiquetas»: número de consultas, de quién ve las etiquetas cada cual, y
crear, renombrar, fusionar y borrar.
"""

from base.contrato import Ancla
from base.pruebas import PruebaDePantalla, contratos_de_prueba, crear_usuario_de_prueba, modulo_falso
from etiquetas.models import Etiqueta, EtiquetaDe
from etiquetas.servicios import crear_etiqueta, etiquetar
from grupos.servicios import admitir, crear_organizacion, nombrar_admin_de_organizacion

# Módulo de mentira con un ancla, para poder etiquetar algo.
ALFA = modulo_falso("alfa", anclas=(Ancla("alfa.cosa", "auth.Group", "Una cosa de mentira"),))


class PruebasDeEtiquetasEnPantalla(PruebaDePantalla):
    """Zorro, admin de ORG Tajo, con la sesión iniciada; ORG Ebro aparte."""

    # Crea las organizaciones, el admin y unas etiquetas.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.ebro, _ = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.usuario = crear_usuario_de_prueba("Zorro")
        admitir(cls.usuario, cls.general)
        nombrar_admin_de_organizacion(cls.usuario, cls.tajo)
        cls.huelga = crear_etiqueta("Huelga", cls.tajo, "paro")
        crear_etiqueta("Riego", cls.ebro)
        crear_etiqueta("Asamblea", None)

    # Cuesta lo mismo con pocas etiquetas que con muchas.
    def test_consultas(self):
        self.comprobar_consultas(
            "/etiquetas/", 3, lambda: crear_etiqueta(f"Tema {Etiqueta.objects.count()}", self.tajo, "uno, dos")
        )

    # El admin ve las de su organización (no las de otra ni las comunes, que son del superadmin).
    def test_de_quien(self):
        respuesta = self.client.get("/etiquetas/")
        self.assertContains(respuesta, "Huelga")
        self.assertNotContains(respuesta, "Riego")
        self.assertNotContains(respuesta, "Comunes")
        self.assertEqual(self.client.get(f"/etiquetas/?de={self.ebro.pk}").status_code, 403)
        self.assertEqual(self.client.get("/etiquetas/?de=comunes").status_code, 403)
        self.client.force_login(crear_usuario_de_prueba("superadmin", es_superadmin=True))
        self.assertContains(self.client.get("/etiquetas/?de=comunes"), "Asamblea")

    # Crear (en forma fija), no repetir, renombrar con relacionadas, buscar por una relacionada y borrar.
    def test_crear_renombrar_borrar(self):
        url = f"/etiquetas/?de={self.tajo.pk}"
        datos = {"accion": "crear", "de": self.tajo.pk, "nombre": "LOCAL nuevo", "relacionadas": ""}
        self.assertRedirects(self.client.post("/etiquetas/", datos), url)
        local = Etiqueta.objects.get(nombre="Local nuevo")
        self.assertContains(self.client.post("/etiquetas/", {**datos, "nombre": "local NUEVO"}), "Ya hay una etiqueta")
        datos = {"accion": "editar", "de": self.tajo.pk, "etiqueta": local.pk, "nombre": "Local", "relacionadas": "sede, Sede, centro social"}
        self.client.post("/etiquetas/", datos)
        local.refresh_from_db()
        self.assertEqual((local.nombre, local.relacionadas), ("Local", "Sede, Centro social"))
        # «Huelga» sale también en la ayuda: se mira la celda de la tabla.
        self.assertContains(self.client.get(f"{url}&q=centro"), 'font-medium">Local</td>')
        self.assertNotContains(self.client.get(f"{url}&q=centro"), 'font-medium">Huelga</td>')
        self.client.post("/etiquetas/", {"accion": "borrar", "de": self.tajo.pk, "etiqueta": local.pk})
        self.assertFalse(Etiqueta.objects.filter(pk=local.pk).exists())

    # Fusionar: lo etiquetado pasa a la que se queda y la otra queda como relacionada.
    def test_fusionar(self):
        with contratos_de_prueba(ALFA):
            etiquetar(("alfa.cosa", 1), ["Huelgas"], self.tajo)
        huelgas = Etiqueta.objects.get(nombre="Huelgas")
        datos = {"accion": "fusionar", "de": self.tajo.pk, "etiquetas": [self.huelga.pk, huelgas.pk], "destino": self.huelga.pk}
        self.client.post("/etiquetas/", datos)
        self.assertFalse(Etiqueta.objects.filter(pk=huelgas.pk).exists())
        self.assertEqual(EtiquetaDe.objects.get().etiqueta, self.huelga)
        self.huelga.refresh_from_db()
        self.assertEqual(self.huelga.relacionadas, "Paro, Huelgas")
        respuesta = self.client.post("/etiquetas/", {**datos, "etiquetas": [self.huelga.pk]})
        self.assertContains(respuesta, "marca al menos dos etiquetas")
