"""
Pruebas de la plantilla general: página entera y zona suelta para htmx, menú, vistas, ayuda, número de
consultas y rutas del menú en el registro.
"""

from django.test import SimpleTestCase
from django.utils.module_loading import import_string

from base.comprobaciones import comprobar_contrato
from base.contrato import EntradaDeMenu, Vista
from base.pruebas import PruebaDePantalla, contratos_de_prueba, crear_usuario_de_prueba, modulo_falso
from base.registro import RegistroDeModulos

# Cabeceras que manda htmx al navegar con el menú (ver base/contexto.py).
CABECERAS_DE_HTMX = {"HX-Request": "true", "HX-Target": "zona"}

# Cabeceras que manda htmx al pedir una página para el panel de ayuda (ver panelDeAyuda en interfaz.js).
CABECERAS_DEL_PANEL = {"HX-Request": "true", "HX-Target": "panel-de-ayuda-contenido"}


class PruebasDeLaPlantilla(PruebaDePantalla):
    """Comprueba las pantallas de «Inicio» y lo que pinta la plantilla general."""

    # «Inicio → Panel» hace una sola consulta, la que carga el usuario de la sesión (la sesión está
    # en la caché). El menú y la ayuda salen del registro, en memoria.
    def test_consultas_de_inicio(self):
        self.comprobar_consultas("/", 1, None)

    # «Desarrollo y mantenimiento → Componentes», igual.
    def test_consultas_de_componentes(self):
        self.comprobar_consultas("/componentes/", 1, None)

    # Una visita normal recibe la página entera, con los menús, la zona y la ayuda.
    def test_pagina_entera(self):
        respuesta = self.client.get("/")
        self.assertContains(respuesta, "<!DOCTYPE html>")
        self.assertContains(respuesta, 'aria-label="Secciones"')
        self.assertContains(respuesta, 'id="zona"', count=1)
        self.assertContains(respuesta, "<title>Panel · Inicio · Asambleas</title>", count=1)
        # La miniayuda «?» de la sección, en su ventana emergente; arriba, el «?» rojo y el panel de ayuda.
        self.assertContains(respuesta, 'role="dialog"')
        self.assertContains(respuesta, "Tu portada.")
        self.assertContains(respuesta, 'id="boton-de-ayuda"', count=1)
        self.assertContains(respuesta, 'id="panel-de-ayuda"', count=1)
        self.assertContains(respuesta, 'data-direccion="/ayuda/como-se-hace/"')

    # El panel de ayuda recibe la página sin título de pestaña, sin zona ni menús, con sus pestañas y
    # «Abrir en grande»; cuesta lo mismo que la página entera.
    def test_pagina_para_el_panel(self):
        # Visita de calentamiento: lo que se guarda en la caché tras la primera no cuenta.
        self.client.get("/componentes/", headers=CABECERAS_DEL_PANEL)
        with self.assertNumQueries(1):
            respuesta = self.client.get("/componentes/", headers=CABECERAS_DEL_PANEL)
        self.assertNotContains(respuesta, "<title>")
        self.assertNotContains(respuesta, 'id="zona"')
        self.assertNotContains(respuesta, 'aria-label="Secciones"')
        self.assertContains(respuesta, "Abrir en grande")
        self.assertContains(respuesta, 'aria-current="page">Componentes</a>')

    # La navegación con htmx recibe solo el título y la zona central, sin cabecera ni menús.
    def test_solo_la_zona_para_htmx(self):
        respuesta = self.client.get("/componentes/", headers=CABECERAS_DE_HTMX)
        self.assertNotContains(respuesta, "<html")
        self.assertNotContains(respuesta, 'aria-label="Secciones"')
        self.assertContains(respuesta, 'id="zona"', count=1)
        self.assertContains(respuesta, "<title>Componentes · Asambleas</title>")

    # Para el botón «atrás», htmx pide la página entera, aunque mande sus cabeceras.
    def test_pagina_entera_al_volver_atras(self):
        cabeceras = {**CABECERAS_DE_HTMX, "HX-History-Restore-Request": "true"}
        respuesta = self.client.get("/", headers=cabeceras)
        self.assertContains(respuesta, "<!DOCTYPE html>")

    # La respuesta avisa de que cambia según las cabeceras de htmx, para que el navegador no las mezcle.
    def test_cabecera_vary(self):
        respuesta = self.client.get("/")
        self.assertIn("HX-Request", respuesta["Vary"])

    # La zona lleva los códigos de la sección actual (para marcar el menú) y marca la vista activa.
    def test_seccion_y_vista_marcadas(self):
        respuesta = self.client.get("/componentes/")
        self.assertContains(respuesta, 'data-secciones="mantenimiento.desarrollo base.componentes"')
        self.assertContains(respuesta, 'aria-current="page">Componentes</a>')

    # Una sección con pestañas («Calendario y eventos»): arriba, sus subsecciones (aunque sean de módulos
    # distintos), la elegida marcada y, en una segunda fila, sus vistas; el menú izquierdo marca la sección
    # (las pestañas no salen en él) y el título es el de la sección.
    def test_seccion_con_pestanas(self):
        # «base» no puede importar «grupos» (está más arriba): sus servicios se nombran como texto.
        _tajo, grupo = import_string("grupos.servicios.crear_organizacion")("ORG Tajo", "GRU Tajo")
        import_string("grupos.servicios.admitir")(self.usuario, grupo)
        respuesta = self.client.get("/eventos/")
        interfaz = respuesta.context["interfaz"]
        self.assertEqual(interfaz["codigos"], ["calendario.calendario"])
        self.assertEqual([p["nombre"] for p in interfaz["pestanas"]], ["Calendario", "Eventos de mis grupos", "Mis eventos", "Convocar"])
        self.assertEqual([p["activa"] for p in interfaz["pestanas"]], [False, True, False, False])
        self.assertEqual([v["vista"].nombre for v in interfaz["subvistas"]], ["Próximos", "Pasados"])
        self.assertContains(respuesta, '<h1 class="text-lg font-semibold">Calendario y eventos</h1>', html=False)
        self.assertNotContains(respuesta, 'data-codigo="eventos.lista"')

    # El menú va en bloques: una persona sin nada que administrar solo ve el suyo, sin título ni banda; la
    # admin de un grupo ve también «Administrar» y, en sus pantallas, la banda que lo recuerda.
    def test_bloques(self):
        respuesta = self.client.get("/")
        self.assertEqual([b["titulo"] for b in respuesta.context["interfaz"]["bloques"]], [""])
        self.assertNotContains(respuesta, "Estás administrando")
        self.client.force_login(crear_usuario_de_prueba("Jefa", es_superadmin=True))
        respuesta = self.client.get("/solicitudes/por-aprobar/")
        self.assertEqual([b["titulo"] for b in respuesta.context["interfaz"]["bloques"]], ["", "Administrar", "Plataforma"])
        self.assertContains(respuesta, "Estás administrando")


