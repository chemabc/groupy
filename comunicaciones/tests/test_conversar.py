"""
Pruebas de las conversaciones con grupos (la sala de cada grupo) y con personas (de dos en dos, con
bloqueo), decididas en [A-56]: quién entra, los números del menú, el bloqueo con su aviso al superadmin y
lo que cuesta cada pantalla.
"""

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from comunicaciones import con_grupos, con_personas
from comunicaciones.models import Bloqueo, ConversacionEntrePersonas, Notificacion
from eventos_sw.servicios import procesar_bandeja
from grupos.servicios import admitir, crear_grupo, crear_organizacion


class PruebaDeConversar(PruebaDePantalla):
    """ORG Tajo con GRU Tajo ⊃ GRU Henares. Nutria (la sesión) y Lince en GRU Henares; Garza solo en GRU Tajo."""

    # Crea la estructura.
    @classmethod
    def setUpTestData(cls):
        _tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(_tajo, "GRU Henares", padre=cls.general)
        cls.usuario = cls.nutria = crear_usuario_de_prueba("Nutria")
        cls.lince = crear_usuario_de_prueba("Lince")
        cls.garza = crear_usuario_de_prueba("Garza")
        admitir(cls.nutria, cls.henares)
        admitir(cls.lince, cls.henares)
        admitir(cls.garza, cls.general)

    # Inicia sesión como otra persona.
    def como(self, persona):
        self.client.force_login(persona)


class PruebasDeSalas(PruebaDeConversar):
    """La sala de cada grupo."""

    # Solo entran sus miembros: Garza (de GRU Tajo, que contiene a GRU Henares) no entra en la de GRU
    # Henares; tampoco el superadmin. Lo que escribe Lince sale en el número de Nutria hasta que lo lee.
    def test_quien_entra_y_sin_leer(self):
        url = f"/comunicaciones/grupos/{self.henares.pk}/"
        self.assertEqual(self.client.get(url).status_code, 200)
        self.como(self.garza)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.como(crear_usuario_de_prueba("superadmin", es_superadmin=True))
        self.assertEqual(self.client.get(url).status_code, 403)
        with self.captureOnCommitCallbacks(execute=True):
            con_grupos.escribir(self.henares, self.lince, "¿Quién abre el sábado?")
        self.assertEqual(con_grupos.salas_sin_leer(self.nutria), 1)
        self.assertEqual(con_grupos.salas_sin_leer(self.lince), 0)
        self.como(self.nutria)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertContains(self.client.get(url), "¿Quién abre el sábado?")
        self.assertEqual(con_grupos.salas_sin_leer(self.nutria), 0)
        # Escribir desde la pantalla.
        respuesta = self.client.post(url, {"texto": "Yo misma"})
        self.assertRedirects(respuesta, url)
        self.assertContains(self.client.get("/comunicaciones/grupos/"), "Nutria: Yo misma")

    # Las pantallas no crecen con los mensajes ni con los grupos.
    def test_consultas(self):
        veces = []

        # Añade un grupo más de Nutria y mensajes en las dos salas (se llama dos veces: nombres distintos).
        def mas():
            veces.append(1)
            otro = crear_grupo(self.henares.organizacion, f"GRU Sorbe {len(veces)}", padre=self.henares)
            admitir(self.nutria, otro)
            for numero in range(3):
                con_grupos.escribir(self.henares, self.lince, f"Mensaje {numero}")
                con_grupos.escribir(otro, self.nutria, f"Otro {numero}")

        con_grupos.escribir(self.henares, self.lince, "Primero")
        self.comprobar_consultas("/comunicaciones/grupos/", 3, mas)
        self.comprobar_consultas(f"/comunicaciones/grupos/{self.henares.pk}/", 5, mas)


