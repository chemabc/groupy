"""
Pantalla «Administrar → Grupos que administro → Miembros» (petición de la persona usuaria, [A-55]).

Las personas de los grupos que administra quien mira y de sus subgrupos (todas, el superadmin), en la tabla
filtrable común: una fila por pertenencia (persona y grupo), con su rol, si es su asamblea base y desde
cuándo. Las filas de un grupo que no es su asamblea base salen más tenues. Si alguien lleva más tiempo sin
usar la plataforma del que dicen los ajustes de inactividad (grupos/inactividad.py), sale «Sin actividad».

Desde aquí se gestiona lo mismo que en la ficha de cada grupo, pero junto:
- en cada fila, cambiar el rol y sacar del grupo;
- marcando varias filas, sacarlas o cambiarles el rol de una vez;
- arriba, admitir a una persona en uno de los grupos.
Cada cosa pide el mismo permiso que en la ficha del grupo («grupos.admitir»; hacer o deshacer admins,
«grupos.nombrar_admin_grupo»). Las filas que no se pueden tocar salen sin controles.
"""

from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from base.tablas import Columna, Filtro, FuenteDeLista, Tabla
from permisos.servicios import SinPermiso, explicar_falta, permisos_de

from . import inactividad, servicios
from .acceso import grupos_que_administra
from .arboles import nombres_de_roles_de_grupo
from .formularios import FormularioDeAdmisionEnGrupo
from .models import Grupo, Pertenencia, camino

# Clave de la sesión donde se guarda, entre el envío y la página siguiente, lo que ha pasado.
AVISO = "miembros_aviso"


class Permisos:
    """Lo que quien mira puede hacer en cada grupo, sacado de su mapa de permisos (sin consultas)."""

    # Lee el mapa de permisos una vez.
    def __init__(self, usuario):
        self.todo = usuario.is_superuser
        self.grupos = {} if self.todo else permisos_de(usuario).grupos

    # Dice si puede admitir, sacar y cambiar el rol en un grupo.
    def admite(self, grupo_id):
        return self.todo or "grupos.admitir" in self.grupos.get(grupo_id, ())

    # Dice si puede hacer o deshacer admins de un grupo.
    def nombra(self, grupo_id):
        return self.todo or "grupos.nombrar_admin_grupo" in self.grupos.get(grupo_id, ())

    # Roles que puede dar en un grupo: todos si nombra admins; si no, todos menos el de admin.
    def roles_que_da(self, grupo_id, roles):
        return [(codigo, nombre) for codigo, nombre in roles.items() if self.nombra(grupo_id) or codigo != Pertenencia.ADMIN_GRUPO]


# Comprueba que se puede tocar una pertenencia y le aplica una operación: «sacar» o «rol:<código>».
# Lanza ValidationError si no se puede.
#   - pertenencia: la pertenencia (con su usuario).
#   - operacion: qué se hace.
#   - permisos: Permisos de quien lo hace.
#   - roles: {código: nombre} de los roles de grupo.
def _aplicar(pertenencia, operacion, permisos, roles):
    if not permisos.admite(pertenencia.grupo_id):
        raise ValidationError(f"No puedes cambiar a quién hay en el grupo de {pertenencia.usuario.alias}.")
    nuevo_rol = operacion.partition(":")[2] if operacion.startswith("rol:") else ""
    if operacion.startswith("rol:") and nuevo_rol not in roles:
        raise ValidationError("Ese rol no existe.")
    if Pertenencia.ADMIN_GRUPO in (pertenencia.rol, nuevo_rol) and not permisos.nombra(pertenencia.grupo_id):
        raise ValidationError(f"Hacer o deshacer admins pide un permiso que no tienes ({pertenencia.usuario.alias}).")
    if operacion == "sacar":
        servicios.sacar(pertenencia.usuario, pertenencia.grupo)
    elif nuevo_rol != pertenencia.rol:
        servicios.cambiar_rol(pertenencia, nuevo_rol)


# Atiende lo que se envía desde la pantalla: una acción de una fila («rol:<pertenencia>» o
# «sacar:<pertenencia>»), varias filas a la vez («en_bloque», con «seleccion» y «operacion») o admitir.
# Devuelve (texto de lo que ha pasado, formulario de admitir con sus errores o None).
#   - request: la petición (POST).
#   - administrados: ids de los grupos que administra (None: todos, el superadmin).
#   - permisos, roles: como en _aplicar.
#   - grupos_para_admitir: pares (id, camino) de los grupos donde puede admitir.
def _atender(request, administrados, permisos, roles, grupos_para_admitir):
    accion = request.POST.get("accion", "")
    if accion == "admitir":
        formulario = FormularioDeAdmisionEnGrupo(request.POST, grupos=grupos_para_admitir, roles=list(roles.items()))
        if not formulario.is_valid():
            return "", formulario
        grupo = Grupo.objects.get(pk=formulario.cleaned_data["grupo"])
        rol = formulario.cleaned_data["rol"]
        if rol == Pertenencia.ADMIN_GRUPO and not permisos.nombra(grupo.pk):
            formulario.add_error("rol", "Hacer admin a alguien pide un permiso que no tienes en ese grupo.")
            return "", formulario
        try:
            servicios.admitir(formulario.cleaned_data["usuario"], grupo, rol=rol)
        except ValidationError as error:
            formulario.add_error(None, error)
            return "", formulario
        return f"{formulario.cleaned_data['usuario'].alias} ya está en {grupo.nombre}.", None
    if accion == "en_bloque":
        numeros, operacion = request.POST.getlist("seleccion"), request.POST.get("operacion", "")
    else:
        operacion, _, numero = accion.partition(":")
        numeros = [numero]
        if operacion == "rol":
            operacion = f"rol:{request.POST.get(f'rol-{numero}', '')}"
    if operacion != "sacar" and not operacion.startswith("rol:"):
        return "No se ha elegido qué hacer.", None
    pertenencias = Pertenencia.objects.filter(pk__in=[n for n in numeros if n.isdigit()]).select_related("usuario", "grupo")
    if administrados is not None:
        pertenencias = pertenencias.filter(grupo_id__in=administrados)
    hechas, fallos = 0, []
    for pertenencia in pertenencias:
        try:
            _aplicar(pertenencia, operacion, permisos, roles)
            hechas += 1
        except ValidationError as error:
            fallos.append(" ".join(error.messages))
    if not hechas and not fallos:
        return "No se ha marcado a nadie.", None
    texto = f"Hecho con {hechas} {'fila' if hechas == 1 else 'filas'}."
    return texto + (f" No se ha podido con {len(fallos)}: {' '.join(fallos)}" if fallos else ""), None


