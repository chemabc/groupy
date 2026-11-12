"""
Pruebas de la plantilla general: página entera y zona suelta para htmx, menú, vistas, ayuda, número de
consultas y rutas del menú en el registro.
"""

from django.test import SimpleTestCase

from base.comprobaciones import comprobar_contrato
from base.contrato import EntradaDeMenu, Vista
from base.pruebas import PruebaDePantalla, contratos_de_prueba, modulo_falso
from base.registro import RegistroDeModulos

# Cabeceras que manda htmx al navegar con el menú (ver base/contexto.py).
CABECERAS_DE_HTMX = {"HX-Request": "true", "HX-Target": "zona"}


class PruebasDeLaPlantilla(PruebaDePantalla):
    """Comprueba las pantallas de «Inicio» y lo que pinta la plantilla general."""

    # «Inicio → Estructura» no hace ninguna consulta: el menú y la ayuda salen del registro, en memoria.
    def test_consultas_de_inicio(self):
        self.comprobar_consultas("/", 0, None)

    # «Inicio → Componentes», igual.
    def test_consultas_de_componentes(self):
        self.comprobar_consultas("/componentes/", 0, None)

    # Una visita normal recibe la página entera, con los menús, la zona y la ayuda.
    def test_pagina_entera(self):
        respuesta = self.client.get("/")
        self.assertContains(respuesta, "<!DOCTYPE html>")
        self.assertContains(respuesta, 'aria-label="Secciones"')
        self.assertContains(respuesta, 'id="zona"', count=1)
        self.assertContains(respuesta, "<title>Estructura · Inicio · Asambleas</title>", count=1)
        self.assertContains(respuesta, 'role="dialog"')

    # La navegación con htmx recibe solo el título y la zona central, sin cabecera ni menús.
    def test_solo_la_zona_para_htmx(self):
        respuesta = self.client.get("/componentes/", headers=CABECERAS_DE_HTMX)
        self.assertNotContains(respuesta, "<html")
        self.assertNotContains(respuesta, 'aria-label="Secciones"')
        self.assertContains(respuesta, 'id="zona"', count=1)
        self.assertContains(respuesta, "<title>Componentes · Inicio · Asambleas</title>")

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
        self.assertContains(respuesta, 'data-secciones="base.inicio"')
        self.assertContains(respuesta, 'aria-current="page">Componentes</a>')


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
