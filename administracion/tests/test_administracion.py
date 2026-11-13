"""
Pruebas de la sección «Usuarios» del superadmin: personas de la bóveda, dominios permitidos y alias,
con su número de consultas (en las dos bases), y que solo entra quien tiene permiso.
"""

from django.contrib.auth import get_user_model

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from boveda.models import Persona
from boveda.servicios import poner_dominios, registrar_persona
from grupos.servicios import admitir, crear_grupo, crear_organizacion


class PruebaComoSuperadmin(PruebaDePantalla):
    """Base: un superadmin con la sesión iniciada, ORG Tajo (GRU Tajo ⊃ GRU Henares) y Nutria en Henares."""

    databases = {"default", "boveda"}

    # Crea el superadmin, la organización y Nutria.
    @classmethod
    def setUpTestData(cls):
        cls.usuario = crear_usuario_de_prueba("superadmin", es_superadmin=True)
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.nutria = crear_usuario_de_prueba("Nutria")
        admitir(cls.nutria, cls.henares, es_base=True)


class PruebasDeLaBovedaEnPantalla(PruebaComoSuperadmin):
    """Personas y dominios."""

    # Añade tres personas más (para comprobar que la lista no crece en consultas).
    def mas_personas(self):
        for numero in range(3):
            registrar_persona(f"Persona {numero}", f"p{numero}@educa.org", self.tajo.pk)

    # La lista de personas cuesta lo mismo con 1 que con 4; la ficha y los dominios, pocas consultas.
    def test_consultas(self):
        persona = registrar_persona("Ana Pérez", "ana@educa.org", self.tajo.pk)
        self.comprobar_consultas("/usuarios/boveda/personas/", 3, self.mas_personas)
        self.comprobar_consultas(f"/usuarios/boveda/personas/{persona.pk}/", 4, None)
        self.comprobar_consultas("/usuarios/boveda/dominios/", 3, lambda: crear_organizacion("ORG Ebro", "GRU Ebro"))

    # Alta desde la pantalla: lleva a la ficha, donde se ve el nombre; en la lista, solo «Persona xxxx».
    def test_alta_y_lista_sin_nombres(self):
        respuesta = self.client.post(
            "/usuarios/boveda/personas/", {"nombre": "Ana Pérez", "correo_oficial": "ana@educa.org", "organizacion": self.tajo.pk}
        )
        persona = Persona.objects.get()
        self.assertRedirects(respuesta, f"/usuarios/boveda/personas/{persona.pk}/")
        self.assertContains(self.client.get(respuesta.url), "Ana Pérez")
        lista = self.client.get("/usuarios/boveda/personas/")
        self.assertContains(lista, str(persona))
        self.assertNotContains(lista, "Ana Pérez")
        self.assertNotContains(lista, "ana@educa.org")

    # Validar desde la ficha: el correo se borra y el pase queda emitido.
    def test_validar(self):
        persona = registrar_persona("Ana Pérez", "ana@educa.org", self.tajo.pk)
        respuesta = self.client.post(f"/usuarios/boveda/personas/{persona.pk}/", {"accion": "validar"})
        self.assertContains(respuesta, "Su correo se ha borrado")
        self.assertContains(respuesta, "Borrado al validar")
        self.assertContains(respuesta, "marcado en el alta provisional")

    # Dominios desde la pantalla; después, el alta con otro dominio se rechaza con explicación.
    def test_dominios(self):
        respuesta = self.client.post("/usuarios/boveda/dominios/", {"organizacion": self.tajo.pk, "dominios": "educa.org, @Otra.es"})
        self.assertContains(respuesta, "Guardados los dominios de «ORG Tajo»: educa.org, otra.es.")
        self.assertContains(respuesta, "se guardan en las tablas de la bóveda")
        respuesta = self.client.post(
            "/usuarios/boveda/personas/", {"nombre": "Luis", "correo_oficial": "luis@gmail.com", "organizacion": self.tajo.pk}
        )
        self.assertContains(respuesta, "Esta organización solo admite correos de: educa.org, otra.es.")

    # La ficha de la organización en la trastienda muestra sus dominios, con la nota de dónde se guardan.
    def test_dominios_en_la_trastienda(self):
        poner_dominios(self.tajo.pk, ["educa.org"])
        respuesta = self.client.get(f"/trastienda/grupos/organizacion/{self.tajo.pk}/change/")
        self.assertContains(respuesta, "educa.org")
        self.assertContains(respuesta, "Se guardan en las tablas de la bóveda")


class PruebasDeAlias(PruebaComoSuperadmin):
    """Lista y ficha de alias."""

    # Añade tres alias más.
    def mas_alias(self):
        for numero in range(3):
            admitir(crear_usuario_de_prueba(f"Extra {numero}"), self.henares)

    # La lista cuesta lo mismo con más alias; la ficha, pocas consultas.
    def test_consultas(self):
        self.comprobar_consultas("/usuarios/alias/", 2, self.mas_alias)
        self.comprobar_consultas(f"/usuarios/alias/{self.nutria.pk}/", 5, None)

    # La lista muestra la asamblea base con su camino y el origen, con enlace a la ficha.
    def test_lista(self):
        respuesta = self.client.get("/usuarios/alias/")
        self.assertContains(respuesta, "ORG Tajo › GRU Tajo › GRU Henares")
        self.assertContains(respuesta, "Alta directa")
        self.assertContains(respuesta, f'href="/usuarios/alias/{self.nutria.pk}/"')

    # Hacer superadmin a otro y quitárselo; a uno mismo, no.
    def test_superadmin(self):
        self.client.post(f"/usuarios/alias/{self.nutria.pk}/", {"accion": "superadmin"})
        self.assertTrue(get_user_model().objects.get(pk=self.nutria.pk).es_superadmin)
        self.client.post(f"/usuarios/alias/{self.nutria.pk}/", {"accion": "superadmin"})
        self.assertFalse(get_user_model().objects.get(pk=self.nutria.pk).es_superadmin)
        respuesta = self.client.post(f"/usuarios/alias/{self.usuario.pk}/", {"accion": "superadmin"})
        self.assertContains(respuesta, "No puedes quitarte a ti mismo el superadmin")
        self.assertTrue(get_user_model().objects.get(pk=self.usuario.pk).es_superadmin)

    # La ficha muestra todos sus grupos, también los heredados.
    def test_ficha(self):
        respuesta = self.client.get(f"/usuarios/alias/{self.nutria.pk}/")
        self.assertContains(respuesta, "ORG Tajo › GRU Tajo › GRU Henares")
        self.assertContains(respuesta, "asamblea base")
        self.assertContains(respuesta, "heredado")


class PruebasSinPermiso(PruebaDePantalla):
    """Una persona normal no ve la sección «Usuarios» ni puede entrar."""

    databases = {"default", "boveda"}

    # No sale en su menú y las pantallas explican lo que falta.
    def test_sin_permiso(self):
        self.assertNotContains(self.client.get("/"), "Bóveda (personas reales)")
        respuesta = self.client.get("/usuarios/boveda/personas/")
        self.assertContains(respuesta, "boveda.ver", status_code=403)
        respuesta = self.client.get("/usuarios/alias/")
        self.assertContains(respuesta, "administracion.usuarios", status_code=403)
