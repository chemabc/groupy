"""
Pruebas del módulo «etiquetas»: forma de las etiquetas, que cada organización vea solo las suyas y las
comunes, palabras relacionadas, etiquetar y buscar, fusionar y el campo de formulario.
"""

from django.core.exceptions import ValidationError
from django.test import TestCase

from base.contrato import Ancla
from base.pruebas import PruebaDePantalla, contratos_de_prueba, crear_usuario_de_prueba, modulo_falso
from etiquetas.formularios import CampoDeEtiquetas
from etiquetas.models import Etiqueta, EtiquetaDe
from etiquetas.servicios import buscar, comprobar_nombre, etiquetar, etiquetas_de, fusionar, obtener_o_crear, sugerir
from grupos.servicios import admitir, crear_organizacion

# Módulo de mentira con un ancla para etiquetar.
ALFA = modulo_falso("alfa", anclas=(Ancla("alfa.cosa", "auth.Group", "Una cosa de mentira"),))


class PruebasDeEtiquetas(TestCase):
    """Etiquetas de ORG Tajo, de ORG Ebro y comunes."""

    # Dos organizaciones; «huelga» común (con «paro» como relacionada) y «local nuevo» de Tajo.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, _ = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.ebro, _ = crear_organizacion("ORG Ebro", "GRU Ebro")
        Etiqueta.objects.create(nombre="huelga", relacionadas="paro, parón")
        Etiqueta.objects.create(organizacion=cls.tajo, nombre="local nuevo")

    # Añade el ancla de mentira al registro durante cada prueba.
    def setUp(self):
        contexto = contratos_de_prueba(ALFA)
        contexto.__enter__()
        self.addCleanup(contexto.__exit__, None, None, None)

    # De una a tres palabras, sin símbolos; se limpian espacios, comas y almohadillas.
    def test_forma(self):
        self.assertEqual(comprobar_nombre("  #Local   nuevo "), "Local nuevo")
        for malo in ["", "una dos tres cuatro", "a@b", "x" * 41]:
            with self.subTest(malo=malo), self.assertRaises(ValidationError):
                comprobar_nombre(malo)

    # Cada organización ve sus etiquetas y las comunes, nunca las de otra; las relacionadas también se buscan.
    def test_sugerencias(self):
        self.assertEqual([s["nombre"] for s in sugerir("lo", self.tajo)], ["local nuevo"])
        self.assertEqual(sugerir("lo", self.ebro), [])
        self.assertEqual(sugerir("par", self.ebro), [{"nombre": "huelga", "comun": True}])
        self.assertEqual(sugerir("HUEL", None), [{"nombre": "huelga", "comun": True}])

    # Al usarlas se crean las que faltan; si hay una común igual, se usa la común; sin repetir.
    def test_obtener_o_crear(self):
        etiquetas = obtener_o_crear(["Huelga", "Cuidados", "cuidados"], self.ebro)
        self.assertEqual([(e.nombre, e.organizacion_id) for e in etiquetas], [("huelga", None), ("Cuidados", self.ebro.pk)])

    # No se puede crear en una organización una etiqueta igual a una común (ni repetida).
    def test_repetidas(self):
        with self.assertRaisesMessage(ValidationError, "Ya hay una etiqueta «huelga» igual"):
            Etiqueta(organizacion=self.tajo, nombre="Huelga").full_clean()

    # Etiquetar pone exactamente esas etiquetas; buscar por una relacionada encuentra lo etiquetado.
    def test_etiquetar_y_buscar(self):
        etiquetar(("alfa.cosa", 7), ["huelga", "local nuevo"], self.tajo)
        etiquetar(("alfa.cosa", 7), ["huelga"], self.tajo)
        self.assertEqual(etiquetas_de(("alfa.cosa", 7)), ["huelga"])
        self.assertEqual(buscar("Paro", "alfa.cosa", self.tajo), {7})
        self.assertEqual(buscar("nada", "alfa.cosa", self.tajo), set())
        with self.assertRaisesMessage(ValidationError, "ningún módulo lo declara como ancla"):
            etiquetar(("alfa.nada", 1), ["huelga"], self.tajo)

    # Fusionar: lo etiquetado pasa a la que se queda, sin duplicar, y las otras son sus relacionadas.
    def test_fusionar(self):
        local, sede = obtener_o_crear(["local nuevo", "sede"], self.tajo)
        etiquetar(("alfa.cosa", 1), ["local nuevo", "sede"], self.tajo)
        etiquetar(("alfa.cosa", 2), ["sede"], self.tajo)
        fusionar(local, [sede])
        local.refresh_from_db()
        self.assertEqual(local.relacionadas, "sede")
        self.assertEqual(sorted(EtiquetaDe.objects.filter(etiqueta=local).values_list("ancla_id", flat=True)), [1, 2])
        self.assertFalse(Etiqueta.objects.filter(nombre="sede").exists())
        de_ebro = obtener_o_crear(["otra"], self.ebro)[0]
        with self.assertRaisesMessage(ValidationError, "es de otra organización"):
            fusionar(local, [de_ebro])

    # El campo de formulario limpia, quita repetidas y explica las que no sirven.
    def test_campo(self):
        campo = CampoDeEtiquetas(organizacion=self.tajo)
        self.assertEqual(campo.clean(["huelga", " Huelga ", "local  nuevo"]), ["huelga", "local nuevo"])
        self.assertIn(f"?organizacion={self.tajo.pk}", campo.widget.url_de_sugerencias)
        with self.assertRaisesMessage(ValidationError, "no sirve como etiqueta"):
            campo.clean(["una dos tres cuatro"])


class PruebasDeSugerenciasEnLaWeb(PruebaDePantalla):
    """La dirección de sugerencias solo da las etiquetas de una organización a quien está en ella."""

    # ORG Tajo con «local nuevo»; el usuario de la sesión no está en Tajo; Lince sí.
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        Etiqueta.objects.create(organizacion=cls.tajo, nombre="local nuevo")
        Etiqueta.objects.create(nombre="lote común")
        cls.lince = crear_usuario_de_prueba("Lince")
        admitir(cls.lince, cls.general)

    # Fuera de la organización, solo las comunes; dentro, también las suyas.
    def test_solo_quien_esta_dentro(self):
        direccion = f"/etiquetas/sugerencias/?q=lo&organizacion={self.tajo.pk}"
        self.assertEqual(self.client.get(direccion).json()["sugerencias"], [{"nombre": "lote común", "comun": True}])
        self.client.force_login(self.lince)
        nombres = [s["nombre"] for s in self.client.get(direccion).json()["sugerencias"]]
        self.assertEqual(nombres, ["local nuevo", "lote común"])
