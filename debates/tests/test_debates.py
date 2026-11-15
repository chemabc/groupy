"""
Pruebas de los debates: se proponen con una solicitud y se abren al aceptarse, los votos (uno por persona y
elemento, se quitan al repetirlos, ⭐ y ⛔ con justificación), las opciones nuevas que se abren con apoyos,
los límites, cerrar (la conclusión llega al registro de decisiones, mirado con apps.get_model) y el número
de consultas de la ficha.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares). Lince, Nutria y Garza en GRU Henares; Erizo, en otra organización.
"""

from django.apps import apps
from django.core.exceptions import ValidationError

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from debates import servicios
from debates.models import Debate, LimitesDeDebate, Opcion, Voto
from grupos.servicios import admitir, crear_grupo, crear_organizacion
from solicitudes.models import Solicitud


class PruebasDeDebates(PruebaDePantalla):
    """Un debate de Lince en GRU Henares, ya abierto."""

    # Crea la estructura.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.ebro, cls.gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.lince, cls.nutria, cls.garza, cls.erizo = (crear_usuario_de_prueba(a) for a in ("Lince", "Nutria", "Garza", "Erizo"))
        for persona in (cls.lince, cls.nutria, cls.garza):
            admitir(persona, cls.henares)
        admitir(cls.erizo, cls.gru_ebro)
        cls.usuario = cls.nutria

    # Propone el debate y lo abre como si su solicitud hubiera conseguido los apoyos.
    def setUp(self):
        super().setUp()
        self.debate = servicios.proponer(self.lince, "¿Dónde hacemos el huerto?", "", ["En el solar", "En la azotea"], grupo=self.henares)
        servicios.abrir(Solicitud.objects.get(tipo="debates.abrir"))
        self.debate.refresh_from_db()
        self.solar, self.azotea = self.debate.opciones.all()

    # Antes de abrirse, solo lo ve quien lo propone; al abrirse, todo el grupo, y Lince tiene la facilitación.
    def test_abrir(self):
        otro = servicios.proponer(self.nutria, "¿Cambiamos de día?", "", ["Martes", "Jueves"], grupo=self.henares)
        self.assertEqual(otro.estado, Debate.PENDIENTE)
        self.assertFalse(servicios.ve(self.garza, otro))
        self.assertTrue(servicios.ve(self.garza, self.debate))
        self.assertFalse(servicios.ve(self.erizo, self.debate))
        self.assertTrue(servicios.facilita(self.lince, self.debate, servicios.facilitacion(self.debate)))

    # Un voto por persona y elemento: repetirlo lo quita y otro lo cambia; ⛔ pide justificación.
    def test_votar(self):
        servicios.votar(self.nutria, self.debate, Voto.APOYO, opcion=self.solar)
        servicios.votar(self.nutria, self.debate, Voto.CONTRA, opcion=self.solar)
        self.assertEqual(list(Voto.objects.values_list("tipo", flat=True)), [Voto.CONTRA])
        servicios.votar(self.nutria, self.debate, Voto.CONTRA, opcion=self.solar)
        self.assertEqual(Voto.objects.count(), 0)
        with self.assertRaises(ValidationError):
            servicios.votar(self.nutria, self.debate, Voto.OPOSICION, opcion=self.solar)
        servicios.votar(self.nutria, self.debate, Voto.TODAS_ME_VALEN)
        self.assertEqual(servicios.recuentos(self.debate, self.nutria)[3], 1)

    # Una opción nueva nace propuesta y se abre con dos apoyos (no cuenta el de quien la propone).
    def test_opcion_nueva(self):
        opcion = servicios.proponer_opcion(self.nutria, self.debate, "En el parque")
        self.assertEqual(opcion.estado, Opcion.PROPUESTA)
        with self.assertRaises(ValidationError):
            servicios.argumentar(self.garza, opcion, "Hay sombra")
        servicios.votar(self.garza, self.debate, Voto.APOYO, opcion=opcion)
        servicios.votar(self.lince, self.debate, Voto.APOYO, opcion=opcion)
        opcion.refresh_from_db()
        self.assertEqual(opcion.estado, Opcion.ABIERTA)

    # Una opción de consenso solo se abre con apoyos de personas que habían apoyado opciones distintas; al
    # abrirse, las intervenciones vuelven a contar desde cero para todo el mundo.
    def test_opcion_de_consenso(self):
        LimitesDeDebate.objects.create(organizacion=self.tajo, intervenciones_blando=1, intervenciones_duro=5)
        servicios.argumentar(self.garza, self.solar, "Hay agua")
        servicios.argumentar(self.garza, self.solar, "Y sol")
        for persona in (self.nutria, self.garza):
            servicios.votar(persona, self.debate, Voto.APOYO, opcion=self.solar)
        consenso = servicios.proponer_opcion(self.lince, self.debate, "Solar con bancales altos", de_consenso=True)
        servicios.votar(self.nutria, self.debate, Voto.APOYO, opcion=consenso)
        servicios.votar(self.garza, self.debate, Voto.APOYO, opcion=consenso)
        consenso.refresh_from_db()
        self.assertEqual(consenso.estado, Opcion.PROPUESTA)  # las dos venían de la misma opción
        self.assertEqual(servicios.apoyos_de_consenso(consenso), 1)
        servicios.votar(self.garza, self.debate, Voto.APOYO, opcion=self.solar)  # Garza quita su 👍 del solar…
        servicios.votar(self.garza, self.debate, Voto.APOYO, opcion=self.azotea)  # …y apoya la azotea
        servicios.votar(self.garza, self.debate, Voto.APOYO, opcion=consenso)  # quita y vuelve a dar su apoyo
        servicios.votar(self.garza, self.debate, Voto.APOYO, opcion=consenso)
        consenso.refresh_from_db()
        self.assertEqual(consenso.estado, Opcion.ABIERTA)
        self.debate.refresh_from_db()
        self.assertIsNotNone(self.debate.intervenciones_desde)
        self.assertFalse(servicios.argumentar(self.garza, self.solar, "De nuevo").pasado)

    # Límites en cascada: el grupo padre y el propio debate pueden ser más estrictos; vale el menor.
    def test_limites_por_grupo_y_debate(self):
        LimitesDeDebate.objects.create(organizacion=self.tajo, palabras_duro=300)
        LimitesDeDebate.objects.create(grupo=self.general, palabras_duro=200, intervenciones_duro=9)
        self.assertEqual(servicios.limites_de(self.henares, self.debate).palabras_duro, 200)
        self.client.force_login(self.lince)
        self.client.post(f"/debates/{self.debate.pk}/", {"accion": "limites", "palabras_duro": "3", "apoyos_para_opcion": "2"})
        limites = servicios.limites_de(self.henares, self.debate)
        self.assertEqual((limites.palabras_duro, limites.intervenciones_duro), (3, 9))
        with self.assertRaises(ValidationError):
            servicios.argumentar(self.nutria, self.solar, "uno dos tres cuatro")
        self.client.force_login(self.nutria)
        self.client.post(f"/debates/{self.debate.pk}/", {"accion": "limites", "palabras_duro": "1"})
        self.assertEqual(servicios.limites_de(self.henares, self.debate).palabras_duro, 3)

    # Límites: pasado el blando, una intervención más y marcada; después, ya no. Las palabras de más, no.
    def test_limites(self):
        LimitesDeDebate.objects.create(organizacion=self.tajo, intervenciones_blando=1, intervenciones_duro=5, palabras_duro=5)
        primero = servicios.argumentar(self.nutria, self.solar, "Hay agua cerca")
        segundo = servicios.argumentar(self.nutria, self.solar, "Y mucho sol")
        self.assertEqual((primero.pasado, segundo.pasado), (False, True))
        with self.assertRaises(ValidationError):
            servicios.argumentar(self.nutria, self.solar, "Otro más")
        with self.assertRaises(ValidationError):
            servicios.argumentar(self.garza, self.solar, "uno dos tres cuatro cinco seis")

    # Al cerrarlo con una conclusión, llega al registro de decisiones y ya no se puede votar.
    def test_cerrar(self):
        servicios.votar(self.nutria, self.debate, Voto.APOYO, opcion=self.solar)
        with self.assertRaises(ValidationError):
            servicios.cerrar(self.nutria, self.debate, "Solar")
        servicios.cerrar(self.lince, self.debate, "El huerto va en el solar", elegida=self.solar)
        Decision = apps.get_model("decisiones", "Decision")
        decision = Decision.objects.get()
        self.assertEqual((decision.texto, decision.forma), ("El huerto va en el solar", "debate"))
        self.assertIn("1 a favor", decision.detalle)
        with self.assertRaises(ValidationError):
            servicios.votar(self.nutria, self.debate, Voto.APOYO, opcion=self.azotea)

    # La ficha (argumentos, votos, respuestas) cuesta lo mismo con más de todo; los votos salen sin nombres.
    def test_ficha(self):
        argumento = servicios.argumentar(self.garza, self.solar, "Hay agua cerca")
        servicios.votar(self.nutria, self.debate, Voto.MUY_IMPORTANTE, opcion=self.solar, justificacion="Es lo más barato")

        # Un argumento, una respuesta y un voto más.
        def mas():
            persona = crear_usuario_de_prueba(f"Persona {Voto.objects.count()}")
            admitir(persona, self.henares)
            otro = servicios.argumentar(persona, self.azotea, "Da el sol todo el día", a_favor=False)
            servicios.argumentar(persona, self.solar, "Y está cerca", padre=argumento)
            servicios.votar(persona, self.debate, Voto.APOYO, argumento=otro)

        respuesta = self.comprobar_consultas(f"/debates/{self.debate.pk}/", 9, mas)
        self.assertContains(respuesta, "Es lo más barato")
        self.assertContains(respuesta, "Garza")
        self.assertNotContains(respuesta, "Nutria ·")
        self.comprobar_consultas("/debates/", 2, mas)

    # Botones de la ficha: votar y argumentar por POST.
    def test_botones(self):
        self.client.post(f"/debates/{self.debate.pk}/", {"accion": "votar", "tipo": "apoyo", "opcion": self.solar.pk})
        self.client.post(f"/debates/{self.debate.pk}/", {"accion": "argumentar", "opcion": self.azotea.pk, "texto": "Hay mucho viento", "a_favor": "no"})
        self.assertEqual(Voto.objects.get().tipo, Voto.APOYO)
        self.assertFalse(self.azotea.argumentos.get().a_favor)
