"""
Pantallas de la sección «Organizaciones y grupos» (ver docs/diseno.md, apartado 8.1):

- Mis grupos: los grupos de quien mira, en árbol, por organización.
- Árbol: los grupos que administra (todos, si es superadmin), con su número de personas y sus admins.
- Ficha de un grupo: camino, subgrupos, admins, miembros (si los puede ver) y, para quien lo administra,
  editar, crear subgrupos, admitir, sacar y cambiar roles.
- Ficha de una organización: sus datos, si sus miembros ven la lista de miembros y sus admins.
- Relaciones: las relaciones libres entre grupos.
- Invitaciones: las de otras organizaciones a sus grupos y las que sus grupos han hecho.

Qué grupos ve cada persona lo decide grupos/acceso.py; quién puede hacer cada cosa, «permisos». Los
cambios se hacen con grupos/servicios.py.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Case, Count, IntegerField, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Coalesce
from django.contrib.postgres.aggregates import StringAgg
from django.shortcuts import get_object_or_404, redirect, render

from base.registro import registro
from base.tablas import Columna, Filtro, FuenteDeLista, Tabla
from permisos.models import Rol
from permisos.servicios import SinPermiso, exigir, explicar_falta, permisos_de, puede

from . import servicios
from .acceso import alcance_de, grupos_visibles, ve_miembros
from .formularios import (
    FormularioDeAdmision,
    FormularioDeAlias,
    FormularioDeGrupo,
    FormularioDeOrganizacion,
    FormularioDeOrganizacionNueva,
    FormularioDeRelacion,
)
from .models import (
    AdminDeOrganizacion,
    Contencion,
    Grupo,
    InvitacionDeGrupo,
    Organizacion,
    Pertenencia,
    RelacionEntreGrupos,
    camino,
)


# ── Ayudas comunes ───────────────────────────────────────────────────────────────────────────────────


# Nombres visibles de los roles de grupo, por su código: {"usuario": "Usuario", …}. Una consulta.
def _roles_de_grupo():
    return dict(Rol.objects.filter(nivel=Rol.GRUPO).order_by("nombre").values_list("codigo", "nombre"))


# Pasa los mensajes de un ValidationError a un solo texto, para mostrarlo arriba de la ficha.
def _texto_del_error(error):
    return " ".join(error.messages)


# Número de personas distintas de un grupo contando sus subgrupos (cada persona una vez), como
# subconsulta para anotar una consulta de grupos. PostgreSQL la resuelve dentro de la misma consulta.
def _personas_del_grupo():
    personas = (
        Pertenencia.objects.filter(grupo__ascendencia__antecesor=OuterRef("pk"))
        .order_by()
        .values("grupo__ascendencia__antecesor")
        .annotate(numero=Count("usuario", distinct=True))
        .values("numero")
    )
    return Coalesce(Subquery(personas), 0)


# Alias de los admins de un grupo, separados por comas, como subconsulta para anotar una consulta de
# grupos.
def _admins_del_grupo():
    admins = (
        Pertenencia.objects.filter(grupo=OuterRef("pk"), rol=Pertenencia.ADMIN_GRUPO)
        .order_by()
        .values("grupo")
        .annotate(texto=StringAgg("usuario__alias", delimiter=", ", order_by="usuario__alias"))
        .values("texto")
    )
    return Subquery(admins)


# ── Mis grupos ───────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Mis grupos»: por cada organización, sus grupos en árbol. Los directos llevan su rol y si son
# la asamblea base; los que solo contienen a uno de los suyos salen como heredados. Cuesta 4 consultas.
def mis_grupos(request):
    usuario = request.user
    directas = {pertenencia.grupo_id: pertenencia for pertenencia in Pertenencia.objects.filter(usuario=usuario)}
    roles = _roles_de_grupo() if directas else {}
    admin_de = set(AdminDeOrganizacion.objects.filter(usuario=usuario).values_list("organizacion_id", flat=True))
    consulta = Grupo.objects.en_orden_de_arbol().select_related("organizacion").filter(
        pk__in=Contencion.objects.filter(descendiente_id__in=list(directas)).values("antecesor_id")
    )
    organizaciones = {}
    for grupo in consulta if directas else []:
        bloque = organizaciones.setdefault(
            grupo.organizacion_id, {"organizacion": grupo.organizacion, "admin": grupo.organizacion_id in admin_de, "grupos": []}
        )
        pertenencia = directas.get(grupo.pk)
        bloque["grupos"].append(
            {
                "grupo": grupo,
                "nivel": grupo.camino.count(" › "),
                "directo": pertenencia is not None,
                "base": pertenencia is not None and pertenencia.es_base,
                "rol": roles.get(pertenencia.rol, pertenencia.rol) if pertenencia and pertenencia.rol != Pertenencia.USUARIO else "",
            }
        )
    contexto = {"organizaciones": list(organizaciones.values()), "superadmin": usuario.is_superuser}
    return render(request, "grupos/mis_grupos.html", contexto)


# ── Árbol ────────────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Árbol»: las organizaciones que administra (todas, el superadmin) y la tabla de los grupos que
# administra, con su ámbito, su número de personas y sus admins. El superadmin crea aquí organizaciones.
# Cuesta 6 consultas.
#   - POST: los datos de FormularioDeOrganizacionNueva (solo el superadmin).
def arbol(request):
    usuario = request.user
    alcance = alcance_de(usuario)
    if not alcance.todo and not alcance.administrados:
        raise SinPermiso(explicar_falta("grupos.ver_arbol"))
    nueva = FormularioDeOrganizacionNueva(request.POST or None) if alcance.todo else None
    if nueva is not None and request.method == "POST" and nueva.is_valid():
        datos = nueva.cleaned_data
        try:
            organizacion, _grupo = servicios.crear_organizacion(datos["nombre"], datos["primer_grupo"], datos["descripcion"])
        except ValidationError as error:
            nueva.add_error(None, error)
        else:
            return redirect("grupos:organizacion", organizacion.pk)
    grupos = grupos_visibles(alcance, solo_administrados=True).annotate(
        personas=_personas_del_grupo(), admins=_admins_del_grupo()
    )
    filas = [
        {
            "pk": grupo.pk,
            "grupo": grupo.camino,
            "organizacion": grupo.organizacion.nombre,
            "ambito": grupo.ambito,
            "personas": grupo.personas,
            "admins": grupo.admins or "",
        }
        for grupo in grupos
    ]
    nombres = sorted({fila["organizacion"] for fila in filas})
    tabla = Tabla(
        request,
        identificador="grupos",
        columnas=[
            Columna("grupo", "Grupo", enlace="grupos:grupo"),
            Columna("organizacion", "Organización"),
            Columna("ambito", "Ámbito"),
            Columna("personas", "Personas"),
            Columna("admins", "Admins"),
        ],
        fuente=FuenteDeLista(filas, campos_de_busqueda=["grupo", "organizacion", "ambito", "admins"]),
        filtros=[Filtro("organizacion", "Organización", opciones=tuple((nombre, nombre) for nombre in nombres))],
    )
    plantilla = tabla.plantilla_parcial()
    if plantilla:
        return render(request, plantilla, {"tabla": tabla})
    if alcance.todo:
        organizaciones = Organizacion.objects.order_by("nombre")
    else:
        organizaciones = Organizacion.objects.filter(admins__usuario=usuario).order_by("nombre")
    return render(request, "grupos/arbol.html", {"tabla": tabla, "organizaciones": organizaciones, "nueva": nueva})


# ── Ficha de un grupo ────────────────────────────────────────────────────────────────────────────────


# Pantalla de la ficha de un grupo. La ven sus miembros (también los de sus subgrupos) y quienes lo
# administran. Cuesta unas 11 consultas, sea cual sea el número de miembros.
#   - pk: el número del grupo.
#   - POST «accion»: editar, subgrupo, admitir, sacar o rol (cada una pide su permiso).
def grupo(request, pk):
    usuario = request.user
    grupo = get_object_or_404(Grupo.objects.con_camino().select_related("organizacion"), pk=pk)
    alcance = alcance_de(usuario)
    if not alcance.ve(grupo.pk):
        raise SinPermiso(
            f"La ficha de «{grupo}» solo la ven sus miembros (también los de sus subgrupos) y quienes lo administran."
        )
    puede_editar = puede(usuario, "grupos.editar_grupo", grupo=grupo)
    puede_mover = puede(usuario, "grupos.editar_organizacion", organizacion=grupo.organizacion_id)
    puede_subgrupo = puede(usuario, "grupos.crear_subgrupo", grupo=grupo)
    puede_admitir = puede(usuario, "grupos.admitir", grupo=grupo)
    puede_nombrar = puede(usuario, "grupos.nombrar_admin_grupo", grupo=grupo)
    roles = _roles_de_grupo()
    roles_que_da = [(codigo, nombre) for codigo, nombre in roles.items() if puede_nombrar or codigo != Pertenencia.ADMIN_GRUPO]

    accion = request.POST.get("accion") if request.method == "POST" else None
    datos = request.POST if accion else None
    padres = _padres_posibles(grupo) if puede_mover else None
    edicion = FormularioDeGrupo(
        datos if accion == "editar" else None,
        initial={"nombre": grupo.nombre, "descripcion": grupo.descripcion, "ambito": grupo.ambito, "padre": grupo.padre_id},
        padres=padres,
    )
    subgrupo = FormularioDeGrupo(datos if accion == "subgrupo" else None)
    admision = FormularioDeAdmision(datos if accion == "admitir" else None, roles=roles_que_da)
    error = ""
    try:
        if accion == "editar":
            exigir(usuario, "grupos.editar_grupo", grupo=grupo)
            if edicion.is_valid():
                cambios = dict(edicion.cleaned_data)
                if "padre" in cambios:
                    cambios["padre"] = Grupo.objects.get(pk=cambios["padre"]) if cambios["padre"] else None
                servicios.editar_grupo(grupo, **cambios)
                return redirect("grupos:grupo", grupo.pk)
        elif accion == "subgrupo":
            exigir(usuario, "grupos.crear_subgrupo", grupo=grupo)
            if subgrupo.is_valid():
                nuevo = servicios.crear_grupo(grupo.organizacion, padre=grupo, **subgrupo.cleaned_data)
                return redirect("grupos:grupo", nuevo.pk)
        elif accion == "admitir":
            exigir(usuario, "grupos.admitir", grupo=grupo)
            if admision.is_valid():
                if admision.cleaned_data["rol"] == Pertenencia.ADMIN_GRUPO:
                    exigir(usuario, "grupos.nombrar_admin_grupo", grupo=grupo)
                servicios.admitir(admision.cleaned_data["usuario"], grupo, rol=admision.cleaned_data["rol"])
                return redirect("grupos:grupo", grupo.pk)
        elif accion in ("sacar", "rol"):
            exigir(usuario, "grupos.admitir", grupo=grupo)
            pertenencia = get_object_or_404(Pertenencia.objects.select_related("usuario"), pk=request.POST.get("pertenencia"), grupo=grupo)
            nuevo_rol = request.POST.get("rol", "") if accion == "rol" else ""
            if Pertenencia.ADMIN_GRUPO in (pertenencia.rol, nuevo_rol):
                exigir(usuario, "grupos.nombrar_admin_grupo", grupo=grupo)
            if accion == "sacar":
                servicios.sacar(pertenencia.usuario, grupo)
            else:
                servicios.cambiar_rol(pertenencia, nuevo_rol)
            return redirect("grupos:grupo", grupo.pk)
    except ValidationError as excepcion:
        error = _texto_del_error(excepcion)

    ve_lista = ve_miembros(usuario, grupo, alcance)
    contexto = {
        "grupo": grupo,
        "antecesores": list(
            Contencion.objects.filter(descendiente=grupo, distancia__gt=0).order_by("-distancia").values_list("antecesor_id", "antecesor__nombre")
        ),
        "subgrupos": list(grupo.hijos.annotate(personas=_personas_del_grupo()).order_by("nombre")),
        "admins": list(Pertenencia.objects.filter(grupo=grupo, rol=Pertenencia.ADMIN_GRUPO).select_related("usuario").order_by("rol_desde")),
        "admins_de_organizacion": list(AdminDeOrganizacion.objects.filter(organizacion=grupo.organizacion_id).select_related("usuario").order_by("desde")),
        "ve_lista": ve_lista,
        "puede_editar": puede_editar,
        "puede_subgrupo": puede_subgrupo,
        "puede_admitir": puede_admitir,
        "roles_que_da": roles_que_da,
        "edicion": edicion,
        "subgrupo": subgrupo,
        "admision": admision,
        "error": error,
        "abrir": accion,
    }
    tabla = None
    if ve_lista:
        tabla, contexto["directos"] = _miembros(request, grupo, roles, puede_admitir)
        plantilla = tabla.plantilla_parcial()
        if plantilla:
            return render(request, plantilla, {"tabla": tabla})
    contexto["tabla"] = tabla
    return render(request, "grupos/grupo.html", contexto)


# Grupos de la organización que pueden ser padre de este: todos menos él mismo y sus subgrupos (sería un
# círculo). Lista de (id, camino). Una consulta.
def _padres_posibles(grupo):
    debajo = Contencion.objects.filter(antecesor=grupo).values("descendiente_id")
    consulta = Grupo.objects.en_orden_de_arbol().filter(organizacion_id=grupo.organizacion_id).exclude(pk__in=debajo)
    return [(candidato.pk, candidato.camino) for candidato in consulta]


# Tabla de todas las personas del grupo y de sus subgrupos (una fila por pertenencia) y lista de los
# miembros directos con su pertenencia (para gestionarlos). Una consulta.
#   - request: la petición (para la tabla).
#   - grupo: el grupo.
#   - roles: {código: nombre} de los roles de grupo.
#   - con_gestion: si se devuelven los miembros directos (solo para quien puede admitir).
def _miembros(request, grupo, roles, con_gestion):
    pertenencias = list(
        Pertenencia.objects.filter(grupo__ascendencia__antecesor=grupo)
        .select_related("usuario")
        .annotate(camino_del_grupo=camino("grupo"))
        .order_by("usuario__alias")
    )
    filas = [
        {
            "pk": pertenencia.pk,
            "alias": pertenencia.usuario.alias,
            "grupo": pertenencia.camino_del_grupo,
            "rol": roles.get(pertenencia.rol, pertenencia.rol),
            "desde": pertenencia.desde,
        }
        for pertenencia in pertenencias
    ]
    tabla = Tabla(
        request,
        identificador="miembros",
        columnas=[Columna("alias", "Alias"), Columna("grupo", "En el grupo"), Columna("rol", "Rol"), Columna("desde", "Desde")],
        fuente=FuenteDeLista(filas, campos_de_busqueda=["alias", "grupo"]),
        filtros=[Filtro("rol", "Rol", opciones=tuple((nombre, nombre) for nombre in roles.values()))],
    )
    directos = [p for p in pertenencias if p.grupo_id == grupo.pk] if con_gestion else []
    return tabla, directos


# ── Ficha de una organización ────────────────────────────────────────────────────────────────────────


# Pantalla de la ficha de una organización, para su admin y el superadmin: sus datos, si sus miembros
# ven la lista de miembros, sus grupos principales y sus admins (que nombra o quita el superadmin).
# Cuesta unas 7 consultas.
#   - pk: el número de la organización.
#   - POST «accion»: datos, nombrar o quitar.
def organizacion(request, pk):
    usuario = request.user
    organizacion = get_object_or_404(Organizacion, pk=pk)
    exigir(usuario, "grupos.editar_organizacion", organizacion=organizacion)
    accion = request.POST.get("accion") if request.method == "POST" else None
    datos = FormularioDeOrganizacion(
        request.POST if accion == "datos" else None,
        initial={"nombre": organizacion.nombre, "descripcion": organizacion.descripcion, "miembros_ven_miembros": organizacion.miembros_ven_miembros},
    )
    nombrar = FormularioDeAlias(request.POST if accion == "nombrar" else None)
    error = ""
    try:
        if accion == "datos" and datos.is_valid():
            servicios.editar_organizacion(organizacion, **datos.cleaned_data)
            return redirect("grupos:organizacion", organizacion.pk)
        if accion in ("nombrar", "quitar") and not usuario.is_superuser:
            raise SinPermiso("Los admins de una organización los nombra o los quita el superadmin.")
        if accion == "nombrar" and nombrar.is_valid():
            servicios.nombrar_admin_de_organizacion(nombrar.cleaned_data["usuario"], organizacion)
            return redirect("grupos:organizacion", organizacion.pk)
        if accion == "quitar":
            quien = get_object_or_404(get_user_model(), pk=request.POST.get("usuario"))
            servicios.quitar_admin_de_organizacion(quien, organizacion)
            return redirect("grupos:organizacion", organizacion.pk)
    except ValidationError as excepcion:
        error = _texto_del_error(excepcion)
    contexto = {
        "organizacion": organizacion,
        "datos": datos,
        "nombrar": nombrar if usuario.is_superuser else None,
        "admins": list(AdminDeOrganizacion.objects.filter(organizacion=organizacion).select_related("usuario").order_by("desde")),
        "principales": list(organizacion.grupos.filter(padre=None).annotate(personas=_personas_del_grupo()).order_by("nombre")),
        "numero_de_grupos": organizacion.grupos.count(),
        "error": error,
        "abrir": accion,
    }
    return render(request, "grupos/organizacion.html", contexto)


# ── Relaciones ───────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Relaciones»: las relaciones de los grupos que ve quien mira, con el formulario para crear una
# y botones para borrar las de los grupos que puede editar. Cuesta unas 6 consultas.
#   - POST «accion»: crear (datos de FormularioDeRelacion) o borrar (relacion).
def relaciones(request):
    usuario = request.user
    alcance = alcance_de(usuario)
    editables = _grupos_con_permiso(usuario, "grupos.editar_grupo")
    origenes = list(Grupo.objects.en_orden_de_arbol().select_related("organizacion").filter(**({} if editables is None else {"pk__in": editables})))
    organizaciones = {grupo.organizacion_id for grupo in origenes}
    destinos = [
        (grupo.pk, f"{grupo.organizacion} › {grupo.camino}")
        for grupo in Grupo.objects.en_orden_de_arbol().select_related("organizacion").filter(organizacion_id__in=organizaciones)
    ] if origenes else []
    accion = request.POST.get("accion") if request.method == "POST" else None
    formulario = FormularioDeRelacion(
        request.POST if accion == "crear" else None,
        origenes=[(grupo.pk, f"{grupo.organizacion} › {grupo.camino}") for grupo in origenes],
        destinos=destinos,
    )
    error = ""
    try:
        if accion == "crear" and formulario.is_valid():
            datos = formulario.cleaned_data
            origen = next(grupo for grupo in origenes if grupo.pk == datos["origen"])
            destino = Grupo.objects.get(pk=datos["destino"])
            servicios.relacionar(origen, destino, datos["tipo"], datos["descripcion"])
            return redirect("grupos:relaciones")
        if accion == "borrar":
            relacion = get_object_or_404(RelacionEntreGrupos, pk=request.POST.get("relacion"))
            if not _puede_tocar(usuario, relacion, editables):
                raise SinPermiso(explicar_falta("grupos.editar_grupo", grupo=relacion.origen_id))
            relacion.delete()
            return redirect("grupos:relaciones")
    except ValidationError as excepcion:
        error = _texto_del_error(excepcion)
    consulta = RelacionEntreGrupos.objects.select_related("origen__organizacion").annotate(
        camino_origen=camino("origen"), camino_destino=camino("destino")
    ).order_by("origen__organizacion__nombre", "camino_origen", "tipo")
    visibles = alcance.visibles()
    if visibles is not None:
        consulta = consulta.filter(Q(origen_id__in=visibles) | Q(destino_id__in=visibles))
    filas = [{"relacion": relacion, "editable": _puede_tocar(usuario, relacion, editables)} for relacion in consulta]
    contexto = {"filas": filas, "formulario": formulario if origenes else None, "error": error, "abrir": accion}
    return render(request, "grupos/relaciones.html", contexto)


# Ids de los grupos donde una persona tiene un permiso, sacados de su cálculo en la caché (sin
# consultas), o None si es superadmin (en todos).
def _grupos_con_permiso(usuario, permiso):
    if usuario.is_superuser:
        return None
    return {grupo for grupo, codigos in permisos_de(usuario).grupos.items() if permiso in codigos}


# Dice si una persona puede borrar una relación: si puede editar alguno de sus dos grupos.
#   - editables: lo que devuelve _grupos_con_permiso (None: todos).
def _puede_tocar(usuario, relacion, editables):
    return editables is None or relacion.origen_id in editables or relacion.destino_id in editables


# ── Invitaciones ─────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Invitaciones»: las que han recibido los grupos de quien mira y las que esos grupos han
# hecho, primero las pendientes. Botones para aceptar o rechazar (quien tiene «grupos.responder_invitacion»
# en el grupo invitado) y para retirar (los miembros del grupo que invitó). Cuesta unas 5 consultas.
#   - POST «accion»: aceptar, rechazar o retirar, con «invitacion».
def invitaciones(request):
    usuario = request.user
    alcance = alcance_de(usuario)
    accion = request.POST.get("accion") if request.method == "POST" else None
    error = ""
    if accion in ("aceptar", "rechazar", "retirar"):
        invitacion = get_object_or_404(InvitacionDeGrupo.objects.select_related("grupo_invitado__organizacion"), pk=request.POST.get("invitacion"))
        try:
            if accion == "retirar":
                servicios.retirar_invitacion(invitacion, usuario)
            else:
                servicios.responder_invitacion(invitacion, usuario, acepta=accion == "aceptar")
            return redirect("grupos:invitaciones")
        except ValidationError as excepcion:
            error = _texto_del_error(excepcion)
    consulta = (
        InvitacionDeGrupo.objects.select_related(
            "grupo_que_invita__organizacion", "grupo_invitado__organizacion", "invitada_por", "respondida_por"
        )
        .annotate(
            pendiente=Case(When(estado=InvitacionDeGrupo.PENDIENTE, then=Value(0)), default=Value(1), output_field=IntegerField())
        )
        .order_by("pendiente", "-creada_el", "-pk")
    )
    visibles = alcance.visibles()
    if visibles is not None:
        consulta = consulta.filter(Q(grupo_invitado_id__in=visibles) | Q(grupo_que_invita_id__in=visibles))
    recibidas, enviadas = [], []
    for invitacion in consulta:
        pendiente = invitacion.estado == InvitacionDeGrupo.PENDIENTE
        ancla = registro.anclas.get(invitacion.ancla_tipo)
        fila = {
            "invitacion": invitacion,
            "que": f"{ancla.descripcion if ancla else invitacion.ancla_tipo} n.º {invitacion.ancla_id}",
            "puede_responder": pendiente and puede(usuario, "grupos.responder_invitacion", grupo=invitacion.grupo_invitado),
            "puede_retirar": pendiente and invitacion.grupo_que_invita_id in alcance.mios,
        }
        if visibles is None or invitacion.grupo_invitado_id in visibles:
            recibidas.append(fila)
        else:
            enviadas.append(fila)
    contexto = {"recibidas": recibidas, "enviadas": enviadas, "todo": alcance.todo, "error": error}
    return render(request, "grupos/invitaciones.html", contexto)


# Pantalla «Administrar → Mi organización → Datos»: las organizaciones que administra quien mira (el
# superadmin: todas), cada una con el enlace a su ficha, donde se cambian sus datos, sus admins y si sus
# miembros ven la lista de miembros. Dos consultas (los permisos salen de la caché).
def mis_organizaciones(request):
    usuario = request.user
    consulta = Organizacion.objects.order_by("nombre")
    if not usuario.is_superuser:
        ids = [org for org, codigos in permisos_de(usuario).organizaciones.items() if "grupos.editar_organizacion" in codigos]
        if not ids:
            raise SinPermiso(explicar_falta("grupos.editar_organizacion"))
        consulta = consulta.filter(pk__in=ids)
    return render(request, "grupos/mis_organizaciones.html", {"organizaciones": list(consulta)})
