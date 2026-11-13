"""
Pruebas del módulo «tipologias»: reglas del árbol, herencia de campos, formulario de los campos, quién
puede cambiar qué y la pantalla «Configuración → Tipologías» (con su número de consultas).
"""

import json

from django.core.exceptions import ValidationError
from django.test import TestCase

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from grupos.servicios import admitir, crear_organizacion, nombrar_admin_de_organizacion
from tipologias.models import Campo, Tipologia
from tipologias.servicios import (
    a_json,
    arbol,
    borrar_tipologia,
    campos_de,
    crear_campo,
    crear_tarea_modelo,
    crear_tipologia,
    formulario_de,
    ordenar_campos,
    tareas_modelo_de,
)

EVENTO = Tipologia.EVENTO
PROYECTO = Tipologia.PROYECTO


class PruebasDelArbol(TestCase):
    """«Acción» común, con «Concentración» común debajo, y dos organizaciones."""

    # Árbol de prueba: Acción (asistentes) → Concentración (lugar, convocatoria).
    @classmethod
    def setUpTestData(cls):
        cls.tajo, _ = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.ebro, _ = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.accion = crear_tipologia(EVENTO, "Acción")
        cls.concentracion = crear_tipologia(EVENTO, "Concentración", padre=cls.accion)
        crear_campo(cls.accion, "Número de asistentes", Campo.NUMERO, obligatorio=True)
        crear_campo(cls.concentracion, "Lugar", Campo.TEXTO)
        crear_campo(cls.concentracion, "Convocatoria", Campo.LISTA, opciones="Abierta\nCerrada")

    # Un subtipo pide los campos de su tipo primero y después los suyos, en su orden.
    def test_herencia(self):
        self.assertEqual([c.clave for c in campos_de(self.concentracion)], ["numero_de_asistentes", "lugar", "convocatoria"])
        self.assertEqual([c.clave for c in campos_de(self.accion)], ["numero_de_asistentes"])

    # El árbol pone cada tipo debajo de su padre, con su camino; cada organización ve las comunes y las suyas.
    def test_arbol_y_visibilidad(self):
        crear_tipologia(EVENTO, "Acción de barrio", padre=self.accion, organizacion=self.tajo)
        caminos = [rama.camino for rama in arbol(EVENTO, [self.tajo.pk])]
        self.assertEqual(caminos, ["Acción", "Acción › Acción de barrio", "Acción › Concentración"])
        self.assertNotIn("Acción › Acción de barrio", [rama.camino for rama in arbol(EVENTO, [self.ebro.pk])])

    # Reglas del árbol: misma familia, sin círculos, y un tipo de una organización no tiene hijas de otra.
    def test_reglas(self):
        with self.assertRaisesMessage(ValidationError, "misma familia"):
            crear_tipologia(Tipologia.PROYECTO, "Mala", padre=self.accion)
        de_tajo = crear_tipologia(EVENTO, "De Tajo", padre=self.accion, organizacion=self.tajo)
        self.assertEqual(crear_tipologia(EVENTO, "Hija", padre=de_tajo, organizacion=self.ebro).organizacion, self.tajo)
        self.accion.padre = self.concentracion
        with self.assertRaisesMessage(ValidationError, "uno de sus subtipos"):
            self.accion.full_clean()

    # Nombres repetidos entre hermanas: no con una común ni con una de la misma organización; sí entre
    # organizaciones distintas (no se ven entre ellas).
    def test_nombres_repetidos(self):
        with self.assertRaisesMessage(ValidationError, "Ya hay un tipo con ese nombre"):
            crear_tipologia(EVENTO, "concentracion", padre=self.accion, organizacion=self.tajo)
        crear_tipologia(EVENTO, "Acción de barrio", padre=self.accion, organizacion=self.tajo)
        crear_tipologia(EVENTO, "Acción de barrio", padre=self.accion, organizacion=self.ebro)
        with self.assertRaisesMessage(ValidationError, "Ya hay un tipo con ese nombre"):
            crear_tipologia(EVENTO, "Acción de barrio", padre=self.accion, organizacion=self.tajo)

    # Un campo no puede repetir la clave de otro de su rama (se heredan) y una lista pide dos opciones.
    def test_campos(self):
        with self.assertRaisesMessage(ValidationError, "Ya hay un campo"):
            crear_campo(self.concentracion, "Número de asistentes", Campo.TEXTO)
        with self.assertRaisesMessage(ValidationError, "al menos dos opciones"):
            crear_campo(self.accion, "Tipo", Campo.LISTA, opciones="Una")

    # Ordenar pone los campos en el orden dado e ignora los que no son de la tipología.
    def test_ordenar(self):
        lugar, convocatoria = self.concentracion.campos.order_by("orden")
        ordenar_campos(self.concentracion, [convocatoria.pk, 99999, lugar.pk])
        self.assertEqual([c.nombre for c in campos_de(self.concentracion)], ["Número de asistentes", "Convocatoria", "Lugar"])

    # El formulario de los campos comprueba los obligatorios y las listas, y a_json() deja los valores guardables.
    def test_formulario(self):
        formulario = formulario_de(self.concentracion, {"numero_de_asistentes": "", "convocatoria": "Otra"})
        self.assertFalse(formulario.is_valid())
        self.assertEqual(set(formulario.errors), {"numero_de_asistentes", "convocatoria"})
        formulario = formulario_de(self.concentracion, {"numero_de_asistentes": "40", "lugar": "Plaza", "convocatoria": "Abierta"})
        self.assertTrue(formulario.is_valid())
        self.assertEqual(a_json(formulario.cleaned_data), {"numero_de_asistentes": "40", "lugar": "Plaza", "convocatoria": "Abierta"})

    # No se borra un tipo con subtipos; sí uno sin ellos, con sus campos.
    def test_borrar(self):
        with self.assertRaisesMessage(ValidationError, "subtipos"):
            borrar_tipologia(self.accion)
        borrar_tipologia(self.concentracion)
        self.assertFalse(Campo.objects.filter(clave="lugar").exists())


