"""
Pantallas del módulo «debates»: la lista, proponer uno, la ficha (las opciones en columnas, con sus
argumentos, votos y recuentos; y lo de la facilitación) y los límites de la plataforma y de cada
organización.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from audiencias.selector import opciones as opciones_de_visibilidad
from base.anclas import buscar_ancla, leer_ancla
from base.markdown import texto_a_html
from base.tablas import Columna, Filtro, FuenteDeLista, Tabla
from grupos.acceso import grupos_donde_puede
from permisos.servicios import SinPermiso, explicar_falta, organizaciones_con

from . import servicios
from .formularios import FormularioDeDebate, FormularioDeLimites
from .models import Argumento, Debate, LimitesDeDebate, Opcion, Voto

# Máximo de debates de la lista (se filtran en el navegador).
MAXIMO = 500


# Pantalla «Participación → Debates»: los debates que ve quien mira, filtrables al momento. 2 consultas.
def lista(request):
    debates = list(servicios.visibles(request.user).select_related("grupo")[:MAXIMO])
    filas = [{"pk": d.pk, "pregunta": d.pregunta, "grupo": d.grupo.nombre, "estado": d.get_estado_display(), "fecha": timezone.localtime(d.creado).strftime("%d/%m/%Y")} for d in debates]
    tabla = Tabla(
        request,
        identificador="debates",
        columnas=[Columna("pregunta", "Pregunta", enlace="debates:debate"), Columna("grupo", "Grupo"), Columna("estado", "Estado"), Columna("fecha", "Propuesto")],
        fuente=FuenteDeLista(filas, campos_de_busqueda=["pregunta", "grupo"]),
        filtros=[Filtro("estado", "Estado", opciones=tuple((n, n) for _c, n in Debate.ESTADOS))],
    )
    plantilla = tabla.plantilla_parcial()
    if plantilla:
        return render(request, plantilla, {"tabla": tabla})
    return render(request, "debates/lista.html", {"tabla": tabla})


# Pantalla «Proponer un debate». Con «?ancla=…» cuelga de algo (toma su grupo y su audiencia); con
# «?pregunta=…» trae la pregunta escrita (por ejemplo, un tema de un acta).
#   - GET «grupo», «ancla», «pregunta».
#   - POST: los campos de FormularioDeDebate.
def nuevo(request):
    usuario = request.user
    ancla = leer_ancla(request.GET.get("ancla", ""))
    elemento = buscar_ancla(*ancla) if ancla[0] else None
    grupos = grupos_donde_puede(usuario, "debates.abrir")
    if not grupos and not (elemento and getattr(elemento, "grupo_id", None)):
        raise SinPermiso(explicar_falta("debates.abrir"))
    con_grupo = elemento is not None and getattr(elemento, "grupo_id", None)
    grupo = elemento.grupo if con_grupo else next((g for g in grupos if str(g.pk) == request.GET.get("grupo", "")), grupos[0])
    formulario = FormularioDeDebate(
        request.POST or None, initial={"pregunta": request.GET.get("pregunta", "")},
        visibilidades=None if con_grupo else opciones_de_visibilidad(grupo),
    )
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            debate = servicios.proponer(
                usuario, datos["pregunta"], datos["descripcion"], formulario.lista_de_opciones(), grupo=grupo,
                visibilidad=datos.get("visibilidad", "grupo:0"), ancla=ancla if elemento else (None, None), cierra=datos["cierra"],
                justificacion=datos["justificacion"],
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("debates:debate", debate.pk)
    contexto = {"formulario": formulario, "elemento": elemento, "grupos": [] if con_grupo else grupos, "grupo": grupo}
    return render(request, "debates/nuevo.html", contexto)


# Lo que hace cada botón de la ficha (función interna de debate()). Lanza ValidationError si no se puede.
#   - accion: «votar», «argumentar», «opcion», «facilitar», «ampliar» o «cerrar».
def _hacer(request, debate, accion):
    usuario, datos = request.user, request.POST
    opcion = get_object_or_404(Opcion, pk=datos["opcion"], debate=debate) if datos.get("opcion") else None
    if accion == "votar":
        argumento = get_object_or_404(Argumento, pk=datos["argumento"], opcion__debate=debate) if datos.get("argumento") else None
        servicios.votar(usuario, debate, datos.get("tipo", ""), opcion=opcion if not argumento else None, argumento=argumento, justificacion=datos.get("justificacion", ""))
    elif accion == "argumentar":
        padre = get_object_or_404(Argumento, pk=datos["padre"], opcion__debate=debate) if datos.get("padre") else None
        servicios.argumentar(usuario, opcion or padre.opcion, datos.get("texto", ""), a_favor=datos.get("a_favor") != "no", padre=padre)
    elif accion == "opcion":
        servicios.proponer_opcion(usuario, debate, datos.get("texto", ""), de_consenso=bool(datos.get("de_consenso")))
    elif accion == "facilitar":
        persona = get_user_model().objects.filter(alias__iexact=datos.get("alias", "").strip()).first()
        if persona is None:
            raise ValidationError("No ve este debate nadie con ese alias.")
        servicios.dar_facilitacion(usuario, debate, persona)
    elif accion == "ampliar":
        servicios.ampliar(usuario, debate, datos.get("visibilidad", ""))
    elif accion == "cerrar":
        servicios.cerrar(usuario, debate, datos.get("conclusion", ""), elegida=opcion)


# Botones de voto de una opción o de un argumento, listos para pintar: (tipo, icono, nombre, cuántos, si
# es el voto de quien mira, si pide justificación). Sin consultas.
#   - cuentas: {tipo: número} de ese elemento.
#   - mio: el tipo que ha votado quien mira, o None.
#   - tipos: los votos que admite (de opción o de argumento).
def _botones(cuentas, mio, tipos):
    return [
        (tipo, nombre.split(" ", 1)[0], nombre.split(" ", 1)[1], cuentas.get(tipo, 0), mio == tipo, tipo in servicios.CON_JUSTIFICACION)
        for tipo, nombre in Voto.TIPOS if tipo in tipos
    ]


# Ficha de un debate: la pregunta y su contexto; la clasificación de las opciones (solo a favor, y a favor
# menos en contra); las opciones en columnas, cada una con sus recuentos, sus justificaciones (sin
# nombre), sus argumentos (con alias, y sus respuestas) y sus botones de voto; las opciones propuestas que
# esperan apoyos; «todas me valen»; y, para quien facilita, ampliar y cerrar. Unas 9 consultas.
#   - POST «accion»: ver _hacer().
def debate(request, pk):
    usuario = request.user
    debate = get_object_or_404(Debate.objects.select_related("grupo__organizacion", "elegida"), pk=pk)
    if not servicios.ve(usuario, debate):
        raise SinPermiso("Este debate no es para ti: solo lo ven las personas a las que llega.")
    error = ""
    if request.method == "POST":
        try:
            _hacer(request, debate, request.POST.get("accion", ""))
        except ValidationError as excepcion:
            error = " ".join(excepcion.messages)
        else:
            # Vuelve a la ficha, a la altura de la opción en la que se ha hecho algo.
            ancla = f"#opcion-{request.POST['opcion']}" if request.POST.get("opcion", "").isdigit() else ""
            return redirect(reverse("debates:debate", args=[debate.pk]) + ancla)
    por_opcion, por_argumento, justificaciones, todas, mios = servicios.recuentos(debate, usuario)
    argumentos = list(Argumento.objects.filter(opcion__debate=debate).select_related("autor"))
    hijos = {}
    for argumento in argumentos:
        cuentas = por_argumento.get(argumento.pk, {})
        argumento.cuentas, argumento.mio = cuentas, mios.get((None, argumento.pk))
        argumento.apoyos = servicios.balance(cuentas)[0]
        argumento.botones = _botones(cuentas, argumento.mio, servicios.VOTOS_DE_ARGUMENTO)
        hijos.setdefault((argumento.opcion_id, argumento.padre_id), []).append(argumento)
    for argumento in argumentos:
        argumento.hijos = hijos.get((argumento.opcion_id, argumento.pk), [])
    columnas, propuestas = [], []
    for opcion in debate.opciones.all():
        cuentas = por_opcion.get(opcion.pk, {})
        opcion.cuentas, opcion.mio = cuentas, mios.get((opcion.pk, None))
        opcion.a_favor, opcion.neto = servicios.balance(cuentas)
        opcion.raices = hijos.get((opcion.pk, None), [])
        suyos = [a for a in argumentos if a.opcion_id == opcion.pk]
        opcion.argumentos_a_favor = sum(1 for a in suyos if a.a_favor)
        opcion.mas_votado = max(suyos, key=lambda a: a.apoyos, default=None)
        opcion.justificaciones = [("⭐" if tipo == Voto.MUY_IMPORTANTE else "⛔", texto) for tipo, texto in justificaciones.get(opcion.pk, [])]
        opcion.botones = _botones(cuentas, opcion.mio, servicios.VOTOS_DE_OPCION if opcion.estado == Opcion.ABIERTA else (Voto.APOYO,))
        (columnas if opcion.estado == Opcion.ABIERTA else propuestas).append(opcion)
    de_facilitacion = servicios.facilitacion(debate)
    facilita = servicios.facilita(usuario, debate, de_facilitacion)
    limites = servicios.limites_de(debate.grupo.organizacion_id)
    contexto = {
        "debate": debate,
        "descripcion": texto_a_html(debate.descripcion),
        "columnas": columnas,
        "propuestas": propuestas,
        "solo_a_favor": sorted(columnas, key=lambda o: -o.a_favor),
        "neto": sorted(columnas, key=lambda o: -o.neto),
        "todas": todas,
        "todas_mio": mios.get((None, None)) == Voto.TODAS_ME_VALEN,
        "abierto": debate.estado == Debate.ABIERTO,
        "facilitacion": de_facilitacion,
        "facilita": facilita,
        "ampliaciones": [(clave, texto) for clave, texto in opciones_de_visibilidad(debate.grupo) if clave in servicios.AMPLITUD and debate.visibilidad in servicios.AMPLITUD and servicios.AMPLITUD.index(clave) > servicios.AMPLITUD.index(debate.visibilidad)] if facilita else [],
        "limites": limites,
        "ancla": buscar_ancla(debate.ancla_tipo, debate.ancla_id) if debate.ancla_tipo else None,
        "error": error,
    }
    return render(request, "debates/debate.html", contexto)


# Pantalla «Administrar → Mi organización → Debates»: los límites de los debates de toda la plataforma (el
# superadmin) y de cada organización que administra quien mira. Cada nivel solo puede ser más estricto.
#   - GET «organizacion»: cuál se edita (vacío: la plataforma, solo el superadmin).
#   - POST: los campos de FormularioDeLimites.
def limites(request):
    usuario = request.user
    organizaciones = list(organizaciones_con(usuario, "debates.limitar"))
    if not organizaciones and not usuario.is_superuser:
        raise SinPermiso(explicar_falta("debates.limitar"))
    ambitos = ([(None, "Toda la plataforma")] if usuario.is_superuser else []) + [(o.pk, o.nombre) for o in organizaciones]
    elegido = request.GET.get("organizacion", "")
    organizacion_id = int(elegido) if elegido.isdigit() else (None if usuario.is_superuser else ambitos[0][0])
    if organizacion_id not in dict(ambitos):
        raise SinPermiso(explicar_falta("debates.limitar"))
    fila = LimitesDeDebate.objects.filter(organizacion_id=organizacion_id).first() or LimitesDeDebate(organizacion_id=organizacion_id)
    formulario = FormularioDeLimites(request.POST or None, instance=fila)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        return redirect(f"{request.path}?organizacion={organizacion_id or ''}")
    contexto = {
        "formulario": formulario, "ambitos": ambitos, "elegido": organizacion_id,
        "valen": servicios.limites_de(organizacion_id) if organizacion_id else None, "por_defecto": servicios.POR_DEFECTO,
    }
    return render(request, "debates/limites.html", contexto)
