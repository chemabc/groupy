"""
Pruebas de «proyectos»: crear proyectos y subproyectos a cualquier profundidad (y verlos en árbol), quién
los ve (también los personales, ni el superadmin) y quién los gestiona (quien crea o coordina un
antecesor, la administración del grupo), las tareas (responsable que ve el proyecto, aviso, kanban con
las de los subproyectos, mover), su paso por el calendario y lo que cuestan las pantallas.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares ⊃ GRU Sorbe) con Lince admin de GRU Henares, Nutria en GRU
Henares (la sesión), Garza en GRU Sorbe y Zorro en GRU Tajo; Erizo en ORG Ebro.
"""

import json
from datetime import date

from django.apps import apps
from django.core.exceptions import ValidationError

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from eventos_sw.servicios import procesar_bandeja
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion
from proyectos.models import Proyecto, Tarea
from proyectos.servicios import apuntar, crear_proyecto, crear_tarea
from tipologias.servicios import crear_tipologia

# Tabla de notificaciones de «comunicaciones» (otro módulo funcional: se busca por su nombre).
Notificacion = apps.get_model("comunicaciones", "Notificacion")


# Datos de un proyecto para el formulario.
def datos(**otros):
    base = {"titulo": "Huerto", "objetivo_general": "", "objetivos_especificos": "", "alcance": "", "riesgos": "", "inicio": "", "limite": "", "visibilidad": "grupo:0"}
    base.update(otros)
    return base


class PruebaDeProyectos(PruebaDePantalla):
    """Base con la estructura del principio del fichero."""

    # Crea la estructura y la tipología «Genérico».
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        cls.sorbe = crear_grupo(cls.tajo, "GRU Sorbe", padre=cls.henares)
        cls.ebro, cls.gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.lince = crear_usuario_de_prueba("Lince")
        cls.nutria = crear_usuario_de_prueba("Nutria")
        cls.garza = crear_usuario_de_prueba("Garza")
        cls.zorro = crear_usuario_de_prueba("Zorro")
        cls.erizo = crear_usuario_de_prueba("Erizo")
        admitir(cls.lince, cls.henares, rol=Pertenencia.ADMIN_GRUPO)
        admitir(cls.nutria, cls.henares)
        admitir(cls.garza, cls.sorbe)
        admitir(cls.zorro, cls.general)
        admitir(cls.erizo, cls.gru_ebro)
        cls.generico = crear_tipologia("proyecto", "Genérico")
        cls.usuario = cls.nutria

    # Inicia sesión como otra persona.
    def como(self, usuario):
        self.client.force_login(usuario)

    # Un proyecto de Nutria en GRU Henares (o un subproyecto, con «padre»).
    def proyecto(self, titulo="Huerto", padre=None, visibilidad="grupo:0", **otros):
        datos_del_servicio = {"titulo": titulo, **otros}
        return crear_proyecto(self.nutria, self.generico, datos_del_servicio, grupo=self.henares, visibilidad=visibilidad, padre=padre)


