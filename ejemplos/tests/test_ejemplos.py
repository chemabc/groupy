"""
Pruebas del módulo «ejemplos»: borrar los datos de ejemplo funciona aunque, al probar la aplicación, se
haya creado contenido dentro de las organizaciones de ejemplo (eventos, series, proyectos, tareas,
recordatorios, peticiones de talentos…), y después se pueden volver a crear.

«ejemplos» está en la capa base y no puede importar módulos de encima (ni siquiera en las pruebas): los
modelos se piden con apps.get_model y los servicios se nombran como texto (import_string).
"""

from datetime import timedelta

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from django.utils.module_loading import import_string

from ejemplos.servicios import borrar_todos, crear_todos


class PruebasDeBorrarConContenido(TestCase):
    """Lo que se crea al probar dentro de los ejemplos no impide borrarlos."""

    databases = {"default", "boveda"}

    # Crea los ejemplos y, encima, lo que haría una persona al seguir la guía de comprobaciones.
    def preparar_contenido(self):
        crear_recordatorio = import_string("calendario.servicios.crear_recordatorio")
        crear_serie = import_string("eventos.series.crear_serie")
        convocar = import_string("eventos.servicios.convocar")
        crear_proyecto = import_string("proyectos.servicios.crear_proyecto")
        crear_tarea = import_string("proyectos.servicios.crear_tarea")
        pedir = import_string("talentos.servicios.pedir")
        Grupo = apps.get_model("grupos", "Grupo")
        Usuario = get_user_model()
        Tipologia = apps.get_model("tipologias", "Tipologia")
        Talento = apps.get_model("talentos", "Talento")
        lince, nutria = Usuario.objects.get(alias="Lince"), Usuario.objects.get(alias="Nutria")
        henares = Grupo.objects.get(nombre="GRU Henares")
        accion = Tipologia.objects.get(familia=Tipologia.EVENTO, nombre="Acción", organizacion__isnull=True)
        generico = Tipologia.objects.get(familia=Tipologia.PROYECTO, nombre="Genérico", organizacion__isnull=True)
        manana = timezone.now() + timedelta(days=1)
        # Talentos: la petición «2 × Furgoneta» que atascaba el borrado.
        pedir(lince, henares, "Mudanza del local", "", [(Talento.objects.get(nombre="Furgoneta"), 2)])
        # Eventos: uno suelto y una serie (con una tipología común de ejemplo).
        convocar(lince, henares, accion, {"titulo": "Pegada de carteles", "inicio": manana, "direccion": "Plaza"}, "grupo:0")
        crear_serie(lince, henares, accion, {"titulo": "Taller", "inicio": manana, "direccion": "Local", "frecuencia": "semanal"}, "grupo:0")
        # Proyectos y tareas: de grupo, personal y una suelta del grupo con responsable de ejemplo.
        huerto = crear_proyecto(nutria, generico, {"titulo": "Mi huerto de prueba"}, grupo=henares, visibilidad="grupo:0")
        crear_tarea(nutria, {"titulo": "Regar", "responsable": lince}, proyecto=huerto)
        crear_proyecto(nutria, generico, {"titulo": "Lo mío"}, personal=True)
        crear_tarea(lince, {"titulo": "Barrer", "responsable": nutria}, grupo=henares)
        # Calendario: un recordatorio del grupo y otro solo para Nutria.
        crear_recordatorio(nutria, henares, {"titulo": "Pancartas", "inicio": manana}, "grupo:0")
        crear_recordatorio(nutria, henares, {"titulo": "Solo mío", "inicio": manana}, "privado")
        # Grupos y tipologías: un subgrupo nuevo con un evento, y un subtipo propio de ORG Tajo usado en otro.
        nuevo = import_string("grupos.servicios.crear_grupo")(henares.organizacion, "GRU Prueba", padre=henares)
        import_string("grupos.servicios.admitir")(lince, nuevo)
        # En la aplicación, crear un grupo invalida la caché de permisos al confirmar la transacción
        # (permisos/senales.py); dentro de una prueba no se confirma nada, así que se vacía a mano.
        cache.clear()
        propia = Tipologia.objects.create(familia=Tipologia.EVENTO, padre=accion, organizacion=henares.organizacion, nombre="Mi acción")
        convocar(lince, nuevo, propia, {"titulo": "En el subgrupo", "inicio": manana, "direccion": "Calle"}, "grupo:0")
        # Solicitudes y lugares: Garza pide entrar en GRU Manzanares y Nutria elige un lugar de la lista.
        garza = Usuario.objects.get(alias="Garza")
        import_string("solicitudes.servicios.pedir")(garza, "grupos.entrar", Grupo.objects.get(nombre="GRU Manzanares"), "Quiero entrar")
        LugarDePersona = apps.get_model("lugares", "LugarDePersona")
        LugarDePersona.objects.update_or_create(usuario=nutria, defaults={"lugar": apps.get_model("lugares", "Lugar").objects.first()})

    # Borrar no falla, no deja nada de las organizaciones ni de las personas de ejemplo, y se puede volver
    # a crear todo.
    def test_borrar_con_contenido(self):
        crear_todos()
        self.preparar_contenido()
        borrar_todos()
        Organizacion = apps.get_model("grupos", "Organizacion")
        self.assertFalse(Organizacion.objects.exists())
        # Solo queda el superadmin (borrar no lo toca).
        self.assertEqual(list(get_user_model().objects.values_list("alias", flat=True)), ["superadmin"])
        for modelo in ["eventos.Evento", "eventos.Serie", "proyectos.Proyecto", "proyectos.Tarea", "calendario.Recordatorio", "talentos.PeticionDeTalentos"]:
            with self.subTest(modelo=modelo):
                self.assertFalse(apps.get_model(modelo).objects.exists())
        crear_todos()
        self.assertTrue(Organizacion.objects.filter(nombre="ORG Tajo").exists())
