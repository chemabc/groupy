"""
Pruebas de las consultas: preparar las preguntas antes de abrirse, una persona un voto (y cambiarlo solo si
se permite), el voto secreto (la papeleta no dice de quién es), cuándo se ven los resultados, el cierre (el
resultado llega al registro de decisiones, mirado con apps.get_model) y el número de consultas.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares). Lince es admin de GRU Henares; Nutria y Garza, miembros; Erizo, de
otra organización.
"""

import uuid

from datetime import timedelta

from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils import timezone

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from consultas import servicios, urna
from consultas.models import Consulta, Papeleta, Participacion, Pregunta
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion
from solicitudes.models import Solicitud


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
        urna.vaciar_todas()
        self.addCleanup(urna.vaciar_todas)
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

    # Un miembro que no administra la propone: solo la ve él, pide apoyos (las preguntas ya no cambian) y, al
    # aceptarse la solicitud con su apertura ya pasada, se abre en ese momento y dura lo mismo.
    def test_propuesta_de_un_miembro(self):
        ahora = timezone.now()
        datos = {"titulo": "¿Pintamos el local?", "descripcion": "", "abre": ahora + timedelta(hours=1), "cierra": ahora + timedelta(days=2),
                 "resultados": Consulta.AL_CERRAR, "publicar_el": None, "cambiar_voto": False}
        propuesta = servicios.crear(self.garza, self.henares, datos, "grupo:0", "grupo:0")
        self.assertEqual(propuesta.estado, Consulta.PROPUESTA)
        self.assertFalse(servicios.ve(self.nutria, propuesta))
        with self.assertRaises(ValidationError):
            servicios.pedir_apoyos(self.garza, propuesta)  # sin preguntas
        servicios.anadir_pregunta(self.garza, propuesta, "¿Sí?", Pregunta.UNICA, respuestas=["Sí", "No"])
        servicios.pedir_apoyos(self.garza, propuesta)
        with self.assertRaises(ValidationError):
            servicios.anadir_pregunta(self.garza, propuesta, "¿Color?", Pregunta.ABIERTA)
        solicitud = Solicitud.objects.get(tipo="consultas.abrir")
        self.assertIn("¿Sí? (Sí / No)", solicitud.descripcion)
        Consulta.objects.filter(pk=propuesta.pk).update(abre=ahora - timedelta(hours=3), cierra=ahora + timedelta(days=1))
        servicios.aceptar(solicitud)
        propuesta.refresh_from_db()
        self.assertEqual(propuesta.estado, Consulta.ACEPTADA)
        self.assertTrue(servicios.abierta(propuesta) and servicios.ve(self.nutria, propuesta))
        self.assertGreater(propuesta.cierra, ahora + timedelta(days=1, hours=2))

    # Una persona, un voto; la papeleta no dice de quién es. Erizo no vota.
    def test_un_voto_secreto(self):
        self.votar(self.nutria, self.martes)
        with self.assertRaises(ValidationError):
            self.votar(self.nutria, self.jueves)
        with self.assertRaises(ValidationError):
            self.votar(self.erizo, self.jueves)
        # La papeleta aún no está en la base: espera en la urna, sin nombre.
        self.assertEqual(Papeleta.objects.count(), 0)
        self.assertEqual(urna.mirar(self.consulta.pk)[0]["respuestas"], {str(self.pregunta.pk): [self.martes.pk]})
        servicios.vaciar_urna(self.consulta)
        papeleta = Papeleta.objects.get()
        self.assertEqual(papeleta.respuestas, {str(self.pregunta.pk): [self.martes.pk]})
        self.assertIsNone(papeleta.usuario)
        self.assertEqual(Participacion.objects.get().usuario, self.nutria)

    # Las papeletas secretas se guardan en tandas de cinco, en desorden y con números al azar; hasta entonces
    # cuentan en los resultados igual.
    def test_tandas(self):
        personas = [crear_usuario_de_prueba(f"Votante {n}") for n in range(urna.TANDA)]
        for persona in personas:
            admitir(persona, self.henares)
        for persona in personas[:-1]:
            self.votar(persona, self.jueves)
        self.assertEqual(Papeleta.objects.count(), 0)
        self.assertEqual(servicios.resultados(self.consulta, [self.pregunta])["total"], urna.TANDA - 1)
        self.votar(personas[-1], self.martes)
        self.assertEqual(Papeleta.objects.count(), urna.TANDA)
        self.assertEqual(urna.mirar(self.consulta.pk), [])
        self.assertIsInstance(Papeleta.objects.first().pk, uuid.UUID)

    # Una consulta pública guarda quién vota cada papeleta y los resultados lo dicen; la ficha avisa.
    def test_voto_publico(self):
        Consulta.objects.filter(pk=self.consulta.pk).update(secreta=False, resultados=Consulta.EN_TIEMPO_REAL)
        self.consulta.refresh_from_db()
        self.votar(self.nutria, self.jueves)
        self.assertEqual(Papeleta.objects.get().usuario, self.nutria)
        filas = servicios.resultados(self.consulta, [self.pregunta])["preguntas"][0]["filas"]
        self.assertEqual(filas[1]["quienes"], ["Nutria"])
        self.assertContains(self.client.get(f"/consultas/{self.consulta.pk}/"), "Voto público")

    # Si la consulta lo permite, el voto nuevo sustituye al anterior (sigue habiendo una papeleta).
    def test_cambiar_el_voto(self):
        Consulta.objects.filter(pk=self.consulta.pk).update(cambiar_voto=True)
        self.consulta.refresh_from_db()
        self.votar(self.nutria, self.martes)
        servicios.vaciar_urna(self.consulta)
        self.votar(self.nutria, self.jueves)
        servicios.vaciar_urna(self.consulta)
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
            persona = crear_usuario_de_prueba(f"Persona {Participacion.objects.count()}")
            admitir(persona, self.henares)
            self.votar(persona, self.jueves)

        self.comprobar_consultas(f"/consultas/{self.consulta.pk}/", 6, mas)
        self.comprobar_consultas("/consultas/", 3, mas)
