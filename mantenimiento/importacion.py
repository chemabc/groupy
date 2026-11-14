"""
Importación masiva de grupos y de usuarios desde una hoja de cálculo (Desarrollo y mantenimiento →
Pruebas). Funciona en dos pasos:

1. revisar_*(): lee las filas, comprueba cada una y prepara un «plan» con lo que se va a crear. No
   cambia nada. La pantalla muestra la vista previa: qué es nuevo, qué ya existe, avisos y errores.
2. aplicar_*(plan): crea todo lo del plan en una sola transacción (todo o nada). El plan se guarda en
   la sesión entre los dos pasos; es JSON y no lleva contraseñas en claro, sino ya cifradas.

Las columnas, los nombres que se aceptan para cada una y las filas de ejemplo de las plantillas están
aquí también, para que la plantilla y la lectura no se separen.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from base.hojas import Hoja, filas_por_columna
from base.tablas import normalizar
from grupos.models import AdminDeOrganizacion, Grupo, Organizacion, Pertenencia
from grupos.servicios import admitir, crear_grupo, nombrar_admin_de_organizacion
from permisos.models import Rol
from usuarios.models import normalizar_alias, validar_forma_del_alias

# Máximo de filas por fichero: más, mejor en varias veces (cifrar cada contraseña tarda un poco).
MAXIMO_DE_FILAS = 2000

# Columnas de la plantilla de grupos: {clave: [nombre en la plantilla, otros nombres aceptados]}.
COLUMNAS_DE_GRUPOS = {
    "organizacion": ["Organización", "Organizacion"],
    "grupo": ["Grupo"],
    "padre": ["Grupo padre", "Padre"],
    "localizacion": ["Localización", "Localización del grupo", "Ámbito geográfico", "Ámbito"],
}
OBLIGATORIAS_DE_GRUPOS = ["organizacion", "grupo", "padre"]

# Columnas de la plantilla de usuarios.
COLUMNAS_DE_USUARIOS = {
    "alias": ["Alias"],
    "contrasena": ["Contraseña", "Contrasena", "Clave"],
    "organizacion": ["Organización", "Organizacion"],
    "grupo": ["Grupo"],
    "rol": ["Rol"],
    "base": ["Asamblea base", "Base"],
    "admin_org": ["Admin de la organización", "Admin de la organizacion", "Admin organización"],
    "correo": ["Correo alternativo", "Correo"],
}
OBLIGATORIAS_DE_USUARIOS = ["alias", "contrasena", "organizacion", "grupo"]

# Textos que valen como «sí» y como «no» en las columnas de sí o no.
SI = {"si", "s", "x", "1", "true", "verdadero", "yes"}
NO = {"", "no", "n", "0", "false", "falso"}


@dataclass
class FilaRevisada:
    """Una fila del fichero con lo que pasará con ella."""

    # Número de la fila en la hoja (como lo ve la persona en LibreOffice).
    numero: int
    # Lo leído en cada columna.
    datos: dict
    # «nuevo», «existe» o «error».
    estado: str = "nuevo"
    # Explicaciones: errores (si estado es «error») o avisos.
    mensajes: list = field(default_factory=list)
    # Texto extra para la vista previa (por ejemplo, el camino del grupo).
    detalle: str = ""

    # Apunta un error en la fila.
    def error(self, texto):
        self.estado = "error"
        self.mensajes.append(texto)

    # Apunta un aviso (no impide importar).
    def aviso(self, texto):
        self.mensajes.append(texto)


@dataclass
class Revision:
    """Resultado de revisar un fichero: las filas, errores generales y el plan para aplicarlo."""

    filas: list = field(default_factory=list)
    errores: list = field(default_factory=list)
    plan: dict = field(default_factory=dict)

    # Si hay algún error (en el fichero o en alguna fila): entonces no se puede importar.
    @property
    def hay_errores(self):
        return bool(self.errores) or any(fila.estado == "error" for fila in self.filas)

    # Cuántas filas hay de cada estado, para el resumen.
    @property
    def resumen(self):
        cuentas = defaultdict(int)
        for fila in self.filas:
            cuentas[fila.estado] += 1
        return dict(cuentas)


# Lee las filas por columna y comprueba la cabecera y el tamaño. Devuelve (filas, Revision con los
# errores generales, si los hay).
def _preparar(filas, columnas, obligatorias):
    revision = Revision()
    por_columna, faltan = filas_por_columna(filas, columnas, obligatorias)
    if faltan:
        nombres = ", ".join(f"«{columnas[clave][0]}»" for clave in faltan)
        revision.errores.append(f"Faltan columnas en la primera fila: {nombres}. Usa la plantilla.")
    if not por_columna and not faltan:
        revision.errores.append("El fichero no tiene ninguna fila de datos debajo de la cabecera.")
    if len(por_columna) > MAXIMO_DE_FILAS:
        revision.errores.append(f"Como mucho {MAXIMO_DE_FILAS} filas por fichero; divídelo en varios.")
    return por_columna, revision


# ── Grupos ───────────────────────────────────────────────────────────────────────────────────────────


# Hojas de la plantilla de grupos: los datos (cabecera y ejemplos) y las instrucciones.
def plantilla_de_grupos():
    datos = [
        [nombres[0] for nombres in COLUMNAS_DE_GRUPOS.values()],
        ["ORG Tajo", "GRU Tajo", "", "Cuenca del Tajo"],
        ["ORG Tajo", "GRU Jarama", "GRU Tajo", "Madrid"],
        ["ORG Tajo", "GRU Henares", "GRU Jarama", "Alcalá de Henares"],
        ["ORG Tajo", "GRU Sorbe", "GRU Henares", ""],
    ]
    instrucciones = [
        ["Importar grupos: instrucciones"],
        ["Una fila por grupo. Las filas de ejemplo de la hoja «Datos» se pueden borrar o cambiar."],
        ["Organización: si no existe, se crea."],
        ["Grupo: su nombre. No puede repetirse dentro de su organización. Si ya existe, no se toca."],
        ["Grupo padre: el grupo que lo contiene, de la misma organización. Vacío si es un grupo principal."],
        ["   El padre puede estar más abajo en el fichero o existir ya en la plataforma."],
        ["   Puede haber tantos niveles como hagan falta (general → zona → centro → …)."],
        ["Localización: zona que abarca el grupo (opcional). Se guarda como su ámbito geográfico."],
        ["Al subir el fichero se ve una vista previa con lo que se creará y los errores. No se crea nada hasta confirmar."],
        ["Se puede subir este .ods o un .csv con las mismas columnas."],
    ]
    return [
        Hoja("Datos", datos, anchos=[5, 6, 6, 6]),
        Hoja("Instrucciones", instrucciones, con_cabecera=True, anchos=[24]),
    ]


# Revisa las filas de un fichero de grupos y prepara el plan. Hace 2 consultas, tenga las filas que
# tenga.
#   - filas: lo que devuelve base.hojas.leer_filas().
def revisar_grupos(filas):
    datos, revision = _preparar(filas, COLUMNAS_DE_GRUPOS, OBLIGATORIAS_DE_GRUPOS)
    if revision.errores:
        return revision
    nombres_de_organizaciones = {fila["organizacion"] for fila in datos if fila["organizacion"]}
    existentes = set(Organizacion.objects.filter(nombre__in=nombres_de_organizaciones).values_list("nombre", flat=True))
    # Grupos que ya existen en esas organizaciones: (organización, grupo) → nombre de su padre.
    en_la_base = {
        (organizacion, grupo): padre or ""
        for organizacion, grupo, padre in Grupo.objects.filter(organizacion__nombre__in=nombres_de_organizaciones).values_list(
            "organizacion__nombre", "nombre", "padre__nombre"
        )
    }
    nuevos = {}  # (organización, grupo) → fila revisada, de los grupos que se crearán.
    padres = dict(en_la_base)  # (organización, grupo) → padre, con los de la base y los nuevos.
    for fila in datos:
        revisada = FilaRevisada(numero=fila["fila"], datos=fila)
        revision.filas.append(revisada)
        organizacion, grupo, padre = fila["organizacion"], fila["grupo"], fila["padre"]
        if not organizacion or not grupo:
            revisada.error("Faltan la organización o el grupo.")
            continue
        if len(grupo) > 100 or len(organizacion) > 100:
            revisada.error("El nombre es demasiado largo (100 caracteres como mucho).")
            continue
        clave = (organizacion, grupo)
        if clave in nuevos:
            revisada.error(f"«{grupo}» de «{organizacion}» ya está más arriba, en la fila {nuevos[clave].numero}.")
            continue
        if clave in en_la_base:
            revisada.estado = "existe"
            if padre and padre != en_la_base[clave]:
                anterior = en_la_base[clave] or "ninguno: es un grupo principal"
                revisada.aviso(f"Ya existe con otro grupo padre ({anterior}); no se cambia.")
            continue
        if padre == grupo:
            revisada.error("Un grupo no puede ser su propio padre.")
            continue
        nuevos[clave] = revisada
        padres[clave] = padre
    # Segunda vuelta, cuando ya se conocen todos los grupos del fichero: comprueba los padres, busca
    # círculos y calcula el camino de cada grupo nuevo.
    for (organizacion, grupo), revisada in nuevos.items():
        if revisada.estado == "error":
            continue
        padre = padres[(organizacion, grupo)]
        if padre and (organizacion, padre) not in padres:
            revisada.error(f"El grupo padre «{padre}» no está en el fichero ni existe en «{organizacion}».")
            continue
        camino = _camino(organizacion, grupo, padres)
        if camino is None:
            revisada.error("Los grupos padre de esta fila forman un círculo (uno acaba dentro de sí mismo).")
            continue
        revisada.detalle = " › ".join([organizacion, *camino])
        if organizacion not in existentes:
            revisada.aviso(f"Se creará la organización «{organizacion}».")
    if not revision.hay_errores:
        revision.plan = {
            "organizaciones": sorted({organizacion for organizacion, _grupo in nuevos} - existentes),
            "grupos": [
                {"organizacion": organizacion, "grupo": grupo, "padre": padres[(organizacion, grupo)], "localizacion": revisada.datos["localizacion"]}
                for (organizacion, grupo), revisada in sorted(nuevos.items(), key=lambda par: len(par[1].detalle.split(" › ")))
            ],
        }
    return revision


# Camino de un grupo, del más alto a él, siguiendo los padres. None si hay un círculo.
def _camino(organizacion, grupo, padres):
    camino, actual, vistos = [], grupo, set()
    while actual:
        if actual in vistos:
            return None
        vistos.add(actual)
        camino.append(actual)
        actual = padres.get((organizacion, actual), "")
    return list(reversed(camino))


# Crea lo que dice el plan de grupos, todo o nada. Los grupos van ordenados de arriba abajo (primero
# los padres). Devuelve cuántas organizaciones y grupos se han creado.
#   - plan: el de revisar_grupos().
@transaction.atomic
def aplicar_grupos(plan):
    organizaciones = {}
    for nombre in plan["organizaciones"]:
        organizacion = Organizacion(nombre=nombre)
        organizacion.full_clean()
        organizacion.save()
        organizaciones[nombre] = organizacion
    creados = {}
    for datos in plan["grupos"]:
        organizacion = organizaciones.get(datos["organizacion"]) or Organizacion.objects.get(nombre=datos["organizacion"])
        organizaciones[datos["organizacion"]] = organizacion
        padre = None
        if datos["padre"]:
            padre = creados.get((datos["organizacion"], datos["padre"])) or Grupo.objects.get(
                organizacion=organizacion, nombre=datos["padre"]
            )
        grupo = crear_grupo(organizacion, datos["grupo"], padre=padre, ambito=datos["localizacion"][:100])
        creados[(datos["organizacion"], datos["grupo"])] = grupo
    return {"organizaciones": len(plan["organizaciones"]), "grupos": len(creados)}


# ── Usuarios ─────────────────────────────────────────────────────────────────────────────────────────


# Hojas de la plantilla de usuarios. El rol tiene un desplegable con los roles de grupo que existen, y
# las columnas de sí o no, uno con «sí» y «no».
def plantilla_de_usuarios():
    roles = list(Rol.objects.filter(nivel=Rol.GRUPO).values_list("codigo", flat=True))
    datos = [
        [nombres[0] for nombres in COLUMNAS_DE_USUARIOS.values()],
        ["Lince", "M3n0sL3ctiv4s", "ORG Tajo", "GRU Henares", "admin_grupo", "sí", "sí", ""],
        ["Lince", "", "ORG Ebro", "GRU Segre", "", "no", "no", ""],
        ["Nutria", "Otra-Clave-2026", "ORG Tajo", "GRU Henares", "", "", "", "nutria@ejemplo.org"],
    ]
    instrucciones = [
        ["Importar usuarios: instrucciones"],
        ["Una fila por cada grupo en el que está una persona: si está en dos grupos, dos filas con el mismo alias."],
        ["Alias: seudónimo con el que entra. De 3 a 30 letras, números, espacios, puntos o guiones. Nunca el nombre real."],
        ["   Da igual escribirlo con o sin mayúsculas y tildes: «María» y «maria» son el mismo alias."],
        ["Contraseña: la que tendrá al empezar. Basta en una de sus filas. Cada persona la cambia en «Configuración de mi cuenta → Contraseña»."],
        ["   Si el alias ya existe, su contraseña no se cambia."],
        ["Organización y Grupo: deben existir (impórtalos antes en «Importar grupos»)."],
        [f"Rol: vacío es «usuario» (miembro normal). Otros: {', '.join(roles)}."],
        ["Asamblea base: «sí» en el grupo más local de la persona (solo uno). Si no se marca ninguno, será el de su primera fila."],
        ["Admin de la organización: «sí» para nombrarle admin de esa organización."],
        ["Correo alternativo: opcional, para avisos. Mejor que no sea el oficial."],
        ["Al subir el fichero se ve una vista previa con lo que se creará y los errores. No se crea nada hasta confirmar."],
        ["Se puede subir este .ods o un .csv con las mismas columnas."],
    ]
    return [
        Hoja(
            "Datos",
            datos,
            anchos=[4, 5, 5, 5, 4, 3.5, 5, 6],
            desplegables={4: roles, 5: ["sí", "no"], 6: ["sí", "no"]},
        ),
        Hoja("Instrucciones", instrucciones, con_cabecera=True, anchos=[26]),
    ]


# Convierte un texto de una columna de sí o no en True o False. None si no se entiende.
def _si_o_no(texto):
    texto = normalizar(texto.strip())
    if texto in SI:
        return True
    if texto in NO:
        return False
    return None


# Revisa las filas de un fichero de usuarios y prepara el plan (con las contraseñas ya cifradas). Hace
# 5 consultas, tenga las filas que tenga (más el cifrado de cada contraseña nueva, que es lento a
# propósito).
#   - filas: lo que devuelve base.hojas.leer_filas().
def revisar_usuarios(filas):
    datos, revision = _preparar(filas, COLUMNAS_DE_USUARIOS, OBLIGATORIAS_DE_USUARIOS)
    if revision.errores:
        return revision
    Usuario = get_user_model()
    claves = {normalizar_alias(fila["alias"]) for fila in datos if fila["alias"]}
    existentes = {usuario.alias_normalizado: usuario for usuario in Usuario.objects.filter(alias_normalizado__in=claves)}
    grupos = {
        (organizacion, nombre): (pk, organizacion_id)
        for pk, nombre, organizacion, organizacion_id in Grupo.objects.filter(
            organizacion__nombre__in={fila["organizacion"] for fila in datos}
        ).values_list("pk", "nombre", "organizacion__nombre", "organizacion_id")
    }
    roles = {}
    for codigo, nombre in Rol.objects.filter(nivel=Rol.GRUPO).values_list("codigo", "nombre"):
        roles[normalizar(codigo)] = codigo
        roles[normalizar(nombre)] = codigo
    ya_dentro = {
        (usuario_id, grupo_id): (rol, es_base)
        for usuario_id, grupo_id, rol, es_base in Pertenencia.objects.filter(usuario__in=existentes.values()).values_list(
            "usuario_id", "grupo_id", "rol", "es_base"
        )
    }
    ya_admins = set(AdminDeOrganizacion.objects.filter(usuario__in=existentes.values()).values_list("usuario_id", "organizacion_id"))
    con_base = {usuario_id for (usuario_id, _grupo), (_rol, es_base) in ya_dentro.items() if es_base}

    escrito = {}  # clave del alias → cómo se escribió la primera vez
    contrasenas = {}  # clave del alias → contraseña (de alguna de sus filas)
    vistas = {}  # (clave del alias, id del grupo) → número de fila
    filas_validas = []
    for fila in datos:
        revisada = FilaRevisada(numero=fila["fila"], datos={**fila, "contrasena": "•••" if fila["contrasena"] else ""})
        revision.filas.append(revisada)
        alias = " ".join(fila["alias"].split())
        if not alias:
            revisada.error("Falta el alias.")
            continue
        try:
            validar_forma_del_alias(alias)
        except ValidationError as error:
            revisada.error(" ".join(error.messages))
            continue
        clave = normalizar_alias(alias)
        if escrito.setdefault(clave, alias) != alias:
            revisada.error(f"«{alias}» es el mismo alias que «{escrito[clave]}» escrito de otra forma; escríbelo igual en todas sus filas.")
            continue
        existente = existentes.get(clave)
        if existente is not None:
            # El alias ya existe: la fila solo le añade este grupo (si no está ya en él, ver más abajo).
            revisada.aviso("El alias ya existe" + (": su contraseña no se cambia." if fila["contrasena"] else "; se le añade este grupo."))
        elif fila["contrasena"]:
            if contrasenas.setdefault(clave, fila["contrasena"]) != fila["contrasena"]:
                revisada.error("Este alias tiene otra contraseña en otra fila; pon la misma o déjala en una sola.")
                continue
        grupo = grupos.get((fila["organizacion"], fila["grupo"]))
        if grupo is None:
            revisada.error(
                f"No existe el grupo «{fila['grupo']}» en «{fila['organizacion']}». Impórtalo antes en «Importar grupos»."
            )
            continue
        grupo_id, organizacion_id = grupo
        rol = roles.get(normalizar(fila["rol"].strip())) if fila["rol"].strip() else Pertenencia.USUARIO
        if rol is None:
            revisada.error(f"No existe el rol «{fila['rol']}». Los roles de grupo son: {', '.join(sorted(set(roles.values())))}.")
            continue
        base, admin_org = _si_o_no(fila["base"]), _si_o_no(fila["admin_org"])
        if base is None or admin_org is None:
            revisada.error("En «Asamblea base» y «Admin de la organización» escribe «sí», «no» o déjalo vacío.")
            continue
        if fila["correo"]:
            try:
                validate_email(fila["correo"])
            except ValidationError:
                revisada.error(f"«{fila['correo']}» no es un correo válido.")
                continue
        if (clave, grupo_id) in vistas:
            revisada.error(f"Esta persona ya está en este grupo más arriba, en la fila {vistas[(clave, grupo_id)]}.")
            continue
        vistas[(clave, grupo_id)] = revisada.numero
        if existente is not None and (existente.pk, grupo_id) in ya_dentro:
            revisada.estado = "existe"
            revisada.aviso("Ya está en este grupo: no se cambia su rol.")
            continue
        revisada.detalle = f"{fila['organizacion']} › {fila['grupo']}" + ("" if rol == Pertenencia.USUARIO else f" ({rol})")
        filas_validas.append(
            {"clave": clave, "alias": alias, "grupo_id": grupo_id, "organizacion_id": organizacion_id, "rol": rol,
             "base": base, "admin_org": admin_org, "correo": fila["correo"], "revisada": revisada}
        )
    # Por persona: contraseña para los nuevos, una sola asamblea base y la base por defecto.
    por_persona = defaultdict(list)
    for fila in filas_validas:
        por_persona[fila["clave"]].append(fila)
    nuevos = {}
    for clave, suyas in por_persona.items():
        existente = existentes.get(clave)
        if existente is None:
            contrasena = contrasenas.get(clave)
            if not contrasena:
                suyas[0]["revisada"].error("Falta la contraseña de este alias nuevo (basta en una de sus filas).")
                continue
            try:
                validate_password(contrasena, user=Usuario(alias=suyas[0]["alias"]))
            except ValidationError as error:
                suyas[0]["revisada"].error("Contraseña no válida: " + " ".join(error.messages))
                continue
            correo = next((fila["correo"] for fila in suyas if fila["correo"]), "")
            nuevos[clave] = {"alias": suyas[0]["alias"], "contrasena": make_password(contrasena), "correo": correo}
        marcadas = [fila for fila in suyas if fila["base"]]
        if len(marcadas) > 1:
            marcadas[1]["revisada"].error("Solo puede haber una asamblea base por persona.")
            continue
        tiene_base = existente is not None and existente.pk in con_base
        if tiene_base and marcadas:
            marcadas[0]["revisada"].aviso("Ya tiene asamblea base: no se cambia.")
            marcadas[0]["base"] = False
        elif not tiene_base and not marcadas:
            suyas[0]["base"] = True
            suyas[0]["revisada"].aviso("Será su asamblea base (es su primera fila y no se marcó ninguna).")
        for fila in suyas:
            if fila["admin_org"] and existente is not None and (existente.pk, fila["organizacion_id"]) in ya_admins:
                fila["revisada"].aviso("Ya es admin de esta organización.")
                fila["admin_org"] = False
    if not revision.hay_errores:
        revision.plan = {
            "usuarios": list(nuevos.values()),
            "pertenencias": [
                {"alias": fila["alias"], "grupo_id": fila["grupo_id"], "organizacion_id": fila["organizacion_id"],
                 "rol": fila["rol"], "base": fila["base"], "admin_org": fila["admin_org"]}
                for fila in filas_validas
            ],
        }
    return revision


# Crea lo que dice el plan de usuarios, todo o nada: los alias nuevos (con su contraseña ya cifrada),
# sus pertenencias (con los servicios de «grupos», que comprueban y avisan) y los admins de
# organización. Devuelve cuántos usuarios y pertenencias se han creado.
#   - plan: el de revisar_usuarios().
@transaction.atomic
def aplicar_usuarios(plan):
    Usuario = get_user_model()
    for datos in plan["usuarios"]:
        usuario = Usuario(alias=datos["alias"], password=datos["contrasena"], correo_alternativo=datos["correo"])
        usuario.full_clean(exclude=["password"])
        usuario.save()
    usuarios = {
        usuario.alias_normalizado: usuario
        for usuario in Usuario.objects.filter(alias_normalizado__in={normalizar_alias(fila["alias"]) for fila in plan["pertenencias"]})
    }
    grupos = Grupo.objects.in_bulk({fila["grupo_id"] for fila in plan["pertenencias"]})
    # Primero las asambleas base, para que la regla de una por persona se compruebe bien.
    for fila in sorted(plan["pertenencias"], key=lambda fila: not fila["base"]):
        usuario = usuarios[normalizar_alias(fila["alias"])]
        admitir(usuario, grupos[fila["grupo_id"]], rol=fila["rol"], es_base=fila["base"])
    # Admins de organización, una sola vez por persona y organización aunque se marque en varias filas.
    nombrados = set()
    for fila in plan["pertenencias"]:
        clave = (normalizar_alias(fila["alias"]), fila["organizacion_id"])
        if fila["admin_org"] and clave not in nombrados:
            nombrados.add(clave)
            nombrar_admin_de_organizacion(usuarios[clave[0]], grupos[fila["grupo_id"]].organizacion)
    return {"usuarios": len(plan["usuarios"]), "pertenencias": len(plan["pertenencias"])}
