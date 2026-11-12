"""
Pruebas de eventos_sw: emitir, escuchas síncronas y asíncronas, bandeja de salida y reintentos.

Usan un módulo de mentira, «alfa», con tres avisos declarados:
- alfa.creado: lo escucha «anotar» de forma síncrona.
- alfa.cerrado: lo escuchan dos «anotar» de forma asíncrona.
- alfa.roto: lo escucha «fallar», de forma síncrona y asíncrona.
"""

from io import StringIO

from django.core.management import call_command
from django.db import transaction
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from base.contrato import Emision, Escucha, Modo
from base.pruebas import contratos_de_prueba, modulo_falso
from eventos_sw.models import AvisoPendiente
from eventos_sw.servicios import (
    MAXIMO_DE_INTENTOS,
    EventoNoDeclarado,
    FueraDeTransaccion,
    emitir,
    procesar_bandeja,
)

from . import receptores

# Rutas de los receptores de mentira, como las escribiría un contrato.
ANOTAR = "eventos_sw.tests.receptores.anotar"
FALLAR = "eventos_sw.tests.receptores.fallar"

# El módulo de mentira que emite y escucha los avisos de estas pruebas.
ALFA = modulo_falso(
    "alfa",
    emite=(
        Emision("alfa.creado", "Se ha creado un alfa"),
        Emision("alfa.cerrado", "Se ha cerrado un alfa"),
        Emision("alfa.roto", "Aviso cuyo receptor falla"),
    ),
    escucha=(
        Escucha("alfa.creado", ANOTAR, Modo.SINCRONO),
        Escucha("alfa.cerrado", ANOTAR, Modo.ASINCRONO),
        Escucha("alfa.cerrado", ANOTAR, Modo.ASINCRONO),
        Escucha("alfa.roto", FALLAR, Modo.ASINCRONO),
    ),
)


class PruebasDeEmitir(TestCase):
    """Comprueba emitir() y procesar_bandeja() con la base de datos de pruebas."""

    # Antes de cada prueba: vacía la lista de recibidos y añade el módulo «alfa» al registro.
    def setUp(self):
        receptores.recibidos.clear()
        contexto = contratos_de_prueba(ALFA)
        contexto.__enter__()
        # Al acabar la prueba (bien o mal), el registro vuelve a ser el real.
        self.addCleanup(contexto.__exit__, None, None, None)

    # Una escucha síncrona se ejecuta en el acto, con los datos del aviso, y no deja nada en la bandeja.
    def test_sincrono_en_el_acto(self):
        emitir("alfa.creado", alfa_id=7)
        self.assertEqual(receptores.recibidos, [{"alfa_id": 7}])
        self.assertFalse(AvisoPendiente.objects.exists())

    # Las escuchas asíncronas se apuntan en la bandeja con una sola consulta y no se ejecutan hasta
    # que se procesa la bandeja. Después, sus filas desaparecen.
    def test_asincrono_por_la_bandeja(self):
        with self.assertNumQueries(1):
            emitir("alfa.cerrado", alfa_id=7)
        self.assertEqual(receptores.recibidos, [])
        self.assertEqual(AvisoPendiente.objects.count(), 2)
        self.assertEqual(procesar_bandeja(), 2)
        self.assertEqual(receptores.recibidos, [{"alfa_id": 7}, {"alfa_id": 7}])
        self.assertFalse(AvisoPendiente.objects.exists())

    # Un aviso que nadie declara da error.
    def test_aviso_no_declarado(self):
        with self.assertRaises(EventoNoDeclarado):
            emitir("alfa.inventado")

    # Los datos que no se pueden guardar como JSON (un objeto) dan error, aunque no haya asíncronas.
    def test_datos_que_no_son_simples(self):
        with self.assertRaises(TypeError):
            emitir("alfa.creado", alfa=object())

    # Si falla una escucha síncrona, se deshace todo lo hecho en la transacción, también el cambio.
    def test_fallo_sincrono_lo_deshace_todo(self):
        falla_en_el_acto = modulo_falso(
            "beta",
            emite=(Emision("beta.roto", "…"),),
            escucha=(Escucha("beta.roto", FALLAR, Modo.SINCRONO),),
        )
        with contratos_de_prueba(ALFA, falla_en_el_acto):
            with self.assertRaises(ValueError):
                with transaction.atomic():
                    AvisoPendiente.objects.create(evento="cambio", receptor="de prueba")
                    emitir("beta.roto")
        self.assertFalse(AvisoPendiente.objects.exists())

    # Un aviso asíncrono que falla se queda en la bandeja con el error y se retrasa su siguiente intento.
    def test_fallo_asincrono_se_reintenta(self):
        emitir("alfa.roto", alfa_id=7)
        procesar_bandeja()
        aviso = AvisoPendiente.objects.get()
        self.assertEqual(aviso.intentos, 1)
        self.assertIn("Fallo a propósito", aviso.ultimo_error)
        self.assertGreater(aviso.proximo_intento, timezone.now())
        self.assertFalse(aviso.fallido)
        # Mientras no llega su momento, la bandeja no lo vuelve a intentar.
        self.assertEqual(procesar_bandeja(), 0)

    # Al llegar al máximo de intentos, el aviso queda marcado como fallido y ya no se reintenta.
    def test_demasiados_fallos(self):
        emitir("alfa.roto", alfa_id=7)
        AvisoPendiente.objects.update(intentos=MAXIMO_DE_INTENTOS - 1)
        procesar_bandeja()
        self.assertTrue(AvisoPendiente.objects.get().fallido)
        AvisoPendiente.objects.update(proximo_intento=timezone.now())
        self.assertEqual(procesar_bandeja(), 0)

    # Un aviso que falla no impide que se entreguen los demás de la misma tanda.
    def test_un_fallo_no_para_a_los_demas(self):
        emitir("alfa.roto")
        emitir("alfa.cerrado", alfa_id=8)
        self.assertEqual(procesar_bandeja(), 3)
        self.assertEqual(len(receptores.recibidos), 2)
        self.assertEqual(AvisoPendiente.objects.count(), 1)


class PruebasFueraDeTransaccion(SimpleTestCase):
    """Comprueba que emitir() exige estar dentro de una transacción."""

    # Fuera de transaction.atomic(), emitir() da un error que explica qué hacer.
    def test_exige_transaccion(self):
        with self.assertRaises(FueraDeTransaccion):
            emitir("alfa.creado")


class PruebasDeLaOrden(TestCase):
    """Comprueba la orden «procesar_bandeja»."""

    # Con --una-vez, procesa lo pendiente, lo cuenta y termina.
    def test_una_vez(self):
        salida = StringIO()
        with contratos_de_prueba(ALFA):
            emitir("alfa.cerrado", alfa_id=7)
            call_command("procesar_bandeja", "--una-vez", stdout=salida)
        self.assertIn("2 avisos procesados", salida.getvalue())
        self.assertFalse(AvisoPendiente.objects.exists())
