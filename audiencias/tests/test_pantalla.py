"""
Pruebas de «Configuración → Visibilidad»: número de consultas, quién ve qué organización y que guardar
cambia lo que se puede elegir al publicar.
"""

from django.core.exceptions import ValidationError

from audiencias.models import ConfiguracionDeVisibilidad
from audiencias.servicios import audiencia_para
from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from grupos.servicios import admitir, crear_grupo, crear_organizacion, nombrar_admin_de_organizacion


class PruebasDeLaVisibilidad(PruebaDePantalla):
    """ORG Tajo (con su admin Zorro, que inicia sesión) y ORG Ebro."""

    # Crea las dos organizaciones y el admin de ORG Tajo.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.ebro, _ = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.usuario = crear_usuario_de_prueba("Zorro")
        admitir(cls.usuario, cls.general)
        nombrar_admin_de_organizacion(cls.usuario, cls.tajo)

    # Cuesta lo mismo con una organización que con varias (como superadmin, que las ve todas).
    def test_consultas(self):
        self.comprobar_consultas("/configuracion/visibilidad/", 3, None)
        self.client.force_login(crear_usuario_de_prueba("superadmin", es_superadmin=True))

        # Una organización más, con su configuración guardada.
        def mas():
            organizacion, _grupo = crear_organizacion(f"ORG {ConfiguracionDeVisibilidad.objects.count()}", "GRU Nuevo")
            ConfiguracionDeVisibilidad.objects.create(organizacion=organizacion)

        self.comprobar_consultas("/configuracion/visibilidad/", 3, mas)

    # El admin ve solo la suya (por defecto, la más cerrada); no puede tocar la de otra.
    def test_solo_la_suya(self):
        respuesta = self.client.get("/configuracion/visibilidad/")
        self.assertContains(respuesta, "ORG Tajo")
        self.assertNotContains(respuesta, "ORG Ebro")
        self.assertContains(respuesta, "por defecto (la más cerrada)")
        datos = {"organizacion": self.ebro.pk, f"o{self.ebro.pk}-altura_maxima": 3}
        self.assertEqual(self.client.post("/configuracion/visibilidad/", datos).status_code, 403)

    # Guardar abre «toda la organización»; a partir de ahí se puede elegir al publicar.
    def test_guardar(self):
        with self.assertRaises(ValidationError):
            audiencia_para("organizacion", self.henares)
        prefijo = f"o{self.tajo.pk}"
        datos = {"organizacion": self.tajo.pk, f"{prefijo}-altura_maxima": 2, f"{prefijo}-permite_toda_la_organizacion": "on"}
        respuesta = self.client.post("/configuracion/visibilidad/", datos)
        self.assertRedirects(respuesta, f"/configuracion/visibilidad/#organizacion-{self.tajo.pk}", fetch_redirect_response=False)
        configuracion = ConfiguracionDeVisibilidad.objects.get(organizacion=self.tajo)
        self.assertEqual((configuracion.altura_maxima, configuracion.permite_toda_la_organizacion, configuracion.permite_publico), (2, True, False))
        # Se vuelve a leer el grupo: el de la prueba recuerda que su organización no tenía configuración.
        audiencia_para("organizacion", self.henares.__class__.objects.get(pk=self.henares.pk))
        self.assertContains(self.client.get("/configuracion/visibilidad/"), "toda la organización. No se permite lo público.")

    # Una persona sin admin no ve «Configuración» en el menú ni puede entrar.
    def test_sin_permiso(self):
        nutria = crear_usuario_de_prueba("Nutria")
        admitir(nutria, self.henares)
        self.client.force_login(nutria)
        self.assertNotContains(self.client.get("/"), 'data-codigo="tipologias.configuracion"')
        self.assertContains(self.client.get("/configuracion/visibilidad/"), "audiencias.configurar", status_code=403)