# La pantalla. Cuesta 7 consultas (el usuario, los grupos que administra, los roles, los grupos, los que los
# contienen, los plazos de inactividad y las pertenencias con sus personas), sean cuantas sean las filas.
#   - POST: ver _atender.
def miembros(request):
    usuario = request.user
    administrados = None if usuario.is_superuser else grupos_que_administra(usuario)
    if administrados is not None and not administrados:
        raise SinPermiso(explicar_falta("grupos.ver_arbol"))
    permisos = Permisos(usuario)
    roles = nombres_de_roles_de_grupo()
    grupos = Grupo.objects.en_orden_de_arbol().select_related("organizacion")
    if administrados is not None:
        grupos = grupos.filter(pk__in=administrados)
    grupos = list(grupos)
    grupos_para_admitir = [(g.pk, f"{g.organizacion.nombre} › {g.camino}") for g in grupos if permisos.admite(g.pk)]
    admision = None
    if request.method == "POST":
        texto, admision = _atender(request, administrados, permisos, roles, grupos_para_admitir)
        if admision is None:
            request.session[AVISO] = texto
            return redirect(request.get_full_path())
    aviso = request.session.pop(AVISO, "")

    pertenencias = Pertenencia.objects.filter(grupo_id__in=[g.pk for g in grupos]).select_related("usuario").annotate(camino_del_grupo=camino("grupo")).order_by("usuario__alias", "camino_del_grupo")
    dias = inactividad.dias_por_grupo(grupos)
    filas = []
    for pertenencia in pertenencias:
        plazo = dias[pertenencia.grupo_id]
        gestiona = permisos.admite(pertenencia.grupo_id)
        filas.append({
            "pk": pertenencia.pk, "alias": pertenencia.usuario.alias, "grupo": pertenencia.camino_del_grupo,
            "rol": roles.get(pertenencia.rol, pertenencia.rol), "codigo_del_rol": pertenencia.rol,
            "base": "Sí" if pertenencia.es_base else "No", "desde": pertenencia.desde,
            "actividad": f"Sin actividad (más de {plazo} días)" if inactividad.sin_actividad(pertenencia.usuario, plazo) else "",
            "gestiona": gestiona and (permisos.nombra(pertenencia.grupo_id) or pertenencia.rol != Pertenencia.ADMIN_GRUPO),
            "roles": permisos.roles_que_da(pertenencia.grupo_id, roles),
            "_clase": "" if pertenencia.es_base else "opacity-60",
        })
    tabla = Tabla(
        request,
        identificador="miembros",
        columnas=[
            Columna("pk", "✓", ordenable=False, filtrable=False, plantilla="grupos/miembros/_marcar.html"),
            Columna("alias", "Persona"), Columna("grupo", "Grupo"),
            Columna("rol", "Rol", plantilla="grupos/miembros/_rol.html"),
            Columna("base", "Asamblea base"), Columna("desde", "Desde"), Columna("actividad", "Actividad"),
            Columna("codigo_del_rol", "", ordenable=False, filtrable=False, plantilla="grupos/miembros/_sacar.html"),
        ],
        fuente=FuenteDeLista(filas, campos_de_busqueda=["alias", "grupo"]),
        filtros=[
            Filtro("grupo", "Grupo", tuple((c, c) for c in sorted({f["grupo"] for f in filas}))),
            Filtro("rol", "Rol", tuple((n, n) for n in roles.values())),
            Filtro("base", "Asamblea base", (("Sí", "Sí"), ("No", "No"))),
            Filtro("actividad", "Actividad", tuple((a, a) for a in sorted({f["actividad"] for f in filas} - {""}))),
        ],
    )
    plantilla = tabla.plantilla_parcial()
    if plantilla:
        return render(request, plantilla, {"tabla": tabla})
    # En bloque, el rol de admin solo se ofrece a quien puede nombrar admins en alguno de sus grupos.
    nombra = any(permisos.nombra(g.pk) for g in grupos)
    operaciones = [("sacar", "Sacar del grupo")] + [
        (f"rol:{codigo}", f"Cambiar el rol a «{nombre}»") for codigo, nombre in roles.items() if nombra or codigo != Pertenencia.ADMIN_GRUPO
    ]
    contexto = {
        "tabla": tabla, "hay": bool(filas), "aviso": aviso, "operaciones": operaciones,
        "admision": admision or FormularioDeAdmisionEnGrupo(grupos=grupos_para_admitir, roles=list(roles.items())),
        "puede_admitir": bool(grupos_para_admitir),
    }
    return render(request, "grupos/miembros/miembros.html", contexto)
