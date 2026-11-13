"""
Pruebas de «proyectos»: crear proyectos y subproyectos a cualquier profundidad (y verlos en árbol), quién
los ve (también los personales, ni el superadmin) y quién los gestiona (quien crea o coordina un
antecesor, la administración del grupo), las tareas (responsable que ve el proyecto, aviso, kanban con
las de los subproyectos, mover), las dependencias entre tareas (bloqueo y desbloqueo solos), los recursos
(con su petición de talentos), las etiquetas, las tareas modelo de su tipo, su paso por el calendario y lo que cuestan las pantallas.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares ⊃ GRU Sorbe) con Lince admin de GRU Henares, Nutria en GRU
Henares (la sesión), Garza en GRU Sorbe y Zorro en GRU Tajo; Erizo en ORG Ebro.
"""

import json
from datetime import date, timedelta

from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils import timezone

from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from etiquetas.servicios import etiquetas_de
from eventos_sw.servicios import procesar_bandeja
from grupos.models import Pertenencia
from grupos.servicios import admitir, crear_grupo, crear_organizacion
from proyectos.models import Proyecto, Tarea
from proyectos.servicios import anadir_recurso, apuntar, crear_proyecto, crear_tarea, editar_tarea
from tipologias.servicios import crear_tarea_modelo, crear_tipologia

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

    # Un proyecto de Nutria en GRU Henares (o un subproyecto, con «padre»), con sus etiquetas.
    def proyecto(self, titulo="Huerto", padre=None, visibilidad="grupo:0", etiquetas=(), **otros):
        datos_del_servicio = {"titulo": titulo, **otros}
        return crear_proyecto(self.nutria, self.generico, datos_del_servicio, grupo=self.henares, visibilidad=visibilidad, padre=padre, etiquetas=etiquetas)


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

    # Para la limpieza: al pasar a «Hecha» (arrastrando) o a «Finalizado» se apunta cuándo terminó; al
    # reabrir, se borra esa fecha y la de archivo. Lo archivado sale de «Mis tareas» y de «Personales».
    def test_fecha_de_fin_y_archivo(self):
        suelta = crear_tarea(self.nutria, {"titulo": "Limpiar el local", "responsable": self.nutria}, grupo=self.henares, visibilidad="grupo:0")
        mover = lambda estado: self.client.post("/proyectos/tareas/mover/", json.dumps({"tarea": suelta.pk, "estado": estado, "orden": [suelta.pk]}), content_type="application/json")  # noqa: E731
        mover("hecha")
        suelta.refresh_from_db()
        self.assertIsNotNone(suelta.terminado)
        Tarea.objects.filter(pk=suelta.pk).update(archivado=suelta.terminado)
        self.assertNotContains(self.client.get("/proyectos/tareas/"), "Limpiar el local")
        mover("en_curso")
        suelta.refresh_from_db()
        self.assertEqual((suelta.terminado, suelta.archivado), (None, None))
        self.assertContains(self.client.get("/proyectos/tareas/"), "Limpiar el local")
        mio = crear_proyecto(self.nutria, self.generico, {"titulo": "Mi huerto"}, personal=True)
        self.client.post(f"/proyectos/{mio.pk}/", {"accion": "estado", "estado": Proyecto.FINALIZADO})
        mio.refresh_from_db()
        self.assertIsNotNone(mio.terminado)
        Proyecto.objects.filter(pk=mio.pk).update(archivado=mio.terminado)
        self.assertNotContains(self.client.get("/proyectos/personales/"), "Mi huerto")

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