class PruebasDeLaPantalla(PruebaDePantalla):
    """La pantalla con un admin de ORG Tajo: ve y cambia lo suyo, no lo común ni lo de otras."""

    # El usuario de la sesión es admin de ORG Tajo; hay un tipo común y uno de ORG Ebro.
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tajo, grupo_tajo = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.ebro, _ = crear_organizacion("ORG Ebro", "GRU Ebro")
        admitir(cls.usuario, grupo_tajo)
        nombrar_admin_de_organizacion(cls.usuario, cls.tajo)
        cls.accion = crear_tipologia(EVENTO, "Acción")
        crear_campo(cls.accion, "Material", Campo.TEXTO)
        cls.de_ebro = crear_tipologia(EVENTO, "Secreto de Ebro", padre=cls.accion, organizacion=cls.ebro)
        cls.direccion = "/configuracion/tipologias/eventos/"

    # Sin el permiso, la pantalla explica por qué no se puede entrar.
    def test_sin_permiso(self):
        self.client.force_login(crear_usuario_de_prueba("Otra"))
        self.assertEqual(self.client.get(self.direccion).status_code, 403)

    # Ve las comunes y las de su organización, nunca las de otra, ni aunque ponga su número en la dirección.
    def test_lo_que_ve(self):
        respuesta = self.client.get(f"{self.direccion}?t={self.de_ebro.pk}")
        self.assertContains(respuesta, "Acción")
        self.assertNotContains(respuesta, "Secreto de Ebro")

    # Crea un subtipo propio de un tipo común y le añade un campo; no puede cambiar el común.
    def test_crear_y_cambiar(self):
        respuesta = self.client.post(
            self.direccion, {"accion": "crear_tipologia", "nombre": "Acción de barrio", "padre": self.accion.pk, "organizacion": self.tajo.pk}
        )
        barrio = Tipologia.objects.get(nombre="Acción de barrio")
        self.assertEqual(barrio.organizacion, self.tajo)
        self.assertRedirects(respuesta, f"{self.direccion}?t={barrio.pk}", fetch_redirect_response=False)
        self.client.post(self.direccion, {"accion": "crear_campo", "t": barrio.pk, "nombre": "Barrio", "tipo": Campo.TEXTO})
        self.assertEqual([c.nombre for c in campos_de(barrio)], ["Material", "Barrio"])
        respuesta = self.client.post(self.direccion, {"accion": "borrar_tipologia", "t": self.accion.pk})
        self.assertContains(respuesta, "solo lo cambia el superadmin")
        self.assertTrue(Tipologia.objects.filter(pk=self.accion.pk).exists())

    # Un admin de organización no puede crear tipos comunes.
    def test_no_crea_comunes(self):
        self.client.post(self.direccion, {"accion": "crear_tipologia", "nombre": "Común falsa", "organizacion": ""})
        self.assertFalse(Tipologia.objects.filter(nombre="Común falsa").exists())

    # Ordenar por la dirección de arrastre: lo suyo sí; lo común, no.
    def test_ordenar(self):
        barrio = crear_tipologia(EVENTO, "Acción de barrio", padre=self.accion, organizacion=self.tajo)
        uno, dos = crear_campo(barrio, "Uno", Campo.TEXTO), crear_campo(barrio, "Dos", Campo.TEXTO)
        cuerpo = json.dumps({"tipologia": barrio.pk, "orden": [str(dos.pk), str(uno.pk)]})
        respuesta = self.client.post("/configuracion/tipologias/ordenar/", cuerpo, content_type="application/json")
        self.assertEqual(respuesta.status_code, 204)
        self.assertEqual(list(barrio.campos.order_by("orden").values_list("nombre", flat=True)), ["Dos", "Uno"])
        cuerpo = json.dumps({"tipologia": self.accion.pk, "orden": []})
        respuesta = self.client.post("/configuracion/tipologias/ordenar/", cuerpo, content_type="application/json")
        self.assertEqual(respuesta.status_code, 403)

    # Número de consultas, con un tipo elegido: no crece con más tipos ni con más campos.
    def test_consultas(self):
        barrio = crear_tipologia(EVENTO, "Acción de barrio", padre=self.accion, organizacion=self.tajo)
        crear_campo(barrio, "Barrio", Campo.TEXTO)

        # Añade más tipos al árbol y más campos al elegido.
        def mas_datos():
            for numero in range(5):
                hija = crear_tipologia(EVENTO, f"Subtipo {numero}", padre=barrio)
                crear_campo(hija, f"Dato {numero}", Campo.TEXTO)
                crear_campo(barrio, f"Otro {numero}", Campo.NUMERO)

        self.comprobar_consultas(f"{self.direccion}?t={barrio.pk}", 4, mas_datos)


