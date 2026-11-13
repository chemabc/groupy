"""
Pantallas de la sección «Usuarios» del superadmin: personas de la bóveda, dominios permitidos y alias.

Las personas están en la base de la bóveda y las organizaciones y alias en la de la plataforma: las
pantallas juntan los datos de las dos, pero nunca guardan nada que las una.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef, Subquery
from django.shortcuts import get_object_or_404, redirect, render

from base.tablas import Columna, Filtro, FuenteDeLista, Tabla
from boveda.models import PaseEmitido, Persona
from boveda.servicios import cambiar_datos, dominios_por_organizacion, poner_dominios, registrar_persona, validar_por_superadmin
from grupos.models import Grupo, Organizacion, Pertenencia, camino
from grupos.servicios import grupos_de
from permisos.decoradores import requiere_permiso

from .formularios import FormularioDeAlta, FormularioDeDominios, FormularioDePersona, organizaciones


# Nombres de las organizaciones por su número: {número: nombre}. Una consulta.
def _nombres_de_organizaciones():
    return dict(Organizacion.objects.values_list("pk", "nombre"))


# Pone los errores de un ValidationError de un servicio en el formulario, para que se vean junto a su
# campo (o arriba, si no son de ningún campo).
def _errores_al_formulario(formulario, error):
    if hasattr(error, "error_dict"):
        for campo, errores in error.error_dict.items():
            formulario.add_error(campo if campo in formulario.fields else None, errores)
    else:
        formulario.add_error(None, error)


# ── Bóveda ───────────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Bóveda → Personas»: alta de una persona y lista de todas («Persona 3f2a9c1e», sin nombre),
# con su estado, método, organización y si tiene el pase emitido. Cuesta 3 consultas.
@requiere_permiso("boveda.ver")
def personas(request):
    lista_de_organizaciones = organizaciones()
    formulario = FormularioDeAlta(request.POST or None, organizaciones=lista_de_organizaciones)
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            persona = registrar_persona(datos["nombre"], datos["correo_oficial"], datos["organizacion"])
        except ValidationError as error:
            _errores_al_formulario(formulario, error)
        else:
            return redirect("administracion:persona", persona.pk)
    nombres = dict(lista_de_organizaciones)
    consulta = Persona.objects.annotate(con_pase=Exists(PaseEmitido.objects.filter(persona=OuterRef("pk"))))
    filas = [
        {
            "pk": persona.pk,
            "persona": str(persona),
            "estado": persona.get_estado_display(),
            "metodo": persona.get_metodo_display(),
            "organizacion": nombres.get(persona.organizacion_id, ""),
            "pase": "Sí" if persona.con_pase else "No",
            "creada_el": persona.creada_el,
            "validada_el": persona.validada_el,
        }
        for persona in consulta
    ]
    tabla = Tabla(
        request,
        identificador="personas",
        columnas=[
            Columna("persona", "Persona", enlace="administracion:persona"),
            Columna("estado", "Estado"),
            Columna("metodo", "Método"),
            Columna("organizacion", "Organización"),
            Columna("pase", "Pase emitido"),
            Columna("creada_el", "Registrada"),
            Columna("validada_el", "Validada"),
        ],
        fuente=FuenteDeLista(filas, campos_de_busqueda=["persona", "organizacion"]),
        filtros=[Filtro("estado", "Estado", opciones=tuple((nombre, nombre) for _clave, nombre in Persona.ESTADOS))],
    )
    plantilla = tabla.plantilla_parcial()
    if plantilla:
        return render(request, plantilla, {"tabla": tabla})
    return render(request, "administracion/personas.html", {"tabla": tabla, "formulario": formulario})


# Pantalla de la ficha de una persona: su nombre real y sus datos, que se pueden corregir, y el botón
# para validarla (alta por el superadmin) si está pendiente.
#   - pk: su identificador.
#   - POST «accion»: «guardar» o «validar».
@requiere_permiso("boveda.ver")
def persona(request, pk):
    persona = get_object_or_404(Persona, pk=pk)
    inicial = {"nombre": persona.nombre, "organizacion": persona.organizacion_id, "correo_oficial": persona.correo_oficial}
    lista_de_organizaciones = organizaciones()
    formulario = FormularioDePersona(request.POST or None, initial=inicial, organizaciones=lista_de_organizaciones)
    aviso = ""
    accion = request.POST.get("accion") if request.method == "POST" else None
    if accion == "validar":
        try:
            validar_por_superadmin(persona)
            aviso = "Validada. Su correo se ha borrado (queda su huella) y su pase está marcado como emitido."
        except ValidationError as error:
            formulario.add_error(None, error)
        formulario = FormularioDePersona(initial={**inicial, "correo_oficial": ""}, organizaciones=lista_de_organizaciones)
    elif accion == "guardar" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            cambiar_datos(persona, datos["nombre"], datos["organizacion"], datos["correo_oficial"])
            aviso = "Datos guardados."
        except ValidationError as error:
            _errores_al_formulario(formulario, error)
    contexto = {
        "persona": persona,
        "formulario": formulario,
        "aviso": aviso,
        "organizacion": dict(lista_de_organizaciones).get(persona.organizacion_id, ""),
        "pases": list(persona.pases.all()),
    }
    return render(request, "administracion/persona.html", contexto)


# Pantalla «Bóveda → Dominios permitidos»: cada organización con sus dominios de correo, que se pueden
# cambiar. Los datos se guardan en la bóveda. Cuesta 3 consultas.
#   - POST: organizacion y dominios (uno por línea o separados por comas).
@requiere_permiso("boveda.ver")
def dominios(request):
    aviso, error, con_error = "", "", None
    if request.method == "POST":
        formulario = FormularioDeDominios(request.POST)
        if formulario.is_valid():
            organizacion = formulario.cleaned_data["organizacion"]
            texto = formulario.cleaned_data["dominios"].replace(",", "\n")
            try:
                guardados = poner_dominios(organizacion, texto.splitlines())
                aviso = f"Guardados los dominios de «{_nombres_de_organizaciones().get(organizacion, organizacion)}»: {', '.join(guardados) or 'ninguno (cualquier dominio)'}."
            except ValidationError as excepcion:
                error, con_error = " ".join(excepcion.messages), organizacion
    por_organizacion = dominios_por_organizacion()
    organizaciones = [
        {"pk": pk, "nombre": nombre, "dominios": por_organizacion.get(pk, []), "con_error": pk == con_error}
        for pk, nombre in Organizacion.objects.order_by("nombre").values_list("pk", "nombre")
    ]
    return render(request, "administracion/dominios.html", {"organizaciones": organizaciones, "aviso": aviso, "error": error})


# ── Alias ────────────────────────────────────────────────────────────────────────────────────────────


# Pantalla «Alias → Lista»: todos los alias con su asamblea base, su origen y si son superadmin o están
# activos. Cuesta 2 consultas.
@requiere_permiso("administracion.usuarios")
def alias(request):
    Usuario = get_user_model()
    base = Pertenencia.objects.filter(usuario=OuterRef("pk"), es_base=True).annotate(texto=camino("grupo"))
    consulta = Usuario.objects.annotate(
        asamblea_base=Subquery(base.values("texto")[:1]),
        organizacion_de_la_base=Subquery(base.values("grupo__organizacion__nombre")[:1]),
    )
    filas = [
        {
            "pk": usuario.pk,
            "alias": usuario.alias,
            "asamblea_base": f"{usuario.organizacion_de_la_base} › {usuario.asamblea_base}" if usuario.asamblea_base else "",
            "origen": "Con pase" if usuario.origen == Usuario.CON_PASE else "Alta directa",
            "superadmin": "Sí" if usuario.es_superadmin else "",
            "activo": "Sí" if usuario.activo else "No",
            "activado_el": usuario.activado_el,
        }
        for usuario in consulta
    ]
    tabla = Tabla(
        request,
        identificador="alias",
        columnas=[
            Columna("alias", "Alias", enlace="administracion:alias_ficha"),
            Columna("asamblea_base", "Asamblea base"),
            Columna("origen", "Origen"),
            Columna("superadmin", "Superadmin"),
            Columna("activo", "Activo"),
            Columna("activado_el", "Activado el"),
        ],
        fuente=FuenteDeLista(filas, campos_de_busqueda=["alias", "asamblea_base"]),
        filtros=[Filtro("origen", "Origen", opciones=(("Alta directa", "Alta directa"), ("Con pase", "Con pase")))],
    )
    plantilla = tabla.plantilla_parcial()
    if plantilla:
        return render(request, plantilla, {"tabla": tabla})
    return render(request, "administracion/alias.html", {"tabla": tabla})


# Pantalla de la ficha de un alias: sus datos, todos sus grupos (también los heredados) y botones para
# hacerle (o dejar de hacerle) superadmin y para activar o desactivar su cuenta. Nadie puede quitarse a
# sí mismo el superadmin ni desactivarse (para no quedarse sin entrar).
#   - pk: el número del usuario.
#   - POST «accion»: «superadmin» o «activo» (cambia lo que haya).
@requiere_permiso("administracion.usuarios")
def alias_ficha(request, pk):
    usuario = get_object_or_404(get_user_model(), pk=pk)
    error = ""
    accion = request.POST.get("accion") if request.method == "POST" else None
    if accion in ("superadmin", "activo"):
        if usuario.pk == request.user.pk:
            error = "No puedes quitarte a ti mismo el superadmin ni desactivar tu propia cuenta: pídeselo a otro superadmin."
        else:
            campo = "es_superadmin" if accion == "superadmin" else "activo"
            setattr(usuario, campo, not getattr(usuario, campo))
            usuario.save(update_fields=[campo])
    directas = {pertenencia.grupo_id: pertenencia for pertenencia in usuario.pertenencias.all()}
    grupos = [
        {
            "camino": f"{grupo.organizacion.nombre} › {grupo.camino}",
            "directo": grupo.pk in directas,
            "base": grupo.pk in directas and directas[grupo.pk].es_base,
            "rol": directas[grupo.pk].rol if grupo.pk in directas else "",
        }
        for grupo in Grupo.objects.en_orden_de_arbol().select_related("organizacion").filter(pk__in=grupos_de(usuario))
    ]
    return render(request, "administracion/alias_ficha.html", {"usuario": usuario, "grupos": grupos, "error": error})
