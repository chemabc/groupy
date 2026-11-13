"""
Pruebas de «limpieza»: archivar lo terminado pasado el plazo (y no antes), avisar a quienes lo ven, el
aviso quince días antes de borrar, borrar y apuntarlo en el registro, «Conservar», sacar del archivo lo
reabierto, borrar un proyecto con todo su árbol al podar a mano, borrar las notificaciones viejas sin
archivar, los plazos del superadmin y lo que cuestan las pantallas.

Como «limpieza» no importa otros módulos funcionales, los elementos se crean con apps.get_model:
recordatorios del calendario, proyectos y notificaciones.

Estructura: ORG Tajo (GRU Tajo ⊃ GRU Henares) con Nutria (la sesión) y Lince en GRU Henares; Erizo en
ORG Ebro; y el superadmin.
"""

from datetime import timedelta

from django.apps import apps
from django.urls import reverse
from django.utils import timezone

from audiencias.servicios import audiencia_de_grupos, crear_privada
from base.pruebas import PruebaDePantalla, crear_usuario_de_prueba
from eventos_sw.servicios import procesar_bandeja
from grupos.servicios import admitir, crear_grupo, crear_organizacion
from limpieza import servicios
from limpieza.models import Archivado, Borrado, Plazo
from tipologias.servicios import crear_tipologia

Recordatorio = apps.get_model("calendario", "Recordatorio")
Proyecto = apps.get_model("proyectos", "Proyecto")
Tarea = apps.get_model("proyectos", "Tarea")
Notificacion = apps.get_model("comunicaciones", "Notificacion")

# El momento de referencia de las pruebas.
AHORA = timezone.now()


# Un momento tantos días antes de AHORA.
def hace(dias):
    return AHORA - timedelta(days=dias)


class PruebaDeLimpieza(PruebaDePantalla):
    """Base con la estructura del principio del fichero."""

    # Crea la estructura y una audiencia de GRU Henares.
    @classmethod
    def setUpTestData(cls):
        cls.tajo, cls.general = crear_organizacion("ORG Tajo", "GRU Tajo")
        cls.henares = crear_grupo(cls.tajo, "GRU Henares", padre=cls.general)
        _ebro, cls.gru_ebro = crear_organizacion("ORG Ebro", "GRU Ebro")
        cls.nutria = crear_usuario_de_prueba("Nutria")
        cls.lince = crear_usuario_de_prueba("Lince")
        cls.erizo = crear_usuario_de_prueba("Erizo")
        cls.superadmin = crear_usuario_de_prueba("Jefa", es_superadmin=True)
        admitir(cls.nutria, cls.henares)
        admitir(cls.lince, cls.henares)
        admitir(cls.erizo, cls.gru_ebro)
        cls.de_henares = audiencia_de_grupos([cls.henares], cls.tajo)
        cls.usuario = cls.nutria

    # Crea un recordatorio de GRU Henares que fue hace tantos días.
    def recordatorio(self, titulo, dias, audiencia=None):
        return Recordatorio.objects.create(
            autor=self.nutria, grupo=self.henares, titulo=titulo, inicio=hace(dias), audiencia=audiencia or self.de_henares
        )

    # Crea un proyecto finalizado hace tantos días (con su raíz puesta), opcionalmente debajo de otro.
    def proyecto(self, titulo, dias=60, padre=None):
        proyecto = Proyecto.objects.create(
            titulo=titulo, tipologia=self.tipologia, grupo=self.henares, creador=self.nutria, audiencia=self.de_henares,
            estado="finalizado", padre=padre,
        )
        proyecto.raiz = padre.raiz if padre else proyecto
        proyecto.save()
        Proyecto.objects.filter(pk=proyecto.pk).update(terminado=hace(dias))
        proyecto.refresh_from_db()
        return proyecto

    # La tipología de los proyectos de prueba (se crea la primera vez).
    @property
    def tipologia(self):
        if not hasattr(self, "_tipologia"):
            self._tipologia = crear_tipologia("proyecto", "Genérico")
        return self._tipologia

    # Pasa la limpieza en un momento dado (AHORA, si no se dice).
    def limpiar(self, momento=AHORA):
        return servicios.limpiar(momento)

    # Inicia sesión como otra persona.
    def como(self, usuario):
        self.client.force_login(usuario)


