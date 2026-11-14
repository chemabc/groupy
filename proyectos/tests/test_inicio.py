"""
Pruebas de la portada, «Inicio» (base/inicio.py y las tarjetas de los módulos), con datos de proyectos,
solicitudes, talentos, lugares y grupos: qué sale en cada recuadro y que el número de consultas no crece
con las filas.

Van aquí, en «proyectos», porque es el único módulo de los que aportan tarjetas que puede importar a los
demás que hacen falta para crear los datos (grupos, solicitudes, talentos…: capas de abajo). Las de
comunicaciones están en comunicaciones/tests/test_inicio.py.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Jarama ⊃ GRU Henares). Nutria está en GRU Henares
(asamblea base); Pato no está en ningún grupo.
"""

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from grupos.servicios import admitir, crear_grupo, crear_organizacion
from solicitudes.servicios import pedir
from talentos.servicios import anadir
from tipologias.servicios import crear_tipologia

from proyectos.models import Proyecto
from proyectos.servicios import crear_proyecto, crear_tarea


class PruebasDeInicio(PruebaDePantalla):
    """Inicio → Panel e Inicio → Mis datos, como Nutria."""

    # Crea la organización, los grupos, las personas y la tipología de proyecto.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.gru_tajo = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.jarama = crear_grupo(cls.tajo, "GRU Jarama", padre=cls.gru_tajo)
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.jarama)
        cls.nutria = crear_usuario_de_prueba("Nutria")
        cls.lince = crear_usuario_de_prueba("Lince")
        admitir(cls.nutria, cls.henares, es_base=True)
        admitir(cls.lince, cls.henares)
        cls.generico = crear_tipologia("proyecto", "Genérico")
        # Un proyecto de Lince en el que Nutria no participa (no sale en su panel). Crea de paso la
        # audiencia «GRU Henares» antes de la primera visita, como pasa en la plataforma de verdad.
        crear_proyecto(cls.lince, cls.generico, {"titulo": "Semilla"}, grupo=cls.henares, visibilidad="grupo:0")
        cls.usuario = cls.nutria

    # Añade de todo lo que sale en el panel: un proyecto de Nutria, otro de Lince con una tarea de Nutria,
    # uno terminado (no sale), una solicitud de otra persona para entrar en GRU Henares (Nutria puede
    # apoyarla) y una de Nutria para entrar en un grupo nuevo, hermano del suyo.
    def mas_de_todo(self):
        numero = Proyecto.objects.count()
        crear_proyecto(self.nutria, self.generico, {"titulo": f"Huerto {numero}"}, grupo=self.henares, visibilidad="grupo:0")
        ajeno = crear_proyecto(self.lince, self.generico, {"titulo": f"Riego {numero}"}, grupo=self.henares, visibilidad="grupo:0")
        crear_tarea(self.lince, {"titulo": "Regar", "responsable": self.nutria}, proyecto=ajeno)
        terminado = crear_proyecto(self.nutria, self.generico, {"titulo": f"Acabado {numero}"}, grupo=self.henares, visibilidad="grupo:0")
        Proyecto.objects.filter(pk=terminado.pk).update(estado=Proyecto.FINALIZADO)
        pedir(crear_usuario_de_prueba(f"Pato {numero}"), "grupos.entrar", self.henares, "Quiero entrar")
        pedir(self.nutria, "grupos.entrar", crear_grupo(self.tajo, f"GRU Guadarrama {numero}", padre=self.jarama), "Me mudo")

    # El panel cuesta lo mismo con pocos datos que con muchos.
    def test_consultas_del_panel(self):
        self.comprobar_consultas("/", 10, self.mas_de_todo)

    # Lo que sale en el panel: los proyectos abiertos en los que participa (no el terminado) y las
    # solicitudes recibidas y enviadas, cada una con su enlace.
    def test_contenido_del_panel(self):
        self.mas_de_todo()
        respuesta = self.client.get("/")
        self.assertContains(respuesta, "Huerto 1")
        self.assertContains(respuesta, "Riego 1")
        self.assertNotContains(respuesta, "Acabado 1")
        self.assertContains(respuesta, "Recibidas, para apoyar (1)")
        self.assertContains(respuesta, "Entrar en un grupo: GRU Henares")
        self.assertContains(respuesta, "Entrar en un grupo: GRU Guadarrama 1")
        self.assertContains(respuesta, 'href="/proyectos/')

    # «Ver todas (N)» sale cuando hay más de las que caben (en proyectos, 8): con 10 proyectos abiertos.
    def test_ver_todas(self):
        for _vez in range(5):
            self.mas_de_todo()
        respuesta = self.client.get("/")
        self.assertContains(respuesta, "Ver todas (10)")
        self.assertNotContains(respuesta, "Semilla")

    # Mis datos: datos públicos y privados, talentos, lugar y el árbol de grupos; cuesta lo mismo con más
    # talentos y más grupos.
    def test_mis_datos(self):
        # Un talento y un grupo más cada vez.
        def mas():
            numero = self.nutria.talentos.count()
            anadir(self.nutria, f"Furgoneta {numero}", "recurso")
            admitir(self.nutria, crear_grupo(self.tajo, f"GRU Lozoya {numero}", padre=self.henares))

        respuesta = self.comprobar_consultas("/mis-datos/", 6, mas)
        self.assertContains(respuesta, "Datos públicos")
        self.assertContains(respuesta, "Furgoneta 0")
        self.assertContains(respuesta, "Aún no has elegido tu lugar.")
        self.assertContains(respuesta, "arbol-grupo arbol-base")
        self.assertContains(respuesta, 'href="/cuenta/datos/"')
