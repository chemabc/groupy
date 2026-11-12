"""
Pruebas de la regla de dependencias entre capas.

La primera prueba revisa el código real de todos los módulos: si alguien hace que un módulo funcional
importe otro, falla y dice en qué fichero. Las demás comprueban la propia regla.
"""

import tempfile
from pathlib import Path
from types import SimpleNamespace

from django.test import SimpleTestCase

from base.contrato import Capa
from base.dependencias import importacion_permitida, importaciones_prohibidas
from base.registro import registro


class PruebasDeDependencias(SimpleTestCase):
    """Comprueba la regla de capas: hacia abajo sí, hacia arriba no, entre funcionales tampoco."""

    # Ningún módulo real de la aplicación rompe la regla.
    def test_ningun_modulo_rompe_la_regla(self):
        self.assertEqual(importaciones_prohibidas(registro.modulos), [])

    # Importar de una capa inferior está permitido.
    def test_hacia_abajo_si(self):
        self.assertTrue(importacion_permitida(Capa.FUNCIONAL, Capa.BASE))
        self.assertTrue(importacion_permitida(Capa.ORGANIZACION, Capa.IDENTIDAD))

    # Importar de una capa superior está prohibido.
    def test_hacia_arriba_no(self):
        self.assertFalse(importacion_permitida(Capa.BASE, Capa.FUNCIONAL))

    # Dentro de la misma capa se permite, salvo entre módulos funcionales.
    def test_misma_capa(self):
        self.assertTrue(importacion_permitida(Capa.ORGANIZACION, Capa.ORGANIZACION))
        self.assertFalse(importacion_permitida(Capa.FUNCIONAL, Capa.FUNCIONAL))

    # Con dos módulos funcionales de mentira en una carpeta temporal, detecta que uno importa al otro.
    def test_detecta_una_importacion_prohibida(self):
        with tempfile.TemporaryDirectory() as carpeta:
            # Crea «alfa/vistas.py», que importa del módulo «beta».
            (Path(carpeta) / "alfa").mkdir()
            (Path(carpeta) / "alfa" / "vistas.py").write_text("from beta.models import Cosa\n")
            (Path(carpeta) / "beta").mkdir()
            modulos = {
                "alfa": SimpleNamespace(name="alfa", path=Path(carpeta) / "alfa", capa=Capa.FUNCIONAL),
                "beta": SimpleNamespace(name="beta", path=Path(carpeta) / "beta", capa=Capa.FUNCIONAL),
            }
            infracciones = importaciones_prohibidas(modulos)
        self.assertEqual(len(infracciones), 1)
        self.assertIn("«alfa» (FUNCIONAL) importa «beta»", infracciones[0])
