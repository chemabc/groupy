"""
Pruebas de las consultas: preparar las preguntas antes de abrirse, una persona un voto (y cambiarlo solo si
se permite), el voto secreto (la papeleta no dice de quién es), cuándo se ven los resultados, el cierre (el
resultado llega al registro de decisiones, mirado con apps.get_model) y el número de consultas.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares). Lince es admin de GRU Henares; Nutria y Garza, miembros; Erizo, de
otra organización.
"""

from datetime import timedelta

from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils import timezone

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from consultas import servicios
from consultas.models import Consulta, Papeleta, Participacion, Pregunta
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion


class PruebasDeConsultas(PruebaDePantalla):
    """Una consulta de Lince a GRU Henares, con una pregunta de respuesta única."""

    # Crea la estructura.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.ebro, cls.gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.lince, cls.nutria, cls.garza, cls.erizo = (crear_usuario_de_prueba(a) for a in ("Lince", "Nutria", "Garza", "Erizo"))
        admitir(cls.lince, cls.henares, rol=Pertenencia.ADMIN_GRUPO)
        admitir(cls.nutria, cls.henares, es_base=True)
        admitir(cls.garza, cls.henares)
        admitir(cls.erizo, cls.gru_ebro)
        cls.usuario = cls.nutria

    # Crea la consulta (aún sin abrir), le pone la pregunta y la abre (mueve sus fechas).
    def setUp(self):
        super().setUp()
        ahora = timezone.now()
        datos = {"titulo": "¿Qué día hacemos la asamblea?", "descripcion": "", "abre": ahora + timedelta(hours=1), "cierra": ahora + timedelta(days=7),
                 "resultados": Consulta.AL_CERRAR, "publicar_el": None, "cambiar_voto": False}
        self.consulta = servicios.crear(self.lince, self.henares, datos, "grupo:0", "grupo:0")
        self.pregunta = servicios.anadir_pregunta(self.lince, self.consulta, "Día", Pregunta.UNICA, respuestas=["Martes", "Jueves"])
        self.martes, self.jueves = self.pregunta.respuestas.all()
        Consulta.objects.filter(pk=self.consulta.pk).update(abre=ahora - timedelta(minutes=1))
        self.consulta.refresh_from_db()

    # Vota una persona por una respuesta.
    def votar(self, persona, respuesta):
        servicios.votar(persona, self.consulta, {str(self.pregunta.pk): [respuesta.pk]})

    # Una vez abierta, ya no se le cambian las preguntas.
    def test_preparar(self):
        with self.assertRaises(ValidationError):
            servicios.anadir_pregunta(self.lince, self.consulta, "Hora", Pregunta.ABIERTA)

    # Una persona, un voto; la papeleta no dice de quién es. Erizo no vota.
    def test_un_voto_secreto(self):
        self.votar(self.nutria, self.martes)
        with self.assertRaises(ValidationError):
            self.votar(self.nutria, self.jueves)
        with self.assertRaises(ValidationError):
            self.votar(self.erizo, self.jueves)
        papeleta = Papeleta.objects.get()
        self.assertEqual(papeleta.respuestas, {str(self.pregunta.pk): [self.martes.pk]})
        self.assertNotIn("usuario", [campo.name for campo in Papeleta._meta.get_fields()])
        self.assertEqual(Participacion.objects.get().usuario, self.nutria)

    # Si la consulta lo permite, el voto nuevo sustituye al anterior (sigue habiendo una papeleta).
    def test_cambiar_el_voto(self):
        Consulta.objects.filter(pk=self.consulta.pk).update(cambiar_voto=True)
        self.consulta.refresh_from_db()
        self.votar(self.nutria, self.martes)
        self.votar(self.nutria, self.jueves)
        self.assertEqual(Papeleta.objects.get().respuestas, {str(self.pregunta.pk): [self.jueves.pk]})

    # Los resultados se ven al cerrar; entonces la consulta se cierra sola al abrirla y su resultado llega
    # al registro de decisiones.
    def test_resultados_y_cierre(self):
        self.votar(self.nutria, self.jueves)
        self.votar(self.garza, self.jueves)
        self.assertFalse(servicios.ve_resultados(self.nutria, self.consulta))
        Consulta.objects.filter(pk=self.consulta.pk).update(cierra=timezone.now() - timedelta(minutes=1))
        respuesta = self.client.get(f"/consultas/{self.consulta.pk}/")
        self.assertContains(respuesta, "Resultados · 2 votos")
        Decision = apps.get_model("decisiones", "Decision")
        self.assertIn("«Jueves» (2 de 2)", Decision.objects.get().texto)

    # Votar desde la ficha y las pantallas, que cuestan lo mismo con más votos.
    def test_pantallas(self):
        self.client.post(f"/consultas/{self.consulta.pk}/", {"accion": "votar", f"p{self.pregunta.pk}": self.martes.pk})
        self.assertTrue(servicios.ha_votado(self.nutria, self.consulta))

        # Una persona más que vota.
        def mas():
            persona = crear_usuario_de_prueba(f"Persona {Papeleta.objects.count()}")
            admitir(persona, self.henares)
            self.votar(persona, self.jueves)

        self.comprobar_consultas(f"/consultas/{self.consulta.pk}/", 5, mas)
        self.comprobar_consultas("/consultas/", 3, mas)