class PruebasDeSubproyectos(PruebaDeProyectos):
    """Proyectos dentro de proyectos."""

    # Desde la pantalla: proyecto, subproyecto y sub-subproyecto. Todos comparten raíz y salen en árbol.
    def test_tres_niveles(self):
        url = f"/proyectos/nuevo/?grupo={self.henares.pk}&tipologia={self.generico.pk}"
        self.client.post(url, datos(titulo="Huerto"))
        huerto = Proyecto.objects.get()
        self.client.post(f"/proyectos/nuevo/?padre={huerto.pk}&tipologia={self.generico.pk}", datos(titulo="Riego"))
        riego = Proyecto.objects.get(titulo="Riego")
        respuesta = self.client.post(f"/proyectos/nuevo/?padre={riego.pk}&tipologia={self.generico.pk}", datos(titulo="Bomba solar"))
        bomba = Proyecto.objects.get(titulo="Bomba solar")
        self.assertRedirects(respuesta, f"/proyectos/{bomba.pk}/")
        self.assertEqual({p.raiz_id for p in Proyecto.objects.all()}, {huerto.pk})
        self.assertEqual((bomba.padre, bomba.grupo), (riego, self.henares))
        pagina = self.client.get("/proyectos/").content.decode()
        self.assertLess(pagina.index("Huerto"), pagina.index("Riego"))
        self.assertLess(pagina.index("Riego"), pagina.index("Bomba solar"))
        self.assertIn("calc(2 * 1.25rem)", pagina)
        ficha = self.client.get(f"/proyectos/{bomba.pk}/")
        self.assertContains(ficha, f'href="/proyectos/{huerto.pk}/"')
        self.assertContains(self.client.get(f"/proyectos/{huerto.pk}/"), "Bomba solar")

    # Quién gestiona: Garza (de un subgrupo) no crea subproyectos; Lince (admin del grupo) sí; con la
    # coordinación del principal, Garza también gestiona un subproyecto suyo.
    def test_quien_gestiona(self):
        huerto = self.proyecto()
        riego = self.proyecto("Riego", padre=huerto)
        self.como(self.garza)
        self.assertEqual(self.client.get(f"/proyectos/nuevo/?padre={riego.pk}").status_code, 403)
        self.assertNotContains(self.client.get(f"/proyectos/{riego.pk}/"), "+ Subproyecto")
        apuntar(self.nutria, huerto, self.garza, "proyectos.coordinacion")
        self.assertContains(self.client.get(f"/proyectos/{riego.pk}/"), "+ Subproyecto")
        with self.assertRaises(ValidationError):
            apuntar(self.zorro, huerto, self.zorro, "proyectos.coordinacion")
        self.como(self.lince)
        self.assertEqual(self.client.get(f"/proyectos/nuevo/?padre={riego.pk}").status_code, 200)

    # Un subproyecto privado no se ve aunque se vea su padre; desde uno visible bajo uno privado, el
    # camino dice que hay un proyecto que no se ve.
    def test_visibilidad(self):
        huerto = self.proyecto()
        secreto = self.proyecto("Secreto", padre=huerto, visibilidad="privado")
        abierto = self.proyecto("Abierto", padre=secreto)
        self.como(self.garza)
        self.assertNotContains(self.client.get(f"/proyectos/{huerto.pk}/"), "Secreto")
        self.assertEqual(self.client.get(f"/proyectos/{secreto.pk}/").status_code, 403)
        self.assertContains(self.client.get(f"/proyectos/{abierto.pk}/"), "(un proyecto que no puedes ver)")
        self.como(self.zorro)
        self.assertEqual(self.client.get(f"/proyectos/{huerto.pk}/").status_code, 403)

    # Lo personal: sus subproyectos también lo son; ni el superadmin lo ve.
    def test_personal(self):
        url = f"/proyectos/nuevo/?personal=1&tipologia={self.generico.pk}"
        self.client.post(url, datos(titulo="Mi mudanza"))
        mudanza = Proyecto.objects.get()
        self.client.post(f"/proyectos/nuevo/?padre={mudanza.pk}&tipologia={self.generico.pk}", datos(titulo="Cajas"))
        cajas = Proyecto.objects.get(titulo="Cajas")
        self.assertEqual((mudanza.personal, cajas.personal, cajas.grupo), (True, True, None))
        self.assertContains(self.client.get("/proyectos/personales/"), "Cajas")
        self.assertNotContains(self.client.get("/proyectos/"), "Mi mudanza")
        self.como(crear_usuario_de_prueba("superadmin", es_superadmin=True))
        self.assertEqual(self.client.get(f"/proyectos/{cajas.pk}/").status_code, 403)