class PruebasDeConversacionesEntrePersonas(PruebaDeConversar):
    """Conversaciones de dos en dos."""

    # Nutria escribe a Lince (comparten GRU Henares) desde la pantalla; a Garza no puede empezar a
    # escribirle (no comparten grupo). Solo la leen las dos: Garza y el superadmin no la encuentran.
    def test_escribir_y_quien_lee(self):
        respuesta = self.client.post("/comunicaciones/personas/escribir/", {"persona": "Lince", "texto": "¡Hola!"})
        conversacion = ConversacionEntrePersonas.objects.get()
        self.assertRedirects(respuesta, f"/comunicaciones/personas/{conversacion.pk}/")
        respuesta = self.client.post("/comunicaciones/personas/escribir/", {"persona": "Garza", "texto": "¡Hola!"})
        self.assertContains(respuesta, "No compartes grupo con esta persona")
        self.assertEqual(con_personas.sin_leer(self.lince), 1)
        url = f"/comunicaciones/personas/{conversacion.pk}/"
        for persona, codigo in ((self.garza, 404), (crear_usuario_de_prueba("superadmin", es_superadmin=True), 404), (self.lince, 200)):
            self.como(persona)
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.client.get(url).status_code, codigo)
        self.assertEqual(con_personas.sin_leer(self.lince), 0)
        # La lista del selector: Lince ve a Nutria (en GRU Henares) y no a Garza.
        datos = self.client.get("/comunicaciones/personas/lista/").json()
        nombres = [persona["alias"] for bloque in datos["bloques"] for grupo in bloque["grupos"] for persona in grupo["personas"]]
        self.assertEqual(nombres, ["Nutria"])

    # Lince bloquea a Nutria: ninguna de las dos puede escribir, el superadmin recibe un aviso y, al
    # desbloquear, vuelven a poder.
    def test_bloqueo(self):
        superadmin = crear_usuario_de_prueba("superadmin", es_superadmin=True)
        conversacion = con_personas.escribir(self.nutria, self.lince, "Hola")
        url = f"/comunicaciones/personas/{conversacion.pk}/"
        self.como(self.lince)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(url, {"accion": "bloquear"})
            procesar_bandeja()
        self.assertTrue(Bloqueo.objects.filter(quien=self.lince, a_quien=self.nutria).exists())
        aviso = Notificacion.objects.get(usuario=superadmin)
        self.assertEqual(aviso.texto, "Lince ha bloqueado a Nutria en las conversaciones entre personas.")
        self.assertContains(self.client.get(url), "Desbloquear a Nutria")
        self.como(self.nutria)
        self.assertContains(self.client.post(url, {"accion": "escribir", "texto": "¿Por qué?"}), "Esta conversación está bloqueada")
        self.assertEqual(conversacion.mensajes.count(), 1)
        self.assertNotContains(self.client.get(url), "Desbloquear")
        # Nutria no puede quitar un bloqueo que no puso; Lince sí.
        self.client.post(url, {"accion": "desbloquear"})
        self.assertTrue(Bloqueo.objects.exists())
        self.como(self.lince)
        self.client.post(url, {"accion": "desbloquear"})
        self.assertFalse(Bloqueo.objects.exists())
        self.assertRedirects(self.client.post(url, {"accion": "escribir", "texto": "Perdona"}), url)

    # Las pantallas no crecen con las conversaciones ni con los mensajes.
    def test_consultas(self):
        conversacion = con_personas.escribir(self.nutria, self.lince, "Hola")
        veces = []

        # Añade conversaciones de otras personas con Nutria, mensajes de Lince y un bloqueo (se llama dos
        # veces: alias distintos).
        def mas():
            veces.append(1)
            for numero in range(3):
                otra = crear_usuario_de_prueba(f"Persona {len(veces)}{numero}")
                admitir(otra, self.henares)
                con_personas.escribir(otra, self.nutria, "Hola")
                con_personas.escribir(self.lince, self.nutria, f"Mensaje {numero}")
            con_personas.bloquear(self.nutria, otra)

        self.comprobar_consultas("/comunicaciones/personas/", 3, mas)
        self.comprobar_consultas(f"/comunicaciones/personas/{conversacion.pk}/", 5, mas)
        self.comprobar_consultas("/comunicaciones/personas/escribir/", 1, None)
