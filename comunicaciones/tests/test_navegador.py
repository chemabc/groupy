"""
Pruebas de «Comunicaciones → Notificaciones» en un navegador de verdad (ver base/pruebas_navegador.py):
el número del menú baja al marcar como vista sin recargar la página, la papelera borra una y «Limpiar las
vistas» pide confirmación y borra solo las vistas. También la sala de un grupo y las conversaciones entre
personas (elegir con el selector y bloquear).
"""

from django.core.cache import cache

from base.pruebas_navegador import PruebaEnElNavegador
from comunicaciones.models import Notificacion


class PruebasDeNotificacionesEnElNavegador(PruebaEnElNavegador):
    """Tres notificaciones del usuario de la prueba: dos sin ver y una vista."""

    # Marcar una como vista baja el número del menú (de 2 a 1); la papelera borra otra; «Limpiar las
    # vistas», aceptando la confirmación, deja solo la que sigue sin ver.
    def test_bandeja(self):
        Notificacion.objects.bulk_create(
            [
                Notificacion(usuario=self.usuario, tipo="t", origen="grupos", texto="Primera"),
                Notificacion(usuario=self.usuario, tipo="t", origen="grupos", texto="Segunda"),
                Notificacion(usuario=self.usuario, tipo="t", origen="sistema", texto="Ya vista", vista_el="2026-11-13T10:00:00Z"),
            ]
        )
        # Se han creado a mano (no con repartir): se olvida el número sin ver guardado al entrar.
        cache.clear()
        primera = Notificacion.objects.get(texto="Primera")
        self.abrir("/comunicaciones/")
        contador = self.pagina.locator("#contador-comunicacionesnotificaciones")
        self.assertEqual(contador.inner_text(), "(2)")
        self.pagina.locator(f'li[data-notificacion="{primera.pk}"] button[value="vista"]').click()
        self.pagina.wait_for_function("document.querySelector('#contador-comunicacionesnotificaciones').textContent === '(1)'")
        # La papelera de «Segunda».
        segunda = Notificacion.objects.get(texto="Segunda")
        self.pagina.locator(f'li[data-notificacion="{segunda.pk}"] button[value="borrar"]').click()
        self.pagina.wait_for_selector("text=Segunda", state="detached")
        # «Limpiar las vistas» pregunta antes; se acepta.
        self.pagina.once("dialog", lambda dialogo: dialogo.accept())
        self.pagina.get_by_role("button", name="Limpiar las vistas").click()
        self.pagina.wait_for_selector("text=No tienes notificaciones")
        self.assertFalse(Notificacion.objects.exists())
        self.assertEqual(contador.inner_text(), "(0)")
        self.assertEqual(self.errores, [])


class PruebasDeConversacionesEnElNavegador(PruebaEnElNavegador):
    """Una conversación abierta en el navegador recibe sola los mensajes nuevos."""

    # Con la conversación abierta, un mensaje que escribe la administración aparece sin recargar (htmx
    # vuelve a pedir la lista cada 10 segundos), y el formulario de respuesta no se pierde.
    def test_mensajes_nuevos_aparecen_solos(self):
        from comunicaciones.administraciones import Buzon
        from comunicaciones.servicios import abrir_conversacion, escribir
        from base.pruebas import crear_usuario_de_prueba
        from grupos.models import Pertenencia
        from grupos.servicios import admitir, crear_organizacion

        _tajo, grupo = crear_organizacion("ORG Tajo", "GRU Tajo")
        lince = crear_usuario_de_prueba("Lince")
        admitir(lince, grupo, rol=Pertenencia.ADMIN_GRUPO)
        admitir(self.usuario, grupo)
        conversacion = abrir_conversacion(self.usuario, Buzon(grupo=grupo), "Llaves", "¿Quién las tiene?")
        self.abrir(f"/comunicaciones/conversaciones/{conversacion.pk}/")
        self.pagina.locator('textarea[name="texto"]').fill("Escribiendo…")
        escribir(conversacion, lince, "Las tengo yo.", como_admin=True)
        self.pagina.wait_for_selector("text=Las tengo yo.", timeout=15000)
        self.assertTrue(self.pagina.locator("text=Admin de GRU Tajo (Lince)").is_visible())
        self.assertEqual(self.pagina.locator('textarea[name="texto"]').input_value(), "Escribiendo…")
        self.assertEqual(self.errores, [])


class PruebasDeConversarEnElNavegador(PruebaEnElNavegador):
    """La sala de un grupo y las conversaciones entre personas, en el navegador ([A-56])."""

    # Prepara GRU Tajo con el usuario de la prueba y Lince. Devuelve (grupo, lince).
    def preparar(self):
        from base.pruebas import crear_usuario_de_prueba
        from grupos.servicios import admitir, crear_organizacion

        _tajo, grupo = crear_organizacion("ORG Tajo", "GRU Tajo")
        lince = crear_usuario_de_prueba("Lince")
        admitir(lince, grupo)
        admitir(self.usuario, grupo)
        return grupo, lince

    # Con la sala abierta, lo que escribe Lince aparece solo (htmx vuelve a pedir la lista cada 10
    # segundos) sin perder lo que se está escribiendo.
    def test_sala(self):
        from comunicaciones.con_grupos import escribir

        grupo, lince = self.preparar()
        self.abrir(f"/comunicaciones/grupos/{grupo.pk}/")
        self.pagina.get_by_text("Aún no ha escrito nadie").wait_for()
        self.pagina.locator('textarea[name="texto"]').fill("Escribiendo…")
        escribir(grupo, lince, "¿Quién abre el sábado?")
        self.pagina.wait_for_selector("text=¿Quién abre el sábado?", timeout=15000)
        self.assertEqual(self.pagina.locator('textarea[name="texto"]').input_value(), "Escribiendo…")
        self.assertEqual(self.errores, [])

    # Escribir a una persona eligiéndola en el selector (sale Lince, de GRU Tajo); después, bloquearla
    # aceptando la confirmación: el formulario desaparece y sale «Desbloquear a Lince».
    def test_escribir_y_bloquear(self):
        from comunicaciones.models import Bloqueo

        _grupo, lince = self.preparar()
        self.abrir("/comunicaciones/personas/escribir/")
        self.pagina.locator("#id_persona").click()
        ventana = self.pagina.get_by_role("dialog", name="Elegir una persona")
        ventana.get_by_text("Personas de tus grupos").wait_for()
        ventana.get_by_role("radio", name="Lince").click()
        ventana.wait_for(state="hidden")
        self.pagina.locator('textarea[name="texto"]').fill("¡Hola, Lince!")
        self.pagina.get_by_role("button", name="Enviar").click()
        self.pagina.get_by_role("heading", name="Con Lince").wait_for()
        self.assertTrue(self.pagina.get_by_text("¡Hola, Lince!").is_visible())
        self.pagina.once("dialog", lambda dialogo: dialogo.accept())
        self.pagina.get_by_role("button", name="Bloquear").click()
        self.pagina.get_by_role("button", name="Desbloquear a Lince").wait_for()
        self.assertEqual(self.pagina.locator('textarea[name="texto"]').count(), 0)
        self.assertTrue(Bloqueo.objects.filter(quien=self.usuario, a_quien=lince).exists())
        self.assertEqual(self.errores, [])