class PruebasDeArchivarYBorrar(PruebaDeLimpieza):
    """El recorrido completo: archivar, avisar, conservar y borrar."""

    # Lo que pasó hace más de 30 días se archiva; lo de hace 10 días, no. El archivado guarda título,
    # enlace y audiencia.
    def test_archiva_lo_terminado_pasado_el_plazo(self):
        viejo, reciente = self.recordatorio("Viejo", 40), self.recordatorio("Reciente", 10)
        self.assertEqual(self.limpiar()["archivados"], 1)
        viejo.refresh_from_db()
        reciente.refresh_from_db()
        self.assertIsNotNone(viejo.archivado)
        self.assertIsNone(reciente.archivado)
        fila = Archivado.objects.get()
        self.assertEqual((fila.tipo, fila.objeto_id, fila.titulo), ("calendario.recordatorio", viejo.pk, "Viejo"))
        self.assertEqual(fila.enlace, reverse("calendario:recordatorio", args=[viejo.pk]))
        self.assertEqual(fila.audiencia_id, self.de_henares.pk)
        # La segunda vuelta no lo archiva otra vez.
        self.assertEqual(self.limpiar()["archivados"], 0)

    # Al archivar se avisa a quienes lo ven (Nutria y Lince), no a quien no (Erizo).
    def test_avisa_al_archivar(self):
        self.recordatorio("Viejo", 40)
        self.recordatorio("Otro viejo", 50)
        self.limpiar()
        procesar_bandeja()
        avisos = Notificacion.objects.filter(tipo="limpieza.archivados")
        self.assertEqual({aviso.usuario_id for aviso in avisos}, {self.nutria.pk, self.lince.pk})
        self.assertIn("Se han archivado 2 elementos", avisos.first().texto)
        self.assertEqual(avisos.first().enlace, reverse("limpieza:archivados"))

    # Quince días antes de cumplir el plazo se avisa; se borra cuando se cumplen el plazo y los quince
    # días desde el aviso, y queda en el registro de borrados.
    def test_avisa_y_borra(self):
        viejo = self.recordatorio("Viejo", 40)
        self.limpiar()
        Archivado.objects.update(archivado_el=hace(355))
        resumen = self.limpiar()
        self.assertEqual((resumen["avisados"], resumen["borrados"]), (1, 0))
        procesar_bandeja()
        aviso = Notificacion.objects.get(tipo="limpieza.se_borraran", usuario=self.nutria)
        self.assertIn("Dentro de 15 días se borrará un elemento archivado", aviso.texto)
        # A los 14 días del aviso, aún no.
        self.assertEqual(self.limpiar(AHORA + timedelta(days=14))["borrados"], 0)
        self.assertEqual(self.limpiar(AHORA + timedelta(days=16))["borrados"], 1)
        self.assertFalse(Recordatorio.objects.filter(pk=viejo.pk).exists())
        self.assertFalse(Archivado.objects.exists())
        borrado = Borrado.objects.get()
        self.assertEqual((borrado.titulo, borrado.motivo, borrado.audiencia_id), ("Viejo", Borrado.PLAZO, self.de_henares.pk))

    # Si el plazo se cumplió sin aviso (por ejemplo, porque el superadmin lo acortó), primero se avisa y
    # se borra quince días después, nunca en la misma vuelta.
    def test_nunca_borra_sin_aviso_previo(self):
        self.recordatorio("Viejo", 40)
        self.limpiar()
        Archivado.objects.update(archivado_el=hace(1000))
        self.assertEqual(self.limpiar()["borrados"], 0)
        self.assertEqual(Archivado.objects.get().avisado_el, AHORA)

    # «Conservar» (quien lo ve): ya no se borra. Quien no lo ve no lo encuentra. El superadmin puede
    # dejar de conservarlo y vuelve a contar, con aviso nuevo.
    def test_conservar(self):
        viejo = self.recordatorio("Viejo", 40)
        self.limpiar()
        fila = Archivado.objects.get()
        url = reverse("limpieza:archivado", args=[fila.pk])
        self.como(self.erizo)
        self.assertEqual(self.client.post(url, {"accion": "conservar"}).status_code, 404)
        self.como(self.lince)
        self.assertRedirects(self.client.post(url, {"accion": "conservar"}), reverse("limpieza:archivados"))
        fila.refresh_from_db()
        self.assertEqual(fila.conservado_por, self.lince)
        Archivado.objects.update(archivado_el=hace(1000), avisado_el=hace(100))
        self.assertEqual(self.limpiar()["borrados"], 0)
        self.assertTrue(Recordatorio.objects.filter(pk=viejo.pk).exists())
        # Solo el superadmin deja de conservar.
        self.assertEqual(self.client.post(url, {"accion": "dejar"}).status_code, 403)
        self.como(self.superadmin)
        self.client.post(url, {"accion": "dejar"})
        fila.refresh_from_db()
        self.assertIsNone(fila.conservado_el)
        self.assertIsNone(fila.avisado_el)

    # Un proyecto reabierto sale del archivo: su módulo borra la fecha y la limpieza quita la fila.
    def test_lo_reabierto_sale_del_archivo(self):
        huerto = self.proyecto("Huerto")
        self.limpiar()
        huerto.refresh_from_db()
        self.assertIsNotNone(huerto.archivado)
        self.assertNotContains(self.client.get(reverse("proyectos:proyectos")), "Huerto")
        self.assertContains(self.client.get(reverse("proyectos:proyecto", args=[huerto.pk])), "Archivado el")
        huerto.estado = "empezado"
        huerto.save()
        self.assertIsNone(huerto.archivado)
        self.assertIsNone(huerto.terminado)
        self.limpiar()
        self.assertFalse(Archivado.objects.exists())
        self.assertContains(self.client.get(reverse("proyectos:proyectos")), "Huerto")

    # Solo se archivan los proyectos principales; al podar uno a mano (el superadmin), se borra con sus
    # subproyectos y sus tareas, y queda en el registro como poda.
    def test_podar_un_proyecto_con_su_arbol(self):
        huerto = self.proyecto("Huerto")
        riego = self.proyecto("Riego", padre=huerto)
        Tarea.objects.create(titulo="Comprar mangueras", proyecto=riego, grupo=self.henares, responsable=self.nutria)
        self.limpiar()
        fila = Archivado.objects.get()
        self.assertEqual(fila.objeto_id, huerto.pk)
        url = reverse("limpieza:archivado", args=[fila.pk])
        self.assertEqual(self.client.post(url, {"accion": "podar"}).status_code, 403)
        self.como(self.superadmin)
        self.client.post(url, {"accion": "podar"})
        self.assertFalse(Proyecto.objects.exists())
        self.assertFalse(Tarea.objects.exists())
        borrado = Borrado.objects.get()
        self.assertEqual((borrado.motivo, borrado.quien), (Borrado.A_MANO, self.superadmin))

    # Lo personal solo lo ve su dueña en el archivo (ni el superadmin).
    def test_lo_personal_en_el_archivo(self):
        self.recordatorio("Mío", 40, audiencia=crear_privada([self.nutria], personal=True))
        self.limpiar()
        self.assertContains(self.client.get(reverse("limpieza:archivados")), "Mío")
        for persona in (self.lince, self.superadmin):
            self.como(persona)
            self.assertNotContains(self.client.get(reverse("limpieza:archivados")), "Mío")


