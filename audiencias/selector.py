"""
Selector de visibilidad: las opciones de «¿Quién lo ve?» que se ofrecen al publicar algo en un grupo,
según lo que permite su organización (ver docs/diseno.md, apartado 3.4), y la audiencia que corresponde a
la opción elegida. Lo usan los módulos que publican cosas (eventos, proyectos…) en sus formularios.

Las opciones se identifican con una clave de texto: «privado», «grupo:0» (su grupo), «grupo:1» (hasta el
padre), …, «organizacion» y «publico».
"""

from grupos.models import Contencion

from .servicios import audiencia_para, configuracion_de


# Opciones de visibilidad para publicar desde un grupo: lista de (clave, explicación). La explicación dice
# en una frase a quién llega («Hasta el grupo padre: las personas de GRU Jarama y de todos sus
# subgrupos»). Una consulta.
#   - grupo: el grupo desde el que se publica (con su organización cargada).
def opciones(grupo):
    configuracion = configuracion_de(grupo.organizacion)
    encima = dict(
        Contencion.objects.filter(descendiente=grupo, distancia__lte=configuracion.altura_maxima).values_list("distancia", "antecesor__nombre")
    )
    resultado = [("privado", "Privado: solo las personas implicadas (quien lo crea y quien tenga un cometido)")]
    for altura in sorted(encima):
        nombre = encima[altura]
        if altura == 0:
            resultado.append(("grupo:0", f"Mi grupo: las personas de {nombre} y de sus subgrupos"))
        else:
            que = {1: "Hasta el grupo padre", 2: "Hasta el grupo abuelo"}.get(altura, f"Hasta {altura} niveles por encima")
            resultado.append((f"grupo:{altura}", f"{que}: las personas de {nombre} y de todos sus subgrupos"))
    if configuracion.permite_toda_la_organizacion:
        resultado.append(("organizacion", f"Toda la organización: todas las personas de {grupo.organizacion}"))
    if configuracion.permite_publico:
        resultado.append(("publico", "Público: cualquiera, también sin cuenta (sin alias)"))
    return resultado


# Audiencia que corresponde a una opción elegida (ver opciones()). Comprueba lo que permite la
# organización (audiencia_para lanza ValidationError si no). Devuelve la audiencia.
#   - clave: la opción elegida.
#   - grupo: el grupo desde el que se publica.
#   - personas: con «privado», las personas implicadas.
#   - ancla: (tipo, id) de lo que se publica.
def audiencia_de(clave, grupo, personas=(), ancla=None):
    if clave.startswith("grupo:"):
        return audiencia_para("grupo", grupo, altura=int(clave.split(":")[1]), ancla=ancla)
    if clave in ("organizacion", "publico"):
        return audiencia_para(clave, grupo, ancla=ancla)
    return audiencia_para("privado", grupo, personas=personas, ancla=ancla)


# Clave de la opción que corresponde a una audiencia ya guardada (para editar), o «privado».
#   - audiencia: la audiencia.
#   - grupo: el grupo desde el que se publicó.
def clave_de(audiencia, grupo):
    if audiencia is None or audiencia.tipo == "privada":
        return "privado"
    if audiencia.tipo == "organizacion":
        return "organizacion"
    if audiencia.tipo == "publica":
        return "publico"
    grupos = list(audiencia.grupos.values_list("grupo_id", flat=True))
    if len(grupos) == 1:
        distancia = Contencion.objects.filter(antecesor_id=grupos[0], descendiente=grupo).values_list("distancia", flat=True).first()
        if distancia is not None:
            return f"grupo:{distancia}"
    return "privado"
