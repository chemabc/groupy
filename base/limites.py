"""
Límites en cascada: varios niveles (la plataforma, cada organización, cada grupo y sus antecesores, cada
elemento concreto) pueden poner un máximo, y vale el más estricto de cada uno. Lo usan los debates
(palabras, intervenciones…) y los documentos (cuántas personas escriben y comentan a la vez). Cada módulo
guarda sus filas en su propia tabla; aquí solo se juntan.
"""


# Junta los límites de varios niveles: de cada campo, el más pequeño de los que alguien ha puesto. Si la
# plataforma no tiene fila, cuenta también el valor de partida. Devuelve un diccionario campo → valor (None:
# sin límite).
#   - filas: las filas de límites que tocan (de la plataforma, la organización, los grupos, el elemento).
#   - por_defecto: campo → valor de partida (None: sin límite de partida).
#   - plataforma: la fila de la plataforma, o None si el superadmin no ha puesto ninguna.
def mas_estricto(filas, por_defecto, plataforma):
    valores = {}
    for campo, defecto in por_defecto.items():
        candidatos = [getattr(fila, campo) for fila in filas if getattr(fila, campo) is not None]
        if plataforma is None and defecto is not None:
            candidatos.append(defecto)
        valores[campo] = min(candidatos) if candidatos else None
    return valores