class PruebasDeDependencias(PruebaDeProyectos):
    """Tareas que esperan a otras: se bloquean y desbloquean solas, con sus reglas."""

    # Mueve una tarea en el kanban como lo haría la isla; devuelve la respuesta.
    def mover(self, tarea, estado):
        datos = json.dumps({"tarea": tarea.pk, "estado": estado, "orden": [tarea.pk]})
        return self.client.post("/proyectos/tareas/mover/", datos, content_type="application/json")

    # Estado actual de una tarea (de la base de datos).
    def estado(self, tarea):
        return Tarea.objects.get(pk=tarea.pk).estado

    # «Bomba» (en el subproyecto Riego) espera a «Zanja» y «Tubos»: queda bloqueada, no se puede sacar a
    # mano y, cuando las dos están hechas, vuelve sola a «Pendiente» (el kanban recibe «otras») y se
    # avisa a Garza. Si una vuelve atrás, se bloquea otra vez.
    def test_bloquea_y_desbloquea(self):
        huerto = self.proyecto()
        riego = self.proyecto("Riego", padre=huerto)
        zanja = crear_tarea(self.nutria, {"titulo": "Zanja", "responsable": self.nutria}, proyecto=huerto)
        tubos = crear_tarea(self.nutria, {"titulo": "Tubos", "responsable": self.nutria}, proyecto=huerto)
        bomba = crear_tarea(self.nutria, {"titulo": "Bomba", "responsable": self.garza}, proyecto=riego, espera_a=[zanja, tubos])
        self.assertEqual(self.estado(bomba), Tarea.BLOQUEADA)
        respuesta = self.mover(bomba, Tarea.EN_CURSO)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("espera a «Tubos», «Zanja»", respuesta.json()["error"])
        self.assertEqual(self.mover(zanja, Tarea.HECHA).json(), {"ok": True})
        self.assertEqual(self.estado(bomba), Tarea.BLOQUEADA)
        self.assertEqual(self.mover(tubos, Tarea.HECHA).json(), {"ok": True, "otras": 1})
        self.assertEqual(self.estado(bomba), Tarea.PENDIENTE)
        procesar_bandeja()
        aviso = Notificacion.objects.get(tipo="proyectos.tarea_desbloqueada")
        self.assertEqual(aviso.usuario, self.garza)
        self.assertIn("Ya puedes ponerte con «Bomba»", aviso.texto)
        self.mover(tubos, Tarea.EN_CURSO)
        self.assertEqual(self.estado(bomba), Tarea.BLOQUEADA)

    # Lo bloqueado a mano no se desbloquea solo; al borrar la tarea esperada, la que esperaba se libera.
    def test_bloqueo_a_mano_y_borrar(self):
        huerto = self.proyecto()
        zanja = crear_tarea(self.nutria, {"titulo": "Zanja", "responsable": self.nutria}, proyecto=huerto)
        manual = crear_tarea(self.nutria, {"titulo": "Manual", "responsable": self.nutria}, proyecto=huerto)
        self.mover(manual, Tarea.BLOQUEADA)
        manual.refresh_from_db()
        editar_tarea(self.nutria, manual, {}, espera_a=[zanja])
        self.mover(zanja, Tarea.HECHA)
        self.assertEqual(self.estado(manual), Tarea.BLOQUEADA)
        espera = crear_tarea(self.nutria, {"titulo": "Espera", "responsable": self.nutria}, proyecto=huerto, espera_a=[manual])
        self.assertEqual(self.estado(espera), Tarea.BLOQUEADA)
        self.client.post(f"/proyectos/tareas/{manual.pk}/", {"accion": "borrar"})
        self.assertEqual(self.estado(espera), Tarea.PENDIENTE)

    # Reglas: del mismo árbol, no a sí misma, sin círculos y solo en proyectos.
    def test_reglas(self):
        huerto, otro = self.proyecto(), self.proyecto("Otro")
        a = crear_tarea(self.nutria, {"titulo": "A", "responsable": self.nutria}, proyecto=huerto)
        b = crear_tarea(self.nutria, {"titulo": "B", "responsable": self.nutria}, proyecto=huerto, espera_a=[a])
        c = crear_tarea(self.nutria, {"titulo": "C", "responsable": self.nutria}, proyecto=huerto, espera_a=[b])
        fuera = crear_tarea(self.nutria, {"titulo": "Fuera", "responsable": self.nutria}, proyecto=otro)
        for esperas, error in (([fuera], "no es de este proyecto"), ([a], "sí misma"), ([c], "círculo")):
            with self.subTest(error=error), self.assertRaisesMessage(ValidationError, error):
                editar_tarea(self.nutria, a, {}, espera_a=esperas)
        suelta = crear_tarea(self.nutria, {"titulo": "Suelta", "responsable": self.nutria}, grupo=self.henares, visibilidad="grupo:0")
        with self.assertRaisesMessage(ValidationError, "Solo las tareas de un proyecto"):
            editar_tarea(self.nutria, suelta, {}, espera_a=[a])

    # Desde la ficha: el formulario ofrece las tareas del árbol y guarda a cuáles espera; la ficha lo
    # muestra en las dos tareas.
    def test_desde_la_ficha(self):
        huerto = self.proyecto()
        a = crear_tarea(self.nutria, {"titulo": "Cavar", "responsable": self.nutria}, proyecto=huerto)
        b = crear_tarea(self.nutria, {"titulo": "Sembrar", "responsable": self.nutria}, proyecto=huerto)
        datos_del_formulario = {"accion": "guardar", "titulo": "Sembrar", "descripcion": "", "limite": "", "estado": "pendiente", "responsable": "Nutria", "colaboradores": "", "espera_a": [a.pk]}
        self.assertRedirects(self.client.post(f"/proyectos/tareas/{b.pk}/", datos_del_formulario), f"/proyectos/tareas/{b.pk}/")
        self.assertEqual(self.estado(b), Tarea.BLOQUEADA)
        self.assertContains(self.client.get(f"/proyectos/tareas/{b.pk}/"), "bloqueada hasta que estén hechas")
        self.assertContains(self.client.get(f"/proyectos/tareas/{a.pk}/"), "La esperan")