class PruebasDeTareasModelo(PruebaDePantalla):
    """Tareas modelo de los tipos de proyecto: se heredan, se añaden y quitan en la pantalla."""

    # El usuario de la sesión es admin de ORG Tajo; «Acción» (común) propone dos tareas.
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tajo, grupo_tajo = crear_organizacion("ORG Tajo", "GRU Tajo")
        admitir(cls.usuario, grupo_tajo)
        nombrar_admin_de_organizacion(cls.usuario, cls.tajo)
        cls.accion = crear_tipologia(PROYECTO, "Preparación de acción")
        crear_tarea_modelo(cls.accion, "Pedir permiso", dias=7)
        crear_tarea_modelo(cls.accion, "Hacer el cartel", espera_a_la_anterior=True)
        cls.direccion = "/configuracion/tipologias/proyectos/"

    # Un subtipo propone las de arriba y las suyas, en orden; los tipos de evento no tienen.
    def test_herencia_y_reglas(self):
        barrio = crear_tipologia(PROYECTO, "Acción de barrio", padre=self.accion, organizacion=self.tajo)
        crear_tarea_modelo(barrio, "Hablar con los comercios")
        self.assertEqual([t.titulo for t in tareas_modelo_de(barrio)], ["Pedir permiso", "Hacer el cartel", "Hablar con los comercios"])
        with self.assertRaisesMessage(ValidationError, "solo de los tipos de proyecto"):
            crear_tarea_modelo(crear_tipologia(EVENTO, "Reunión"), "Algo")

    # El admin añade y quita tareas modelo en lo suyo; en lo común, no.
    def test_pantalla(self):
        barrio = crear_tipologia(PROYECTO, "Acción de barrio", padre=self.accion, organizacion=self.tajo)
        self.client.post(self.direccion, {"accion": "crear_tarea_modelo", "t": barrio.pk, "titulo": "Buzonear", "dias": "3", "espera_a_la_anterior": "on"})
        nueva = barrio.tareas_modelo.get()
        self.assertEqual((nueva.titulo, nueva.dias, nueva.espera_a_la_anterior), ("Buzonear", 3, True))
        respuesta = self.client.get(f"{self.direccion}?t={barrio.pk}")
        self.assertContains(respuesta, "heredada de Preparación de acción")
        self.client.post(self.direccion, {"accion": "borrar_tarea_modelo", "t": barrio.pk, "tarea_modelo": nueva.pk})
        self.assertFalse(barrio.tareas_modelo.exists())
        respuesta = self.client.post(self.direccion, {"accion": "crear_tarea_modelo", "t": self.accion.pk, "titulo": "Colada"})
        self.assertContains(respuesta, "solo lo cambia el superadmin")

    # Número de consultas con un tipo de proyecto elegido: no crece con más tareas modelo.
    def test_consultas(self):
        barrio = crear_tipologia(PROYECTO, "Acción de barrio", padre=self.accion, organizacion=self.tajo)

        # Añade más tareas modelo.
        def mas_datos():
            for numero in range(5):
                crear_tarea_modelo(barrio, f"Tarea {numero}")

        self.comprobar_consultas(f"{self.direccion}?t={barrio.pk}", 5, mas_datos)
