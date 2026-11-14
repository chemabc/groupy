"""
Pruebas de la tarjeta «Comunicaciones» de «Inicio → Panel» (comunicaciones/inicio.py): qué sale en
«Recibidas» y en «Enviadas» y que el panel cuesta lo mismo con más notificaciones y conversaciones. (Las
demás tarjetas del panel se prueban en proyectos/tests/test_inicio.py.)

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares). Lince es admin de GRU Henares; Nutria, miembro.
"""

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from comunicaciones.administraciones import Buzon
from comunicaciones.models import Notificacion
from comunicaciones.servicios import abrir_conversacion, escribir
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion


class PruebasDeLaTarjeta(PruebaDePantalla):
    """El panel de Nutria."""

    # Crea la estructura.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.lince = crear_usuario_de_prueba("Lince")
        cls.nutria = crear_usuario_de_prueba("Nutria")
        admitir(cls.lince, cls.henares, rol=Pertenencia.ADMIN_GRUPO)
        admitir(cls.nutria, cls.henares, es_base=True)
        cls.usuario = cls.nutria

    # Una notificación sin ver, una conversación de Nutria sin respuesta y otra que la administración ya
    # ha contestado (sale en «Recibidas», no en «Enviadas»).
    def mas_comunicaciones(self):
        numero = Notificacion.objects.count()
        Notificacion.objects.create(usuario=self.nutria, tipo="t", origen="grupos", texto=f"Aviso {numero}")
        abrir_conversacion(self.nutria, Buzon(grupo=self.henares), f"Llaves {numero}", "¿Quién las tiene?")
        contestada = abrir_conversacion(self.nutria, Buzon(grupo=self.henares), f"Local {numero}", "¿Está libre?")
        escribir(contestada, self.lince, "Sí, el jueves.", como_admin=True)

    # El panel cuesta lo mismo con pocas comunicaciones que con muchas.
    def test_consultas(self):
        self.comprobar_consultas("/", 10, self.mas_comunicaciones)

    # Recibidas: la notificación y la respuesta, resaltadas; enviadas: la que sigue sin resolver. La que
    # tiene una respuesta sin leer no se repite en «Enviadas».
    def test_contenido(self):
        self.mas_comunicaciones()
        respuesta = self.client.get("/")
        self.assertContains(respuesta, "Recibidas (2)")
        self.assertContains(respuesta, "Aviso 0")
        self.assertContains(respuesta, "respuesta de la administración")
        self.assertContains(respuesta, "Enviadas, sin resolver (1)")
        self.assertContains(respuesta, "Llaves 0")
        self.assertContains(respuesta, 'aria-label="pendiente"')