class PruebasDeRecursos(PruebaDeProyectos):
    """Los recursos de un proyecto y su petición de talentos."""

    # Nutria (gestiona) apunta un recurso y lo marca como conseguido; Garza (lo ve, no lo gestiona) no puede tocarlo. Nutria no
    # puede pedir talentos al grupo; Lince (admin del grupo) sí: se crea la petición, anclada al proyecto.
    def test_recursos(self):
        huerto = self.proyecto()
        url = f"/proyectos/{huerto.pk}/"
        self.client.post(url, {"accion": "recurso", "recurso-nombre": "Mangueras", "recurso-cantidad": "3", "recurso-origen": "Ferretería"})
        recurso = huerto.recursos.get()
        self.assertEqual((recurso.nombre, recurso.cantidad), ("Mangueras", "3"))
        self.assertNotContains(self.client.get(url), "Pedir al grupo")
        self.assertContains(self.client.post(url, {"accion": "pedir_recurso", "recurso": recurso.pk}), "poder pedir talentos")
        self.client.post(url, {"accion": "conseguido", "recurso": recurso.pk})
        recurso.refresh_from_db()
        self.assertTrue(recurso.conseguido)
        self.client.post(url, {"accion": "pendiente", "recurso": recurso.pk})
        self.como(self.garza)
        self.assertContains(self.client.post(url, {"accion": "quitar_recurso", "recurso": recurso.pk}), "Solo quien gestiona")
        self.como(self.lince)
        self.assertContains(self.client.get(url), "Pedir al grupo")
        respuesta = self.client.post(url, {"accion": "pedir_recurso", "recurso": recurso.pk})
        recurso.refresh_from_db()
        peticion = recurso.peticion
        self.assertRedirects(respuesta, f"/talentos/peticiones/{peticion.pk}/", fetch_redirect_response=False)
        self.assertEqual((peticion.asunto, peticion.ancla_tipo, peticion.ancla_id, peticion.grupo), ("Huerto: Mangueras", "proyectos.proyecto", huerto.pk, self.henares))
        self.assertEqual(peticion.necesidades.get().cantidad, 3)
        self.assertContains(self.client.get(url), "petición de talentos")
        self.client.post(url, {"accion": "quitar_recurso", "recurso": recurso.pk})
        self.assertFalse(huerto.recursos.exists())


