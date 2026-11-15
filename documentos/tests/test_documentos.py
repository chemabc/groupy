"""
Pruebas de los documentos: la autoría de cada párrafo, no pisar el trabajo de otra persona, el acta desde
su orden del día, quién escribe y quién comenta, y que al aprobar un acta sus acuerdos llegan al registro
de decisiones (se mira con apps.get_model, sin importar el módulo «decisiones»).

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares). Lince y Nutria están en GRU Henares; Erizo, en otra organización.
"""

from django.apps import apps
from django.core.exceptions import ValidationError

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from documentos import servicios
from documentos.models import CambioDeDocumento, Documento
from grupos.servicios import admitir, crear_grupo, crear_organizacion


class PruebasDeAutoria(PruebaDePantalla):
    """El cálculo de quién ha contribuido a cada párrafo (sin base de datos)."""

    # Lo que no cambia conserva sus alias; lo cambiado pone al final a quien cambia; lo nuevo, solo a quien
    # escribe.
    def test_calcular(self):
        antes = ["Uno", "Dos", "Tres"]
        despues = ["Uno", "Dos cambiado", "Tres", "Cuatro"]
        autorias, resumen = servicios.calcular_autorias(antes, despues, [["Lince"], ["Lince", "Nutria"], ["Nutria"]], "Garza")
        self.assertEqual(autorias, [["Lince"], ["Lince", "Nutria", "Garza"], ["Nutria"], ["Garza"]])
        self.assertIn("1 cambiado(s)", resumen)
        self.assertIn("1 nuevo(s)", resumen)


class PruebasDeDocumentos(PruebaDePantalla):
    """Crear, escribir, comentar y aprobar, como Lince."""

    # Crea la estructura.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.ebro, cls.gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.lince = crear_usuario_de_prueba("Lince")
        cls.nutria = crear_usuario_de_prueba("Nutria")
        cls.erizo = crear_usuario_de_prueba("Erizo")
        admitir(cls.lince, cls.henares)
        admitir(cls.nutria, cls.henares)
        admitir(cls.erizo, cls.gru_ebro)
        cls.usuario = cls.lince

    # Un orden del día de GRU Henares, de Lince, que ve todo el grupo.
    def odd(self):
        return servicios.crear(self.lince, Documento.ODD, "Orden del día de la asamblea", grupo=self.henares, visibilidad="grupo:0")

    # Al crearlo, Lince tiene la redacción, el texto de partida y una línea en el registro.
    def test_crear(self):
        odd = self.odd()
        self.assertTrue(servicios.puede_escribir(self.lince, odd))
        self.assertFalse(servicios.puede_escribir(self.nutria, odd))
        self.assertIn("Ruegos y preguntas", odd.texto)
        self.assertEqual(CambioDeDocumento.objects.filter(documento=odd).count(), 1)

    # Si otra persona ha guardado desde que se abrió, no se pisa.
    def test_no_pisar(self):
        odd = self.odd()
        servicios.guardar(self.lince, odd, odd.titulo, "Primero", odd.version)
        with self.assertRaises(ValidationError):
            servicios.guardar(self.lince, odd, odd.titulo, "Segundo", odd.version - 1)

    # El acta sale del orden del día con sus apartados fijos; al aprobarla, cada acuerdo llega al registro
    # de decisiones y ya no se puede escribir.
    def test_acta_y_acuerdos(self):
        odd = self.odd()
        acta = servicios.acta_desde(self.lince, odd)
        self.assertEqual(acta.origen, odd)
        self.assertIn(servicios.ACUERDOS, acta.texto)
        texto = acta.texto.replace("- [consenso] \n", "- [consenso] Pintar el local\n- [votación 12-3-1] Comprar una furgoneta\n")
        servicios.guardar(self.lince, acta, acta.titulo, texto, acta.version)
        acta.refresh_from_db()
        self.assertEqual(servicios.acuerdos(acta), [("Pintar el local", "consenso", ""), ("Comprar una furgoneta", "votacion", "12-3-1")])
        servicios.aprobar(self.lince, acta)
        Decision = apps.get_model("decisiones", "Decision")
        self.assertEqual(set(Decision.objects.values_list("texto", "forma")), {("Pintar el local", "consenso"), ("Comprar una furgoneta", "votacion")})
        self.assertFalse(servicios.puede_escribir(self.lince, acta))

    # Nutria (del grupo) lo lee y lo comenta, pero no puede escribirlo; Erizo no lo ve.
    def test_quien(self):
        odd = self.odd()
        self.client.force_login(self.nutria)
        self.client.post(f"/documentos/{odd.pk}/", {"accion": "comentar", "texto": "Falta el punto del huerto"})
        self.assertContains(self.client.get(f"/documentos/{odd.pk}/"), "Falta el punto del huerto")
        self.assertEqual(self.client.get(f"/documentos/{odd.pk}/escribir/").status_code, 403)
        self.client.force_login(self.erizo)
        self.assertEqual(self.client.get(f"/documentos/{odd.pk}/").status_code, 403)

    # Lince da la redacción a Nutria (como mucho dos personas).
    def test_dar_redaccion(self):
        odd = self.odd()
        self.client.post(f"/documentos/{odd.pk}/", {"accion": "dar", "alias": "Nutria"})
        self.assertTrue(servicios.puede_escribir(self.nutria, odd))

    # La ficha muestra quién ha escrito cada párrafo, y las pantallas cuestan lo mismo con más documentos y
    # cambios.
    def test_pantallas(self):
        odd = self.odd()
        respuesta = self.client.get(f"/documentos/{odd.pk}/")
        self.assertContains(respuesta, "(Lince)")

        # Un documento y un cambio más.
        def mas():
            otro = self.odd()
            servicios.guardar(self.lince, odd, odd.titulo, odd.texto + f"\n\nPunto {otro.pk}", Documento.objects.get(pk=odd.pk).version)

        self.comprobar_consultas("/documentos/", 2, mas)
        self.comprobar_consultas(f"/documentos/{odd.pk}/", 8, mas)
