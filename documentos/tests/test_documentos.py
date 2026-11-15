"""
Pruebas de los documentos: la autoría de cada párrafo, no pisar el trabajo de otra persona, el acta desde
su orden del día, quién escribe y quién comenta, y que al aprobar un acta sus acuerdos llegan al registro
de decisiones (se mira con apps.get_model, sin importar el módulo «decisiones»).

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares). Lince y Nutria están en GRU Henares; Erizo, en otra organización.
"""

from datetime import timedelta

from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils import timezone

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from documentos import servicios
from documentos.models import CambioDeDocumento, Documento, LimitesDeDocumento, VersionDeDocumento
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

    # En Typst, los títulos del texto de partida salen con «==» y los acuerdos del acta se leen igual.
    def test_formato_typst(self):
        odd = servicios.crear(self.lince, Documento.ODD, "Orden del día", grupo=self.henares, visibilidad="grupo:0", formato=Documento.TYPST)
        self.assertTrue(odd.texto.startswith("== Puntos"))
        acta = servicios.acta_desde(self.lince, odd)
        self.assertEqual(acta.formato, Documento.TYPST)
        self.assertIn(f"== {servicios.ACUERDOS}", acta.texto)
        acta = servicios.guardar(self.lince, acta, acta.titulo, acta.texto.replace("- [consenso] \n", "- [consenso] Huerto en el solar\n"), acta.version)
        self.assertEqual(servicios.acuerdos(acta)[0][0], "Huerto en el solar")
        self.assertContains(self.client.get(f"/documentos/{acta.pk}/"), "== Puntos")

    # Versiones: mientras se sigue escribiendo se pone al día la última; pasado un rato, otra; al aprobar,
    # otra. Se puede volver a una anterior (queda como una nueva) y su pantalla enseña lo que cambió.
    def test_versiones(self):
        odd = self.odd()
        odd = servicios.guardar(self.lince, odd, odd.titulo, "Uno", odd.version)
        odd = servicios.guardar(self.lince, odd, odd.titulo, "Uno y dos", odd.version)
        self.assertEqual(list(odd.versiones.values_list("numero", "texto", "motivo")), [(2, "Uno y dos", ""), (1, servicios.ODD_INICIAL, "creado")])
        VersionDeDocumento.objects.filter(documento=odd, numero=2).update(cerrada=timezone.now() - timedelta(minutes=servicios.VERSION_CADA + 1))
        odd = servicios.guardar(self.lince, odd, odd.titulo, "Tres", odd.version)
        self.assertEqual(odd.versiones.first().numero, 3)
        respuesta = self.client.get(f"/documentos/{odd.pk}/versiones/2/")
        self.assertContains(respuesta, "-Uno y dos")
        self.assertContains(respuesta, "+Tres")
        self.client.post(f"/documentos/{odd.pk}/versiones/2/", {"accion": "volver"})
        odd.refresh_from_db()
        self.assertEqual((odd.texto, odd.versiones.first().motivo), ("Uno y dos", "vuelta a la versión 2"))
        servicios.aprobar(self.lince, odd)
        self.assertEqual(odd.versiones.first().motivo, "aprobado")
        self.client.force_login(self.nutria)
        self.assertNotContains(self.client.get(f"/documentos/{odd.pk}/versiones/1/"), "Volver a esta versión")

        # Una versión más (no debe costar más consultas).
        def mas():
            ultima = odd.versiones.first()
            VersionDeDocumento.objects.create(documento=odd, numero=ultima.numero + 1, texto=f"Texto {ultima.numero}", autores=["Lince"], motivo="prueba")

        self.comprobar_consultas(f"/documentos/{odd.pk}/versiones/1/", 3, mas)

    # Cuántas personas tienen la redacción: de partida 10; el documento puede bajarlo (su administración).
    def test_maximo_de_redaccion(self):
        odd = self.odd()
        LimitesDeDocumento.objects.create(documento=odd, max_escritores=1)
        with self.assertRaises(ValidationError):
            servicios.dar_redaccion(self.lince, odd, self.nutria)
        self.assertEqual(servicios.limites_de(self.henares, odd)["max_escritores"], 1)
        self.assertEqual(servicios.limites_de(self.henares)["max_escritores"], 10)

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

        self.comprobar_consultas("/documentos/", 4, mas)
        self.comprobar_consultas(f"/documentos/{odd.pk}/", 12, mas)
