"""
Pruebas del contrato de módulo y del registro.

Crean módulos de mentira (configuraciones que no están instaladas) y comprueban que el registro reúne
bien lo que declaran y que avisa de cada error de declaración. No tocan la base de datos
(SimpleTestCase), así que son muy rápidas.
"""

from django.test import SimpleTestCase

from base.contrato import Ayuda, EntradaDeMenu, Emision, Escucha, Permiso
from base.pruebas import contratos_de_prueba, modulo_falso
from base.registro import RegistroDeModulos, registro


class PruebasDelRegistro(SimpleTestCase):
    """Comprueba que el registro reúne los contratos y detecta los errores de declaración."""

    # Un contrato bien declarado se carga sin errores y cada cosa queda en su sitio.
    def test_reune_lo_declarado(self):
        alfa = modulo_falso(
            "alfa",
            permisos=(Permiso("alfa.crear", "Crear alfas"),),
            emite=(Emision("alfa.creado", "Se ha creado un alfa"),),
            menu=(EntradaDeMenu("alfa.inicio", "Alfa", url="alfa:inicio", orden=20),),
            ayuda=(Ayuda("alfa.inicio", "Alfa", "Para qué sirve alfa."),),
        )
        beta = modulo_falso(
            "beta",
            escucha=(Escucha("alfa.creado", "beta.receptores.al_crear_alfa"),),
            menu=(EntradaDeMenu("beta.inicio", "Beta", url="beta:inicio", orden=10),),
        )
        nuevo = RegistroDeModulos()
        nuevo.cargar([alfa, beta])
        self.assertEqual(nuevo.errores, [])
        self.assertIn("alfa.crear", nuevo.permisos)
        self.assertEqual(len(nuevo.escuchas["alfa.creado"]), 1)
        # El menú sale ordenado por «orden», no por el orden de carga.
        self.assertEqual([entrada.codigo for entrada in nuevo.menu], ["beta.inicio", "alfa.inicio"])

    # Un código que no empieza por la etiqueta del módulo es un error.
    def test_avisa_del_prefijo_equivocado(self):
        nuevo = RegistroDeModulos()
        nuevo.cargar([modulo_falso("alfa", permisos=(Permiso("beta.crear", "…"),))])
        self.assertEqual(len(nuevo.errores), 1)
        self.assertIn("debe empezar por «alfa.»", nuevo.errores[0])

    # El mismo código declarado dos veces es un error.
    def test_avisa_de_codigos_repetidos(self):
        repetido = (Permiso("alfa.crear", "…"), Permiso("alfa.crear", "…"))
        nuevo = RegistroDeModulos()
        nuevo.cargar([modulo_falso("alfa", permisos=repetido)])
        self.assertIn("declarado dos veces", nuevo.errores[0])

    # Escuchar un eventos_sw que nadie emite es un error (casi siempre, una errata).
    def test_avisa_de_escuchas_sin_emisor(self):
        nuevo = RegistroDeModulos()
        nuevo.cargar([modulo_falso("beta", escucha=(Escucha("alfa.creadoo", "beta.r.f"),))])
        self.assertIn("ningún módulo lo emite", nuevo.errores[0])

    # Un texto de ayuda de una sección que no existe es un error.
    def test_avisa_de_ayuda_sin_seccion(self):
        nuevo = RegistroDeModulos()
        nuevo.cargar([modulo_falso("alfa", ayuda=(Ayuda("alfa.nada", "…", "…"),))])
        self.assertIn("no está en el menú", nuevo.errores[0])

    # Un módulo sin capa es un error.
    def test_avisa_si_falta_la_capa(self):
        nuevo = RegistroDeModulos()
        nuevo.cargar([modulo_falso("alfa", capa=None)])
        self.assertIn("no dice a qué capa pertenece", nuevo.errores[0])

    # contratos_de_prueba añade un módulo de mentira y, al salir del bloque, el registro vuelve a ser el real.
    def test_contratos_de_prueba_restaura_el_registro(self):
        with contratos_de_prueba(modulo_falso("alfa", permisos=(Permiso("alfa.crear", "…"),))):
            self.assertIn("alfa.crear", registro.permisos)
        self.assertNotIn("alfa.crear", registro.permisos)
        self.assertNotIn("alfa", registro.modulos)

    # El registro real de la aplicación se ha cargado al arrancar y no tiene errores.
    def test_el_registro_real_esta_limpio(self):
        self.assertTrue(registro.cargado)
        self.assertEqual(registro.errores, [])
        self.assertIn("base", registro.modulos)
