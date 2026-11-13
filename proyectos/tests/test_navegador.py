"""
Prueba del kanban en un navegador de verdad (ver base/pruebas_navegador.py): al arrastrar una tarea de
«Pendiente» a «En curso», la isla «kanban» lo guarda, también al llegar navegando con htmx; una tarea de
otra persona no se puede arrastrar; y al terminar una tarea de la que depende otra, el tablero se recarga
y la que esperaba aparece desbloqueada.
"""

from base.pruebas import crear_usuario_de_prueba
from base.pruebas_navegador import PruebaEnElNavegador
from grupos.servicios import admitir, crear_organizacion
from proyectos.models import Tarea
from proyectos.servicios import crear_proyecto, crear_tarea
from tipologias.servicios import crear_tipologia


class PruebasDelKanbanEnElNavegador(PruebaEnElNavegador):
    """Un proyecto de otra persona (Lince) con una tarea del usuario de la prueba y otra de Lince."""

    # Desde la ficha, entra en el kanban (htmx), arrastra su tarea a «En curso» y se guarda; la de Lince
    # no tiene asa (no se mueve).
    def test_kanban(self):
        _tajo, grupo = crear_organizacion("ORG Tajo", "GRU Tajo")
        lince = crear_usuario_de_prueba("Lince")
        admitir(self.usuario, grupo)
        admitir(lince, grupo)
        huerto = crear_proyecto(lince, crear_tipologia("proyecto", "Genérico"), {"titulo": "Huerto"}, grupo=grupo, visibilidad="grupo:0")
        mia = crear_tarea(lince, {"titulo": "Regar", "responsable": self.usuario}, proyecto=huerto)
        crear_tarea(lince, {"titulo": "Abonar", "responsable": lince}, proyecto=huerto)

        self.abrir(f"/proyectos/{huerto.pk}/")
        self.pagina.locator('a:has-text("Kanban")').first.click()
        tarjeta = self.pagina.locator(f'li[data-id="{mia.pk}"]')
        tarjeta.wait_for()
        self.assertEqual(self.pagina.locator("li.movible").count(), 1)
        with self.pagina.expect_response(lambda respuesta: "/proyectos/tareas/mover/" in respuesta.url) as respuesta:
            self.arrastrar(tarjeta, self.pagina.locator('ul[data-estado="en_curso"]'))
        self.assertEqual(respuesta.value.json(), {"ok": True})
        self.assertEqual(Tarea.objects.get(pk=mia.pk).estado, Tarea.EN_CURSO)
        self.assertEqual(self.errores, [])

    # «Bomba» espera a «Zanja»: al arrastrar «Zanja» a «Hecha», el servidor desbloquea «Bomba» y la isla
    # recarga el tablero, donde «Bomba» ya está en «Pendiente».
    def test_desbloquea_al_terminar(self):
        _tajo, grupo = crear_organizacion("ORG Tajo", "GRU Tajo")
        admitir(self.usuario, grupo)
        huerto = crear_proyecto(self.usuario, crear_tipologia("proyecto", "Genérico"), {"titulo": "Huerto"}, grupo=grupo, visibilidad="grupo:0")
        zanja = crear_tarea(self.usuario, {"titulo": "Zanja", "responsable": self.usuario}, proyecto=huerto)
        bomba = crear_tarea(self.usuario, {"titulo": "Bomba", "responsable": self.usuario}, proyecto=huerto, espera_a=[zanja])

        self.abrir(f"/proyectos/{huerto.pk}/kanban/")
        self.assertEqual(self.pagina.locator(f'ul[data-estado="bloqueada"] li[data-id="{bomba.pk}"]').count(), 1)
        with self.pagina.expect_navigation():
            self.arrastrar(self.pagina.locator(f'li[data-id="{zanja.pk}"]'), self.pagina.locator('ul[data-estado="hecha"]'))
        self.pagina.locator(f'ul[data-estado="pendiente"] li[data-id="{bomba.pk}"]').wait_for()
        self.assertEqual(Tarea.objects.get(pk=bomba.pk).estado, Tarea.PENDIENTE)
        self.assertEqual(self.errores, [])

    # Arrastra con el ratón paso a paso (SortableJS, con forceFallback, necesita ver el movimiento).
    def arrastrar(self, origen, destino):
        caja, meta = origen.bounding_box(), destino.bounding_box()
        raton = self.pagina.mouse
        raton.move(caja["x"] + caja["width"] / 2, caja["y"] + caja["height"] / 2)
        raton.down()
        for paso in range(1, 21):
            x = caja["x"] + caja["width"] / 2 + (meta["x"] + meta["width"] / 2 - caja["x"] - caja["width"] / 2) * paso / 20
            y = caja["y"] + caja["height"] / 2 + (meta["y"] + 20 - caja["y"] - caja["height"] / 2) * paso / 20
            raton.move(x, y)
        raton.up()