class PruebasDeRutasDelMenu(SimpleTestCase):
    """Comprueba que el registro sabe a qué sección pertenece cada dirección del menú."""

    # La dirección de una sección y las de sus vistas llevan a esa sección; las de una subsección, a la
    # subsección, aunque repita la de su sección.
    def test_rutas_de_secciones_y_subsecciones(self):
        hija = EntradaDeMenu("alfa.hija", "Hija", url="alfa:lista", vistas=(Vista("Mapa", "alfa:mapa"),))
        madre = EntradaDeMenu("alfa.madre", "Madre", url="alfa:lista", subsecciones=(hija,))
        nuevo = RegistroDeModulos()
        nuevo.cargar([modulo_falso("alfa", menu=(madre,))])
        self.assertEqual(nuevo.errores, [])
        self.assertEqual(nuevo.rutas["alfa:lista"], (madre, hija))
        self.assertEqual(nuevo.rutas["alfa:mapa"], (madre, hija))

    # Dos secciones que no cuelgan una de otra no pueden compartir dirección.
    def test_direccion_repetida(self):
        una = EntradaDeMenu("alfa.una", "Una", url="alfa:lista")
        otra = EntradaDeMenu("alfa.otra", "Otra", url="alfa:lista")
        nuevo = RegistroDeModulos()
        nuevo.cargar([modulo_falso("alfa", menu=(una, otra))])
        self.assertIn("está en dos entradas del menú", nuevo.errores[0])

    # Una entrada de menú que lleva a una dirección que no existe es un error de las comprobaciones.
    def test_direccion_inexistente(self):
        rota = EntradaDeMenu("alfa.rota", "Rota", url="alfa:no_existe")
        with contratos_de_prueba(modulo_falso("alfa", menu=(rota,))):
            codigos = [error.id for error in comprobar_contrato()]
        self.assertIn("base.E004", codigos)
