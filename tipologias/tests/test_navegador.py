"""
Pruebas de «Configuración → Tipologías» en un navegador de verdad (ver base/pruebas_navegador.py): los
campos se ordenan arrastrándolos por el asa (componente «listaOrdenable» de interfaz.js, con SortableJS).
"""

from base.pruebas_navegador import PruebaEnElNavegador
from grupos.servicios import admitir, crear_organizacion, nombrar_admin_de_organizacion
from tipologias.models import Campo
from tipologias.servicios import crear_campo, crear_tipologia


class PruebasDeTipologiasEnElNavegador(PruebaEnElNavegador):
    """Ordenar los campos arrastrando, como admin de ORG Tajo."""

    # Arrastrar el tercer campo encima del primero lo pone el primero, y el orden queda guardado (se ve
    # igual al recargar). En un tipo común (que no puede cambiar) no hay asas.
    def test_arrastrar(self):
        tajo, grupo = crear_organizacion("ORG Tajo", "GRU Tajo")
        admitir(self.usuario, grupo)
        nombrar_admin_de_organizacion(self.usuario, tajo)
        comun = crear_tipologia("evento", "Acción")
        crear_campo(comun, "Material", Campo.TEXTO)
        barrio = crear_tipologia("evento", "Acción de barrio", padre=comun, organizacion=tajo)
        for nombre in ["Uno", "Dos", "Tres"]:
            crear_campo(barrio, nombre, Campo.TEXTO)

        self.abrir(f"/configuracion/tipologias/eventos/?t={barrio.pk}")
        lista = self.pagina.locator("[x-data='listaOrdenable'] > li")
        asas = self.pagina.locator("[x-data='listaOrdenable'] .asa")
        # Arrastre «a mano» con el ratón, en pasos, como lo hace SortableJS con forceFallback.
        origen, destino = asas.nth(2).bounding_box(), lista.nth(0).bounding_box()
        self.pagina.mouse.move(origen["x"] + 4, origen["y"] + 4)
        self.pagina.mouse.down()
        self.pagina.mouse.move(destino["x"] + 10, destino["y"] + 2, steps=15)
        # Al soltar se manda el orden nuevo al servidor: se espera su respuesta antes de mirar la base.
        with self.pagina.expect_response(lambda respuesta: "/ordenar/" in respuesta.url) as respuesta:
            self.pagina.mouse.up()
        self.assertEqual(respuesta.value.status, 204)
        self.assertEqual(list(barrio.campos.order_by("orden").values_list("nombre", flat=True)), ["Tres", "Uno", "Dos"])

        self.abrir(f"/configuracion/tipologias/eventos/?t={barrio.pk}")
        nombres = self.pagina.locator("[x-data='listaOrdenable'] > li > span.flex-1")
        self.assertEqual([texto.split(" (")[0].strip() for texto in nombres.all_inner_texts()], ["Tres", "Uno", "Dos"])
        self.abrir(f"/configuracion/tipologias/eventos/?t={comun.pk}")
        self.assertEqual(asas.count(), 0)
        self.assertEqual(self.errores, [])