class PruebasDeTareas(PruebaDeProyectos):
    """Tareas, kanban y calendario."""

    # Una tarea encargada a Garza le llega como aviso; a Erizo (que no ve el proyecto), no se puede. En un
    # proyecto privado, la responsable pasa a verlo.
    def test_responsable(self):
        huerto = self.proyecto()
        respuesta = self.client.post(f"/proyectos/tareas/nueva/?proyecto={huerto.pk}", {"titulo": "Comprar semillas", "descripcion": "", "limite": "", "estado": "pendiente", "responsable": "garza", "colaboradores": "Lince"})
        self.assertRedirects(respuesta, f"/proyectos/{huerto.pk}/")
        tarea = Tarea.objects.get()
        self.assertEqual((tarea.responsable, list(tarea.colaboradores.all())), (self.garza, [self.lince]))
        procesar_bandeja()
        self.assertEqual(Notificacion.objects.get(tipo="proyectos.tarea_asignada").usuario, self.garza)
        self.assertContains(self.client.post(f"/proyectos/tareas/nueva/?proyecto={huerto.pk}", {"titulo": "X", "estado": "pendiente", "responsable": "Erizo"}), "no ve el proyecto")
        self.assertContains(self.client.post(f"/proyectos/tareas/nueva/?proyecto={huerto.pk}", {"titulo": "X", "estado": "pendiente", "responsable": "Nadie"}), "No hay nadie con el alias")
        privado = self.proyecto("Privado", visibilidad="privado")
        crear_tarea(self.nutria, {"titulo": "Algo", "responsable": self.zorro}, proyecto=privado)
        self.como(self.zorro)
        self.assertEqual(self.client.get(f"/proyectos/{privado.pk}/").status_code, 200)

    # El kanban del proyecto trae las tareas de sus subproyectos; Garza mueve la suya (y se guarda el
    # orden) pero no la de Nutria.
    def test_kanban(self):
        huerto = self.proyecto()
        riego = self.proyecto("Riego", padre=huerto)
        de_nutria = crear_tarea(self.nutria, {"titulo": "Regar", "responsable": self.nutria}, proyecto=huerto)
        de_garza = crear_tarea(self.nutria, {"titulo": "Tubos", "responsable": self.garza}, proyecto=riego)
        respuesta = self.client.get(f"/proyectos/{huerto.pk}/kanban/")
        self.assertContains(respuesta, "Tubos")
        self.assertContains(respuesta, "Regar")
        self.como(self.garza)
        mover = lambda tarea, estado, orden: self.client.post("/proyectos/tareas/mover/", json.dumps({"tarea": tarea.pk, "estado": estado, "orden": orden}), content_type="application/json")  # noqa: E731
        self.assertEqual(mover(de_garza, "en_curso", [de_garza.pk]).json(), {"ok": True})
        self.assertEqual(Tarea.objects.get(pk=de_garza.pk).estado, Tarea.EN_CURSO)
        self.assertEqual(mover(de_nutria, "hecha", [de_nutria.pk]).status_code, 400)
        self.assertEqual(mover(de_garza, "inventado", []).status_code, 400)
        self.assertContains(self.client.get("/proyectos/tareas/kanban/"), "Tubos")

    # Las fechas límite salen en el calendario (proyecto y tarea), y quien lo creó puede arrastrarlas.
    def test_calendario(self):
        huerto = self.proyecto(limite=date(2030, 3, 20))
        crear_tarea(self.nutria, {"titulo": "Semillas", "responsable": self.nutria, "limite": date(2030, 3, 10)}, proyecto=huerto)
        fechas = self.client.get("/calendario/datos/?start=2030-03-01&end=2030-04-01").json()["fechas"]
        titulos = {f["title"]: f for f in fechas}
        self.assertEqual((titulos["Límite: Huerto"]["start"], titulos["Límite: Huerto"]["editable"]), ("2030-03-20", True))
        self.assertEqual(titulos["Semillas"]["categoria"], "Tareas")
        mover = {"fuente": "proyectos.tareas", "id": Tarea.objects.get().pk, "todo_el_dia": "1", "inicio": "2030-03-12", "fin": "2030-03-13"}
        self.assertEqual(self.client.post("/calendario/mover/", mover).json(), {"ok": True})
        self.assertEqual(Tarea.objects.get().limite, date(2030, 3, 12))

    # Tareas sueltas de un grupo y personales.
    def test_sueltas_y_personales(self):
        suelta = crear_tarea(self.nutria, {"titulo": "Limpiar el local", "responsable": self.nutria}, grupo=self.henares, visibilidad="grupo:0")
        personal = crear_tarea(self.lince, {"titulo": "Mía", "responsable": self.nutria}, personal=True)
        self.assertEqual(personal.responsable, self.lince)
        self.como(self.garza)
        self.assertEqual(self.client.get(f"/proyectos/tareas/{suelta.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/proyectos/tareas/{personal.pk}/").status_code, 403)
        self.como(self.zorro)
        self.assertEqual(self.client.get(f"/proyectos/tareas/{suelta.pk}/").status_code, 403)


class PruebasDeConsultas(PruebaDeProyectos):
    """Cada pantalla cuesta lo mismo con pocas filas que con muchas."""

    # Listas: más proyectos y subproyectos.
    def test_listas(self):
        huerto = self.proyecto()
        self.comprobar_consultas("/proyectos/", 2, lambda: self.proyecto("Otro", padre=huerto))
        self.comprobar_consultas("/proyectos/personales/", 3, lambda: crear_proyecto(self.nutria, self.generico, {"titulo": "P"}, personal=True))
        self.comprobar_consultas(f"/proyectos/nuevo/?grupo={self.henares.pk}&tipologia={self.generico.pk}", 6, None)

    # Ficha y kanban: más subproyectos y tareas.
    def test_ficha_y_kanban(self):
        huerto = self.proyecto()

        def mas():
            sub = self.proyecto(f"Sub {Proyecto.objects.count()}", padre=huerto)
            crear_tarea(self.nutria, {"titulo": "T", "responsable": self.garza}, proyecto=sub)
            crear_tarea(self.nutria, {"titulo": "U", "responsable": self.nutria}, proyecto=huerto)

        mas()
        self.comprobar_consultas(f"/proyectos/{huerto.pk}/", 7, mas)
        self.comprobar_consultas(f"/proyectos/{huerto.pk}/kanban/", 6, mas)

    # Mis tareas, su kanban y la ficha de una tarea.
    def test_tareas(self):
        huerto = self.proyecto()

        def mas():
            crear_tarea(self.nutria, {"titulo": "T", "responsable": self.nutria}, proyecto=huerto)

        mas()
        self.comprobar_consultas("/proyectos/tareas/", 2, mas)
        self.comprobar_consultas("/proyectos/tareas/kanban/", 2, mas)
        self.comprobar_consultas(f"/proyectos/tareas/{Tarea.objects.first().pk}/", 5, None)
