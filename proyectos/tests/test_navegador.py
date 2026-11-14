"""
Prueba del kanban en un navegador de verdad (ver base/pruebas_navegador.py): al arrastrar una tarea de
«Pendiente» a «En curso», la isla «kanban» lo guarda, también al llegar navegando con htmx; una tarea de
otra persona no se puede arrastrar; y al terminar una tarea de la que depende otra, el tablero se recarga
y la que esperaba aparece desbloqueada.
"""

from base.pruebas import crear_usuario_de_prueba
from base.pruebas_navegador import PruebaEnElNavegador
from grupos.servicios import admitir, crear_grupo, crear_organizacion
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


class PruebasDelSelectorDePersonasEnElNavegador(PruebaEnElNavegador):
    """
    El selector de personas en el formulario de una tarea nueva: GRU Tajo ⊃ GRU Henares ⊃ GRU Sorbe. El
    usuario de la prueba y Lince están en Henares, Garza en Sorbe y Zorro en Tajo. El proyecto se ve en
    Henares (y sus subgrupos), así que Zorro no sale.
    """

    # Crea los grupos, las personas y el proyecto, y abre el formulario de tarea nueva.
    def preparar(self):
        self.tajo, raiz = crear_organizacion("ORG Tajo", "GRU Tajo")
        henares = crear_grupo(self.tajo, "GRU Henares", padre=raiz)
        sorbe = crear_grupo(self.tajo, "GRU Sorbe", padre=henares)
        self.garza, lince, zorro = (crear_usuario_de_prueba(alias) for alias in ("Garza", "Lince", "Zorro"))
        admitir(self.usuario, henares)
        admitir(lince, henares)
        admitir(self.garza, sorbe)
        admitir(zorro, raiz)
        self.huerto = crear_proyecto(self.usuario, crear_tipologia("proyecto", "Genérico"), {"titulo": "Huerto"}, grupo=henares, visibilidad="grupo:0")
        self.abrir(f"/proyectos/tareas/nueva/?proyecto={self.huerto.pk}")
        self.pagina.locator('input[name="titulo"]').fill("Comprar semillas")

    # Responsable: la ventana enseña los bloques por cercanía (sin Zorro); el buscador filtra mientras se
    # escribe; al pulsar a Garza se cierra y queda su pastilla. Colaboran: se eligen dos. Al crear, se
    # guardan.
    def test_elegir(self):
        self.preparar()
        self.pagina.locator("#id_responsable").click()
        ventana = self.pagina.get_by_role("dialog", name="Elegir una persona")
        ventana.get_by_text("Aquí: GRU Henares").wait_for()
        self.assertTrue(ventana.get_by_text("En sus subgrupos").is_visible())
        self.assertEqual(ventana.get_by_text("Zorro").count(), 0)
        ventana.get_by_placeholder("Buscar por alias o por grupo…").fill("gar")
        self.assertFalse(ventana.get_by_role("radio", name="Lince").is_visible())
        ventana.get_by_role("radio", name="Garza").click()
        ventana.wait_for(state="hidden")
        self.pagina.locator('input[type="hidden"][name="responsable"][value="Garza"]').wait_for(state="attached")
        self.pagina.locator("#id_colaboradores").click()
        varias = self.pagina.get_by_role("dialog", name="Elegir personas")
        varias.get_by_role("checkbox", name="Lince").click()
        varias.get_by_role("checkbox", name="Prueba").click()
        self.assertIn("2 elegidas", varias.inner_text())
        varias.get_by_role("button", name="Listo").click()
        self.pagina.get_by_role("button", name="Crear").click()
        self.pagina.wait_for_url(f"**/proyectos/{self.huerto.pk}/")
        tarea = Tarea.objects.get(titulo="Comprar semillas")
        self.assertEqual(tarea.responsable, self.garza)
        self.assertEqual(sorted(p.alias for p in tarea.colaboradores.all()), ["Lince", "Prueba"])
        self.assertEqual(self.errores, [])

    # Si la organización cierra la lista de miembros, la ventana solo deja escribir el alias exacto; uno
    # que no ve el proyecto da error al guardar, sin más pistas.
    def test_lista_cerrada(self):
        self.preparar()
        self.tajo.miembros_ven_miembros = False
        self.tajo.save()
        self.pagina.locator("#id_responsable").click()
        ventana = self.pagina.get_by_role("dialog", name="Elegir una persona")
        ventana.get_by_text("Tu organización no enseña la lista").wait_for()
        ventana.get_by_label("Alias exacto").fill("Zorro")
        ventana.get_by_role("button", name="Añadir").click()
        self.pagina.get_by_role("button", name="Crear").click()
        self.pagina.get_by_text("No está entre quienes ven esto: Zorro.").wait_for()
        self.assertFalse(Tarea.objects.exists())
        self.assertEqual(self.errores, [])