class PruebasDeNotificacionesYPlazos(PruebaDeLimpieza):
    """Las notificaciones viejas y los plazos del superadmin."""

    # Las vistas hace más de 90 días y las sin ver de hace más de 365 se borran, sin pasar por el archivo.
    def test_borra_las_notificaciones_viejas(self):
        def notificacion(texto, creada, vista_el=None):
            fila = Notificacion.objects.create(usuario=self.nutria, tipo="prueba", origen="sistema", texto=texto)
            Notificacion.objects.filter(pk=fila.pk).update(creada=creada, vista_el=vista_el)

        notificacion("vista hace mucho", hace(200), hace(100))
        notificacion("vista hace poco", hace(200), hace(10))
        notificacion("sin ver, muy vieja", hace(400))
        notificacion("sin ver, de este año", hace(100))
        self.assertEqual(self.limpiar()["sin_archivo"], 2)
        self.assertEqual(set(Notificacion.objects.values_list("texto", flat=True)), {"vista hace poco", "sin ver, de este año"})
        self.assertFalse(Archivado.objects.exists())

    # Los plazos del superadmin mandan: con 50 días, lo de hace 40 no se archiva; desactivado, nada.
    def test_plazos_del_superadmin(self):
        self.recordatorio("Viejo", 40)
        servicios.guardar_plazo("calendario.recordatorio", True, 50, 365)
        self.assertEqual(self.limpiar()["archivados"], 0)
        servicios.guardar_plazo("calendario.recordatorio", False, 10, 365)
        self.assertEqual(self.limpiar()["archivados"], 0)
        servicios.plazo_de_partida("calendario.recordatorio")
        self.assertEqual(self.limpiar()["archivados"], 1)

    # La pantalla de plazos: solo el superadmin; guarda y vuelve a los de partida.
    def test_pantalla_de_plazos(self):
        url = reverse("limpieza:plazos")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.como(self.superadmin)
        self.client.post(url, {"tipo": "proyectos.tarea", "activo": "on", "archivar_a": "7", "borrar_a": "60"})
        plazo = Plazo.objects.get(tipo="proyectos.tarea")
        self.assertEqual((plazo.activo, plazo.archivar_a, plazo.borrar_a), (True, 7, 60))
        self.assertContains(self.client.post(url, {"tipo": "proyectos.tarea", "borrar_a": "cero"}), "Revisa los días")
        self.client.post(url, {"tipo": "proyectos.tarea", "partida": "1"})
        self.assertFalse(Plazo.objects.exists())

    # Qué día se borra: el plazo, pero nunca antes de quince días desde el aviso (o desde hoy, si aún no
    # se ha avisado); conservado o con el tipo parado, nunca.
    def test_se_borra_el(self):
        plazo = servicios.plazos()["calendario.recordatorio"]
        fila = Archivado(archivado_el=hace(10))
        self.assertEqual(servicios.se_borra_el(fila, plazo, AHORA), hace(10) + timedelta(days=365))
        fila.archivado_el = hace(1000)
        self.assertEqual(servicios.se_borra_el(fila, plazo, AHORA), AHORA + timedelta(days=15))
        fila.avisado_el = hace(5)
        self.assertEqual(servicios.se_borra_el(fila, plazo, AHORA), hace(5) + timedelta(days=15))
        fila.conservado_el = AHORA
        self.assertIsNone(servicios.se_borra_el(fila, plazo, AHORA))


