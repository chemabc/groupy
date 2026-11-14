"""
Pruebas del componente de árboles de proyectos (proyectos/arboles.py): cómo cuelga cada proyecto, quién
participa (amarillo), el proyecto que se mira (rojo) y las tareas plegadas con «(hechas/totales)».

Usa la estructura de proyectos/tests/test_proyectos.py (ORG Tajo: GRU Tajo ⊃ GRU Henares ⊃ GRU Sorbe;
Nutria y Lince en GRU Henares).
"""

from proyectos.arboles import arboles_de_proyectos
from proyectos.models import Proyecto, Tarea
from proyectos.servicios import crear_proyecto, crear_tarea, editar_tarea

from .test_proyectos import PruebaDeProyectos


class PruebasDeArboles(PruebaDeProyectos):
    """Huerto (de Nutria) ⊃ Riego (de Lince); Semáforo (de Lince), suelto."""

    # Crea los tres proyectos y dos tareas en Riego, una hecha.
    def setUp(self):
        super().setUp()
        self.huerto = self.proyecto("Huerto")
        self.riego = crear_proyecto(self.lince, self.generico, {"titulo": "Riego"}, grupo=self.henares, visibilidad="grupo:0", padre=self.huerto)
        self.semaforo = crear_proyecto(self.lince, self.generico, {"titulo": "Semáforo"}, grupo=self.henares, visibilidad="grupo:0")
        hecha = crear_tarea(self.lince, {"titulo": "Comprar goteros", "responsable": self.nutria}, proyecto=self.riego)
        editar_tarea(self.lince, hecha, {"estado": Tarea.HECHA})
        crear_tarea(self.lince, {"titulo": "Montar", "responsable": self.lince}, proyecto=self.riego)

    # Dos árboles (Huerto con Riego dentro, y Semáforo), los dos de GRU Henares. Nutria participa en Huerto
    # (lo creó) y en Riego (tiene una tarea), no en Semáforo. Riego lleva sus tareas: 1 de 2 hechas.
    def test_estructura(self):
        lista = list(Proyecto.objects.select_related("grupo__organizacion", "tipologia"))
        arboles = arboles_de_proyectos(self.nutria, lista, actual=self.riego.pk)
        self.assertEqual([arbol.raiz.proyecto.titulo for arbol in arboles], ["Huerto", "Semáforo"])
        self.assertEqual(arboles[0].grupo, self.henares)
        huerto = arboles[0].raiz
        (riego,) = huerto.hijos
        self.assertEqual((huerto.participa, riego.participa, arboles[1].raiz.participa), (True, True, False))
        self.assertEqual((riego.actual, huerto.actual), (True, False))
        self.assertEqual((riego.hechas, len(riego.tareas)), (1, 2))

    # La lista pinta la rejilla, el «(1/2)» con su flecha y las tareas dentro del desplegable; la ficha
    # de Riego, su árbol con Riego en recuadro rojo.
    def test_pantallas(self):
        lista = self.client.get("/proyectos/")
        self.assertContains(lista, "(1/2)")
        self.assertContains(lista, "<details", count=1)
        self.assertContains(lista, "Comprar goteros")
        self.assertContains(lista, "arbol-coordina")
        ficha = self.client.get(f"/proyectos/{self.riego.pk}/")
        self.assertContains(ficha, 'aria-current="page">Riego</a>')
        self.assertContains(ficha, "El proyecto que miras")