class PruebasDeEtiquetasYTareasModelo(PruebaDeProyectos):
    """Etiquetas de los proyectos de grupo y tareas modelo de su tipo al crearlos."""

    # Al crear un proyecto de «Preparación de acción» con la casilla marcada salen sus tareas modelo (la
    # segunda, esperando a la primera) y sus etiquetas; sin la casilla, no hay tareas.
    def test_crear_con_tareas_modelo_y_etiquetas(self):
        accion = crear_tipologia("proyecto", "Preparación de acción")
        crear_tarea_modelo(accion, "Pedir permiso", dias=7)
        crear_tarea_modelo(accion, "Hacer el cartel", espera_a_la_anterior=True)
        url = f"/proyectos/nuevo/?grupo={self.henares.pk}&tipologia={accion.pk}"
        self.assertContains(self.client.get(url), "Crear las 2 tareas modelo de su tipo")
        respuesta = self.client.post(url, datos(titulo="Cacerolada", etiquetas=["vivienda", "Barrio"], con_tareas_modelo="on"))
        cacerolada = Proyecto.objects.get(titulo="Cacerolada")
        self.assertRedirects(respuesta, f"/proyectos/{cacerolada.pk}/")
        permiso, cartel = cacerolada.tareas.order_by("pk")
        self.assertEqual((permiso.titulo, permiso.responsable, permiso.estado), ("Pedir permiso", self.nutria, Tarea.PENDIENTE))
        self.assertEqual(permiso.limite, timezone.localdate() + timedelta(days=7))
        self.assertEqual((cartel.estado, list(cartel.espera_a.all())), (Tarea.BLOQUEADA, [permiso]))
        self.assertEqual(etiquetas_de(("proyectos.proyecto", cacerolada.pk)), ["Barrio", "Vivienda"])
        self.client.post(url, datos(titulo="Sin tareas"))
        self.assertFalse(Proyecto.objects.get(titulo="Sin tareas").tareas.exists())

    # Las etiquetas se cambian al editar, salen en la ficha y en la lista, y filtran la lista. Los
    # personales no llevan etiquetas.
    def test_etiquetas(self):
        huerto = self.proyecto(etiquetas=["Huerto"])
        self.proyecto("Biblioteca")
        self.client.post(f"/proyectos/{huerto.pk}/editar/", datos(etiquetas=["Huerto", "Verano"]))
        self.assertEqual(etiquetas_de(("proyectos.proyecto", huerto.pk)), ["Huerto", "Verano"])
        self.assertContains(self.client.get(f"/proyectos/{huerto.pk}/"), "#Verano")
        filtrada = self.client.get("/proyectos/?etiqueta=Verano")
        self.assertContains(filtrada, "Huerto")
        self.assertNotContains(filtrada, "Biblioteca")
        self.assertContains(self.client.get("/proyectos/"), "Biblioteca")
        respuesta = self.client.get(f"/proyectos/nuevo/?personal=1&tipologia={self.generico.pk}")
        self.assertNotContains(respuesta, 'name="etiquetas"')


class PruebasDeConsultas(PruebaDeProyectos):
    """Cada pantalla cuesta lo mismo con pocas filas que con muchas."""

    # Listas: más proyectos y subproyectos.
    def test_listas(self):
        huerto = self.proyecto()
        self.comprobar_consultas("/proyectos/", 3, lambda: self.proyecto("Otro", padre=huerto, etiquetas=["Barrio"]))
        self.comprobar_consultas("/proyectos/?etiqueta=Barrio", 3, lambda: self.proyecto("Más", etiquetas=["Barrio", "Huerto"]))
        self.comprobar_consultas("/proyectos/personales/", 3, lambda: crear_proyecto(self.nutria, self.generico, {"titulo": "P"}, personal=True))
        self.comprobar_consultas(f"/proyectos/nuevo/?grupo={self.henares.pk}&tipologia={self.generico.pk}", 7, None)

    # Ficha y kanban: más subproyectos y tareas.
    def test_ficha_y_kanban(self):
        huerto = self.proyecto()

        def mas():
            sub = self.proyecto(f"Sub {Proyecto.objects.count()}", padre=huerto)
            crear_tarea(self.nutria, {"titulo": "T", "responsable": self.garza}, proyecto=sub)
            crear_tarea(self.nutria, {"titulo": "U", "responsable": self.nutria}, proyecto=huerto)
            anadir_recurso(self.nutria, huerto, {"nombre": "Mangueras", "cantidad": "3", "origen": "Ferretería"})

        mas()
        self.comprobar_consultas(f"/proyectos/{huerto.pk}/", 9, mas)
        self.comprobar_consultas(f"/proyectos/{huerto.pk}/kanban/", 6, mas)

    # Mis tareas, su kanban y la ficha de una tarea.
    def test_tareas(self):
        huerto = self.proyecto()

        def mas():
            primera = Tarea.objects.order_by("pk").first()
            crear_tarea(self.nutria, {"titulo": "T", "responsable": self.nutria}, proyecto=huerto, espera_a=[primera] if primera else ())

        mas()
        self.comprobar_consultas("/proyectos/tareas/", 2, mas)
        self.comprobar_consultas("/proyectos/tareas/kanban/", 2, mas)
        self.comprobar_consultas(f"/proyectos/tareas/{Tarea.objects.order_by('pk').first().pk}/", 8, mas)
        self.comprobar_consultas(f"/proyectos/tareas/{Tarea.objects.order_by('pk').last().pk}/", 8, mas)