class PruebasDePantallas(PruebaDeLimpieza):
    """Lo que cuestan las pantallas, que no crece con las filas."""

    # Archiva unos cuantos recordatorios más (para medir con más filas).
    def archivar_mas(self):
        for numero in range(5):
            self.recordatorio(f"Más {numero}", 40)
        self.limpiar()
        Archivado.objects.filter(titulo="Más 0").update(conservado_por=self.lince, conservado_el=AHORA)

    # Borra a mano unos cuantos archivados más (para medir el registro con más filas).
    def borrar_mas(self):
        self.archivar_mas()
        servicios._borrar(list(Archivado.objects.all()), Borrado.A_MANO, quien=self.superadmin)

    def test_archivados(self):
        self.recordatorio("Viejo", 40)
        self.limpiar()
        respuesta = self.comprobar_consultas(reverse("limpieza:archivados"), 3, self.archivar_mas)
        self.assertContains(respuesta, "conservado por Lince")
        self.assertContains(respuesta, "Conservar")
        self.assertNotContains(respuesta, "Borrar ya")

    def test_archivados_filtrados(self):
        self.recordatorio("Viejo", 40)
        self.limpiar()
        self.comprobar_consultas(reverse("limpieza:archivados") + "?tipo=calendario.recordatorio&pronto=1", 3, self.archivar_mas)

    def test_borrados(self):
        self.recordatorio("Viejo", 40)
        self.limpiar()
        servicios._borrar(list(Archivado.objects.all()), Borrado.PLAZO)
        respuesta = self.comprobar_consultas(reverse("limpieza:borrados"), 2, self.borrar_mas)
        self.assertContains(respuesta, "a mano, por Jefa")

    def test_plazos(self):
        self.usuario = self.superadmin
        self.como(self.superadmin)
        self.comprobar_consultas(reverse("limpieza:plazos"), 2, None)
