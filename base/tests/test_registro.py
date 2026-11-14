"""
Pruebas del contrato de módulo y del registro.

Crean módulos de mentira (configuraciones que no están instaladas) y comprueban que el registro reúne
bien lo que declaran y que avisa de cada error de declaración. No tocan la base de datos
(SimpleTestCase), así que son muy rápidas.
"""

from django.test import SimpleTestCase

from base.contrato import Ayuda, EntradaDeMenu, Emision, Escucha, Permiso
from base.disposicion import Pestanas
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
            menu=(EntradaDeMenu("alfa.inicio", "Alfa", url="alfa:inicio"),),
            ayuda=(Ayuda("alfa.inicio", "Alfa", "Para qué sirve alfa."),),
        )
        beta = modulo_falso(
            "beta",
            escucha=(Escucha("alfa.creado", "beta.receptores.al_crear_alfa"),),
            menu=(EntradaDeMenu("beta.inicio", "Beta", url="beta:inicio"),),
        )
        nuevo = RegistroDeModulos()
        nuevo.cargar([alfa, beta])
        self.assertEqual(nuevo.errores, [])
        self.assertIn("alfa.crear", nuevo.permisos)
        self.assertEqual(len(nuevo.escuchas["alfa.creado"]), 1)
        # Sin disposición, el menú sale en el orden de carga.
        self.assertEqual([entrada.codigo for entrada in nuevo.menu], ["alfa.inicio", "beta.inicio"])
        self.assertEqual(set(nuevo.entradas), {"alfa.inicio", "beta.inicio"})

    # La disposición decide el orden y dentro de qué sección va cada entrada, también las de otro módulo,
    # a cualquier profundidad; las subsecciones que declaraba el módulo no cuentan.
    def test_disposicion(self):
        alfa = modulo_falso(
            "alfa",
            menu=(
                EntradaDeMenu(
                    "alfa.ajustes", "Ajustes", url="alfa:a",
                    subsecciones=(EntradaDeMenu("alfa.uno", "Uno", url="alfa:uno"),),
                ),
            ),
        )
        beta = modulo_falso(
            "beta",
            menu=(
                EntradaDeMenu("beta.inicio", "Beta", url="beta:inicio"),
                EntradaDeMenu("beta.dos", "Dos", url="beta:dos"),
                EntradaDeMenu("beta.cero", "Cero", url="beta:cero"),
            ),
        )
        disposicion = (
            "beta.inicio",
            ("alfa.ajustes", ("beta.cero", ("alfa.uno", ("beta.dos",)))),
        )
        nuevo = RegistroDeModulos()
        nuevo.cargar([alfa, beta], disposicion=disposicion)
        self.assertEqual(nuevo.errores, [])
        self.assertEqual([entrada.codigo for entrada in nuevo.menu], ["beta.inicio", "alfa.ajustes"])
        ajustes = nuevo.menu[1]
        self.assertEqual([sub.codigo for sub in ajustes.subsecciones], ["beta.cero", "alfa.uno"])
        self.assertEqual([sub.codigo for sub in ajustes.subsecciones[1].subsecciones], ["beta.dos"])
        self.assertEqual([entrada.codigo for entrada in nuevo.rutas["beta:dos"]], ["alfa.ajustes", "alfa.uno", "beta.dos"])

    # Errores de la disposición: una entrada sin colocar (sale al final para no perderse), un código que
    # nadie declara, uno repetido y un elemento mal escrito.
    def test_errores_de_la_disposicion(self):
        alfa = modulo_falso(
            "alfa",
            menu=(EntradaDeMenu("alfa.uno", "Uno", url="alfa:uno"), EntradaDeMenu("alfa.dos", "Dos", url="alfa:dos")),
        )
        nuevo = RegistroDeModulos()
        nuevo.cargar([alfa], disposicion=("alfa.uno", "alfa.nada", "alfa.uno", ("alfa.uno", "alfa.dos")))
        errores = " ".join(nuevo.errores)
        self.assertIn("«alfa.dos» no está colocada", errores)
        self.assertIn("nombra «alfa.nada», pero ningún módulo", errores)
        self.assertIn("«alfa.uno» está dos veces", errores)
        self.assertIn("está mal escrito", errores)
        self.assertEqual([entrada.codigo for entrada in nuevo.menu], ["alfa.uno", "alfa.dos"])

    # La entrada con panel_de_ayuda queda apuntada (ya con sus subsecciones colocadas); dos es un error.
    def test_entrada_de_ayuda(self):
        ayuda = EntradaDeMenu("alfa.ayuda", "Ayuda", url="alfa:a", panel_de_ayuda=True)
        hija = EntradaDeMenu("alfa.hija", "Hija", url="alfa:h")
        nuevo = RegistroDeModulos()
        nuevo.cargar([modulo_falso("alfa", menu=(ayuda, hija))], disposicion=(("alfa.ayuda", ("alfa.hija",)),))
        self.assertEqual(nuevo.entrada_de_ayuda.codigo, "alfa.ayuda")
        self.assertEqual([sub.codigo for sub in nuevo.entrada_de_ayuda.subsecciones], ["alfa.hija"])
        otra = EntradaDeMenu("alfa.otra", "Otra", url="alfa:o", panel_de_ayuda=True)
        nuevo.cargar([modulo_falso("alfa", menu=(ayuda, otra))])
        self.assertIn("varias entradas del menú con panel_de_ayuda", nuevo.errores[0])

    # El menú real: «Ayuda» va antes que «Configuración de mi cuenta», y «Desarrollo y mantenimiento», al
    # final (a petición de la persona usuaria, 14 de noviembre de 2026).
    # Y va en tres bloques: lo propio, «Administrar» y «Plataforma» (14 de noviembre de 2026).
    def test_final_del_menu_real(self):
        self.assertEqual([bloque.titulo for bloque, _entradas in registro.bloques], ["", "Administrar", "Plataforma"])
        propio = [entrada.codigo for entrada in registro.bloques[0][1]]
        self.assertEqual(propio[-2:], ["ayuda.ayuda", "usuarios.cuenta"])
        self.assertEqual(registro.bloques[2][1][-1].codigo, "mantenimiento.desarrollo")
        self.assertEqual(registro.entrada_de_ayuda.codigo, "ayuda.ayuda")

    # Pestanas: la entrada queda marcada (en_pestanas) con sus subsecciones, aunque sean de otro módulo.
    def test_pestanas(self):
        madre = EntradaDeMenu("alfa.madre", "Madre", url="alfa:a")
        hija = EntradaDeMenu("beta.hija", "Hija", url="beta:h")
        nuevo = RegistroDeModulos()
        nuevo.cargar([modulo_falso("alfa", menu=(madre,)), modulo_falso("beta", menu=(hija,))], disposicion=(Pestanas("alfa.madre", ("beta.hija",)),))
        self.assertEqual(nuevo.errores, [])
        self.assertTrue(nuevo.menu[0].en_pestanas)
        self.assertEqual([sub.codigo for sub in nuevo.menu[0].subsecciones], ["beta.hija"])

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
