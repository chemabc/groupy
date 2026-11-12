"""
Vigilancia de la regla de dependencias entre capas (ver docs/diseno.md, apartado 3.2).

La regla: un módulo solo puede importar módulos de capas inferiores o de su misma capa, y un módulo
funcional nunca puede importar otro funcional (se relacionan con anclas y eventos_sw).

Se comprueba leyendo el código fuente de cada módulo, sin ejecutarlo. Lo usa la prueba
base/tests/test_dependencias.py, que falla en cuanto alguien rompe la regla.
"""

import ast
from pathlib import Path

from .contrato import Capa


# Dice si un módulo de la capa «origen» puede importar uno de la capa «destino».
def importacion_permitida(origen, destino):
    if destino < origen:
        return True
    return destino == origen and origen != Capa.FUNCIONAL


# Devuelve los nombres de los módulos de primer nivel que importa un fichero de Python. Por ejemplo, de
# «from eventos.models import Evento» saca «eventos». Las importaciones relativas («from . import x»)
# son del propio módulo y no se cuentan.
def modulos_importados(fichero):
    arbol = ast.parse(Path(fichero).read_text(encoding="utf-8"), filename=str(fichero))
    nombres = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            nombres.add(nodo.module.split(".")[0])
    return nombres


# Recorre todos los ficheros de todos los módulos del registro y devuelve un texto por cada importación
# que rompe la regla. Lista vacía: todo en orden.
#   - modulos: diccionario de etiqueta a ModuloConfig (normalmente, registro.modulos).
def importaciones_prohibidas(modulos):
    # Capa de cada módulo, por el nombre con el que se importa (su «name» de primer nivel).
    capas = {config.name.split(".")[0]: config.capa for config in modulos.values()}
    infracciones = []
    for config in modulos.values():
        nombre_propio = config.name.split(".")[0]
        for fichero in sorted(Path(config.path).rglob("*.py")):
            for importado in modulos_importados(fichero):
                if importado == nombre_propio or importado not in capas:
                    continue
                if not importacion_permitida(config.capa, capas[importado]):
                    infracciones.append(
                        f"{fichero}: «{nombre_propio}» ({config.capa.name}) importa «{importado}» "
                        f"({capas[importado].name})."
                    )
    return infracciones
