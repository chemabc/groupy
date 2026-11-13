"""
Pruebas de «Organizaciones y grupos» en un navegador de verdad (ver base/pruebas_navegador.py): el número
de «Invitaciones (N)» del menú se pone al día al navegar con htmx, sin recargar la página ni volver a
pintar el menú (base/zona.html manda el número aparte, con hx-swap-oob).
"""

from base.contrato import Ancla
from base.pruebas import contratos_de_prueba, crear_usuario_de_prueba, modulo_falso
from base.pruebas_navegador import PruebaEnElNavegador
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion, invitar

# Módulo de mentira con un ancla, para poder invitar a algo.
ALFA = modulo_falso("alfa", anclas=(Ancla("alfa.proyecto", "auth.Group", "Un proyecto de mentira"),))


class PruebasDeGruposEnElNavegador(PruebaEnElNavegador):
    """El usuario de la prueba es admin de GRU Segre (ORG Ebro), que recibe una invitación de GRU Henares."""

    # Al aceptar la invitación, el menú pasa de «(1)» a «(0)» sin recargar; la sección sigue abierta.
    def test_contador_del_menu(self):
        tajo, general = crear_organizacion("ORG Tajo", "GRU Tajo")
        henares = crear_grupo(tajo, "GRU Henares", padre=general)
        ebro, segre = crear_organizacion("ORG Ebro", "GRU Segre")
        lince = crear_usuario_de_prueba("Lince")
        admitir(lince, henares, rol=Pertenencia.ADMIN_GRUPO)
        admitir(self.usuario, segre, rol=Pertenencia.ADMIN_GRUPO)
        with contratos_de_prueba(ALFA):
            invitar("alfa.proyecto", 7, henares, segre, lince, "Hagamos algo juntos")

            self.abrir("/organizaciones/")
            contador = self.pagina.locator("#contador-gruposinvitaciones")
            self.assertEqual(contador.inner_text(), "(1)")
            # Se entra en «Invitaciones» con el menú (htmx) y se acepta.
            self.pagina.locator('nav[aria-label="Secciones"] a[data-codigo="grupos.invitaciones"]').click()
            self.pagina.locator('button[value="aceptar"]').click()
            self.pagina.wait_for_selector("text=Aceptada")
            self.assertEqual(contador.inner_text(), "(0)")
            # Solo hay un contador de invitaciones en la página (htmx lo ha sustituido, no duplicado).
            self.assertEqual(self.pagina.locator("#contador-gruposinvitaciones").count(), 1)
        self.assertEqual(self.errores, [])
