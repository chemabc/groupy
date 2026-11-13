"""
Pruebas de la bóveda: huellas, alta, validación por el superadmin, cambio de correo, dominios
permitidos y que sus tablas vivan solo en su base, sin relación posible con la plataforma.
"""

from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TestCase, override_settings

from boveda.models import DominioPermitido, PaseEmitido, Persona
from boveda.servicios import cambiar_datos, huella, poner_dominios, registrar_persona, validar_por_superadmin
from config.enrutador import EnrutadorDeLaBoveda
from usuarios.models import Usuario


class PruebasDeLaBoveda(TestCase):
    """Comprueba las operaciones de la bóveda, en su propia base de pruebas."""

    databases = {"default", "boveda"}

    # La huella no depende de mayúsculas ni espacios, no contiene el correo y cambia con la clave.
    def test_huella(self):
        self.assertEqual(huella(" Ana@Educa.org "), huella("ana@educa.org"))
        self.assertEqual(len(huella("ana@educa.org")), 64)
        self.assertNotIn("ana", huella("ana@educa.org"))
        with override_settings(BOVEDA_CLAVE_HMAC="otra"):
            otra = huella("ana@educa.org")
        self.assertNotEqual(otra, huella("ana@educa.org"))

    # Alta: queda pendiente, con su correo y su huella; en las listas se ve «Persona xxxxxxxx», no el nombre.
    def test_alta(self):
        persona = registrar_persona("Ana Pérez", "Ana@Educa.org", 7)
        self.assertEqual((persona.estado, persona.correo_oficial), (Persona.PENDIENTE, "ana@educa.org"))
        self.assertEqual(str(persona), f"Persona {persona.id.hex[:8]}")
        self.assertNotIn("Ana", str(persona))

    # Un correo ya registrado (aunque cambien las mayúsculas) no se puede registrar otra vez.
    def test_correo_repetido(self):
        registrar_persona("Ana Pérez", "ana@educa.org", 7)
        with self.assertRaisesMessage(ValidationError, "Ese correo ya está registrado"):
            registrar_persona("Otra", "ANA@educa.org", 7)

    # Si la organización tiene dominios, el correo debe ser de uno de ellos.
    def test_dominios(self):
        self.assertEqual(poner_dominios(7, ["@Educa.org", "educa.org", " otra.es "]), ["educa.org", "otra.es"])
        with self.assertRaisesMessage(ValidationError, "solo admite correos de: educa.org, otra.es"):
            registrar_persona("Ana", "ana@gmail.com", 7)
        registrar_persona("Ana", "ana@otra.es", 7)
        registrar_persona("Luis", "luis@gmail.com", 8)  # La organización 8 no tiene dominios: vale cualquiera.
        with self.assertRaisesMessage(ValidationError, "no parece un dominio"):
            poner_dominios(7, ["sin punto"])
        self.assertEqual(poner_dominios(7, []), [])
        self.assertFalse(DominioPermitido.objects.filter(organizacion_id=7).exists())

    # Validar: el correo se borra (queda la huella) y el pase queda marcado como emitido.
    def test_validar(self):
        persona = validar_por_superadmin(registrar_persona("Ana", "ana@educa.org", 7))
        persona.refresh_from_db()
        self.assertEqual((persona.estado, persona.metodo, persona.correo_oficial), (Persona.VALIDADA, "superadmin", ""))
        self.assertEqual(persona.huella_del_correo, huella("ana@educa.org"))
        self.assertTrue(PaseEmitido.objects.get(persona=persona).provisional)
        with self.assertRaisesMessage(ValidationError, "ya está validada"):
            validar_por_superadmin(persona)
        # Aunque su correo se borró, su huella sigue impidiendo registrarlo otra vez.
        with self.assertRaises(ValidationError):
            registrar_persona("Otra", "ana@educa.org", 7)

    # Cambiar el correo de una persona validada la deja pendiente otra vez, con su pase aún emitido.
    def test_cambiar_correo(self):
        persona = validar_por_superadmin(registrar_persona("Ana", "ana@educa.org", 7))
        cambiar_datos(persona, "Ana Pérez", 7, "ana.perez@educa.org")
        persona.refresh_from_db()
        self.assertEqual((persona.estado, persona.nombre, persona.correo_oficial), (Persona.PENDIENTE, "Ana Pérez", "ana.perez@educa.org"))
        self.assertTrue(persona.pases.exists())
        # Sin correo nuevo, solo cambian el nombre y la organización.
        cambiar_datos(persona, "Ana P.", 8)
        persona.refresh_from_db()
        self.assertEqual((persona.nombre, persona.organizacion_id, persona.correo_oficial), ("Ana P.", 8, "ana.perez@educa.org"))

    # Las tablas de la bóveda están solo en su base; las de la plataforma, solo en la suya; y no se
    # permite ninguna relación entre las dos.
    def test_enrutador(self):
        enrutador = EnrutadorDeLaBoveda()
        self.assertEqual(enrutador.db_for_write(Persona), "boveda")
        self.assertEqual(enrutador.db_for_write(Usuario), "default")
        self.assertFalse(enrutador.allow_relation(Persona(), Usuario()))
        self.assertTrue(enrutador.allow_relation(Persona(), PaseEmitido()))
        self.assertFalse(enrutador.allow_migrate("default", "boveda"))
        self.assertFalse(enrutador.allow_migrate("boveda", "usuarios"))
        tablas_de_la_plataforma = connections["default"].introspection.table_names()
        tablas_de_la_boveda = connections["boveda"].introspection.table_names()
        self.assertNotIn("boveda_persona", tablas_de_la_plataforma)
        self.assertIn("boveda_persona", tablas_de_la_boveda)
        self.assertNotIn("usuarios_usuario", tablas_de_la_boveda)
