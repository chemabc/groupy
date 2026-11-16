"""
Pantallas del módulo «documentos»: la lista filtrable, crear uno (escribir un texto, subir un archivo o
enlazar; suelto o colgado de algo), la ficha (leer con la autoría de cada párrafo, el registro de cambios,
los acuerdos, comentar, aprobar y dar la redacción; o ver un archivo con sus versiones o un enlace),
escribir (con vista previa al momento), descargar, la papelera y el espacio para archivos.
"""

import difflib

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.apps import apps
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from audiencias.selector import opciones
from base import editor
from base.anclas import buscar_ancla, leer_ancla
from base.markdown import texto_a_html
from base.registro import registro
from base.tablas import Columna, Filtro, FuenteDeLista, RangoDeFechas, Tabla
from grupos.acceso import grupos_donde_puede
from permisos.decoradores import requiere_permiso
from permisos.servicios import SinPermiso, explicar_falta, organizaciones_con

from . import archivos, servicios
from .formularios import FormularioDeArchivo, FormularioDeDocumentoNuevo, FormularioDeEnlace, FormularioDeLimites, FormularioDeVersion
from .models import Documento

# Máximo de documentos de la lista (se filtran en el navegador).
MAXIMO = 500


# Pantalla «Participación → Documentos»: todo lo que ve quien mira (textos, archivos y enlaces), filtrable
# al momento por nombre, tipo, formato, de dónde cuelga, grupo, estado y rango de fechas. 2 consultas.
def lista(request):
    usuario = request.user
    documentos = list(servicios.visibles(usuario).select_related("grupo")[:MAXIMO])
    permisos = servicios.permisos_en_lista(usuario, documentos)
    filas = [
        {
            "pk": d.pk, "titulo": d.titulo, "descripcion": d.descripcion, "tipo": d.get_tipo_display(), "formato": _formato(d), "cuelga": _cuelga_de(d.ancla_tipo),
            "grupo": d.grupo.nombre, "estado": _estado(d), "fecha": timezone.localtime(d.actualizado).date(),
            # Lo que puede hacer quien mira (R U D), su texto para buscar y filtrar, y si puede cambiarlo.
            "permisos": _letras(permisos[d.pk]), "cambia": "Sí" if permisos[d.pk].u else "No", "detalle": permisos[d.pk],
        }
        for d in documentos
    ]
    # Las opciones de los desplegables salen de lo que hay (así no salen opciones vacías).
    def opciones_de(campo):
        return tuple((valor, valor) for valor in sorted({fila[campo] for fila in filas}))

    tabla = Tabla(
        request,
        identificador="documentos",
        columnas=[
            Columna("titulo", "Nombre", plantilla="documentos/_celda_de_nombre.html"), Columna("tipo", "Tipo"), Columna("formato", "Formato"),
            Columna("cuelga", "Cuelga de"), Columna("grupo", "Grupo"), Columna("estado", "Estado"), Columna("fecha", "Último cambio"),
            Columna("permisos", "Puedo", ordenable=False, plantilla="documentos/_celda_de_permisos.html"),
        ],
        fuente=FuenteDeLista(filas, campos_de_busqueda=["titulo", "descripcion", "grupo", "formato"]),
        filtros=[
            Filtro("tipo", "Tipo", opciones=opciones_de("tipo")),
            Filtro("formato", "Formato", opciones=opciones_de("formato")),
            Filtro("cuelga", "Cuelga de", opciones=opciones_de("cuelga")),
            Filtro("grupo", "Grupo", opciones=opciones_de("grupo")),
            Filtro("estado", "Estado", opciones=opciones_de("estado")),
            Filtro("cambia", "Puedo cambiarlo", opciones=(("Sí", "Sí"), ("No", "No"))),
        ],
        fechas=RangoDeFechas("fecha", "Último cambio"),
    )
    plantilla = tabla.plantilla_parcial()
    if plantilla:
        return render(request, plantilla, {"tabla": tabla})
    # C (crear): en qué grupos puede crear documentos quien mira o, si en ninguno, por qué y a quién pedirlo.
    donde_crea = grupos_donde_puede(usuario, "documentos.crear")
    contexto = {"tabla": tabla, "donde_crea": donde_crea, "por_que_no_crea": "" if donde_crea else explicar_falta("documentos.crear")}
    return render(request, "documentos/lista.html", contexto)


# Las iniciales de lo que se puede hacer con un documento, para la celda «Puedo» (y para buscar en ella):
# «R U D», «R» o «R U».
def _letras(permisos):
    return " ".join(letra for letra, si in (("R", permisos.r), ("U", permisos.u), ("D", permisos.d)) if si)


# El formato de un documento, para la lista: «Markdown», «Typst», la extensión de un archivo («PDF») o
# «Enlace a otra web» / «Enlace a un documento».
def _formato(documento):
    if documento.tipo == Documento.ARCHIVO:
        return documento.extension.upper()
    if documento.tipo == Documento.ENLACE:
        return "Enlace a un documento" if documento.enlazado_id else "Enlace a otra web"
    return "Typst" if documento.formato == Documento.TYPST else "Markdown"


# El estado de un documento, para la lista: el de los textos (borrador, aprobado); los archivos y enlaces
# no tienen («—»).
def _estado(documento):
    return documento.get_estado_display() if documento.tipo in Documento.ESCRITOS else "—"


# De qué cuelga un documento, en una palabra («Evento», «Tarea», «Consulta»…), sacada del modelo que declara
# esa ancla; «Nada» si no cuelga de nada.
def _cuelga_de(ancla_tipo):
    declarada = registro.anclas.get(ancla_tipo) if ancla_tipo else None
    if declarada is None:
        return "Nada"
    return str(apps.get_model(declarada.modelo)._meta.verbose_name).capitalize()


# De dónde se crea algo nuevo (función interna de nuevo, subir y enlazar): con «?ancla=eventos.evento:12»
# cuelga de esa reunión (toma su grupo y su visibilidad); si no, del grupo elegido en «?grupo=». Devuelve
# (ancla, elemento, grupos, grupo).
def _donde(request):
    usuario = request.user
    ancla = leer_ancla(request.GET.get("ancla", ""))
    elemento = buscar_ancla(*ancla) if ancla[0] else None
    grupos = [] if elemento else grupos_donde_puede(usuario, "documentos.crear")
    if elemento is None and not grupos:
        raise SinPermiso(explicar_falta("documentos.crear"))
    grupo = None if elemento else next((g for g in grupos if str(g.pk) == request.GET.get("grupo", "")), grupos[0])
    return (ancla if elemento else (None, None)), elemento, grupos, grupo


# Lo común a las tres pantallas de crear: aquello de lo que cuelga, los grupos, el elegido y las pestañas
# (Escribir · Subir un archivo · Enlazar), que conservan «?ancla=» y «?grupo=».
def _contexto_de_crear(request, elemento, grupos, grupo, activa):
    consulta = request.GET.urlencode()
    pestanas = [
        ("nuevo", "Escribir un texto", reverse("documentos:nuevo")),
        ("subir", "Subir un archivo", reverse("documentos:subir")),
        ("enlazar", "Enlazar", reverse("documentos:enlazar")),
    ]
    return {
        "elemento": elemento, "grupos": grupos, "grupo": grupo, "ancla": request.GET.get("ancla", ""),
        "pestanas": [{"codigo": c, "nombre": n, "url": f"{u}?{consulta}" if consulta else u, "activa": c == activa} for c, n, u in pestanas],
    }


# Pantalla «Nuevo documento». Con «?ancla=eventos.evento:12» cuelga de esa reunión (toma su grupo y su
# visibilidad); si no, se elige el grupo arriba y quién lo ve en el formulario.
#   - GET «ancla», «grupo», «tipo»: de qué cuelga, el grupo elegido y el tipo propuesto.
#   - POST: los campos de FormularioDeDocumentoNuevo.
def nuevo(request):
    usuario = request.user
    ancla, elemento, grupos, grupo = _donde(request)
    inicial = {"tipo": request.GET.get("tipo") or (Documento.ODD if ancla[0] == "eventos.evento" else Documento.LIBRE)}
    if elemento is not None:
        inicial["titulo"] = f"{dict(Documento.TIPOS).get(inicial['tipo'], 'Documento')}: {elemento}"
    formulario = FormularioDeDocumentoNuevo(request.POST or None, initial=inicial, visibilidades=None if elemento else opciones(grupo))
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            documento = servicios.crear(
                usuario, datos["tipo"], datos["titulo"], grupo=grupo, visibilidad=datos.get("visibilidad", "privado"), ancla=ancla,
                formato=datos["formato"], descripcion=datos["descripcion"],
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("documentos:escribir", documento.pk)
    contexto = {"formulario": formulario, **_contexto_de_crear(request, elemento, grupos, grupo, "nuevo")}
    return render(request, "documentos/nuevo.html", contexto)


# Pantalla «Subir un archivo»: el archivo (PDF, imagen, documento abierto o texto), su nombre y, si no
# cuelga de nada, quién lo ve. Se comprueba y pasa por el antivirus (documentos/archivos.py).
#   - GET «ancla», «grupo»: como en nuevo.
#   - POST: los campos de FormularioDeArchivo (con el fichero).
def subir(request):
    usuario = request.user
    ancla, elemento, grupos, grupo = _donde(request)
    formulario = FormularioDeArchivo(request.POST or None, request.FILES or None, visibilidades=None if elemento else opciones(grupo))
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            documento = servicios.subir_archivo(
                usuario, datos["archivo"], datos["titulo"], grupo=grupo, visibilidad=datos.get("visibilidad", "privado"), ancla=ancla,
                descripcion=datos["descripcion"],
            )
        except ValidationError as error:
            formulario.add_error("archivo", error)
        else:
            return redirect("documentos:documento", documento.pk)
    contexto = {"formulario": formulario, "maximo": archivos.TAMANO_MAXIMO // 1024 // 1024, **_contexto_de_crear(request, elemento, grupos, grupo, "subir")}
    return render(request, "documentos/subir.html", contexto)


# Pantalla «Enlazar»: un enlace a otra web (Drive…) o a otro documento de la plataforma que quien mira ve.
#   - GET «ancla», «grupo»: como en nuevo.
#   - POST: los campos de FormularioDeEnlace.
def enlazar(request):
    usuario = request.user
    ancla, elemento, grupos, grupo = _donde(request)
    formulario = FormularioDeEnlace(
        request.POST or None, documentos=_para_enlazar(usuario), visibilidades=None if elemento else opciones(grupo)
    )
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            documento = servicios.enlazar(
                usuario, datos["titulo"], url=datos["url"], enlazado=datos["documento"], grupo=grupo,
                visibilidad=datos.get("visibilidad", "privado"), ancla=ancla, descripcion=datos["descripcion"],
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("documentos:documento", documento.pk)
    contexto = {"formulario": formulario, **_contexto_de_crear(request, elemento, grupos, grupo, "enlazar")}
    return render(request, "documentos/enlazar.html", contexto)


# Los textos que una persona puede enlazar: los que ve, escritos en el editor, los más recientes primero.
def _para_enlazar(usuario):
    return servicios.visibles(usuario).filter(tipo__in=Documento.ESCRITOS).select_related("grupo").order_by("-actualizado")[:MAXIMO]


# Busca un documento que quien mira puede ver, o da 404 (función interna de las pantallas).
#   - aunque_en_papelera: si se deja abrir también lo eliminado (la ficha, para recuperarlo; solo quien
#     puede recuperarlo).
def _documento(usuario, pk, aunque_en_papelera=False):
    documento = get_object_or_404(Documento.objects.select_related("grupo__organizacion", "origen", "enlazado"), pk=pk)
    if not servicios.ve(usuario, documento):
        raise SinPermiso("Este documento no es para ti: solo lo ven las personas a las que llega.")
    if documento.en_papelera_desde and not (aunque_en_papelera and servicios.puede_eliminar(usuario, documento)):
        raise Http404("Este documento está en la papelera.")
    return documento


# Ficha de un documento: el texto párrafo a párrafo, cada uno con quién ha contribuido (en claro, entre
# paréntesis); arriba, el registro de cambios plegado; los acuerdos y los temas pendientes de un acta; los
# comentarios; los botones de escribir, crear el acta, aprobar y dar la redacción; sus versiones, sus comentarios en el texto y sus «Opciones». Unas 11 consultas.
#   - POST «accion»: «comentar» (con «texto»), «aprobar», «acta», «dar» (con «alias») o «quitar» (con
#     «persona»).
def documento(request, pk):
    usuario = request.user
    documento = _documento(usuario, pk, aunque_en_papelera=True)
    accion = request.POST.get("accion") if request.method == "POST" else None
    if documento.tipo not in Documento.ESCRITOS:
        return _archivo_o_enlace(request, documento, accion)
    error = ""
    try:
        if accion in ("eliminar", "recuperar"):
            return _eliminar_o_recuperar(request, documento, accion)
        if accion == "comentar":
            servicios.comentar(usuario, documento, request.POST.get("texto", ""))
        elif accion == "aprobar":
            servicios.aprobar(usuario, documento)
        elif accion == "acta":
            acta = servicios.acta_desde(usuario, documento)
            return redirect("documentos:escribir", acta.pk)
        elif accion == "dar":
            persona = get_user_model().objects.filter(alias__iexact=request.POST.get("alias", "").strip()).first()
            if persona is None:
                raise ValidationError("No ve este documento nadie con ese alias.")
            servicios.dar_redaccion(usuario, documento, persona)
        elif accion == "quitar":
            persona = get_object_or_404(get_user_model(), pk=request.POST.get("persona"))
            servicios.quitar_redaccion(usuario, documento, persona)
        elif accion == "opciones":
            if not servicios.puede_cambiar_opciones(usuario, documento):
                raise ValidationError("Las opciones del documento las cambia la administración de su grupo.")
            opciones = FormularioDeLimites(request.POST, instance=servicios.fila_de_limites(documento_id=documento.pk))
            if not opciones.is_valid():
                raise ValidationError("Revisa las opciones: solo números enteros.")
            opciones.save()
        if accion:
            return redirect("documentos:documento", documento.pk)
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
    # Markdown se pinta convertido; Typst, tal cual (se ve compilado en el editor y en el PDF).
    convertir = texto_a_html if documento.formato == Documento.MARKDOWN else None
    bloques = [
        {"html": convertir(texto) if convertir else None, "texto": texto, "autores": documento.autorias[numero] if numero < len(documento.autorias) else []}
        for numero, texto in enumerate(servicios.parrafos(documento.texto))
    ]
    cambia_opciones = servicios.puede_cambiar_opciones(usuario, documento)
    contexto = {
        "documento": documento,
        "bloques": bloques,
        "cambios": list(documento.cambios.all()[:200]),
        "versiones": list(documento.versiones.defer("texto")[:100]),
        "version_cada": servicios.VERSION_CADA,
        "comentarios_en_el_texto": list(documento.comentarios_en_el_texto.all()),
        "comentarios": list(documento.comentarios.select_related("usuario")),
        "acuerdos": servicios.acuerdos(documento) if documento.tipo == Documento.ACTA else [],
        "temas": servicios.temas(documento) if documento.tipo == Documento.ACTA else [],
        "redaccion": servicios.redaccion(documento),
        "escribe": servicios.puede_escribir(usuario, documento),
        "en_directo": editor.activo() and documento.estado == Documento.BORRADOR,
        "aprueba": servicios.puede_aprobar(usuario, documento),
        "crea_acta": documento.tipo == Documento.ODD and servicios.puede_escribir(usuario, documento, aunque_aprobado=True),
        "ancla": buscar_ancla(documento.ancla_tipo, documento.ancla_id) if documento.ancla_tipo else None,
        "error": error,
        "limites": servicios.limites_de(documento.grupo, documento),
        "opciones": FormularioDeLimites(instance=servicios.fila_de_limites(documento_id=documento.pk)) if cambia_opciones else None,
        "elimina": servicios.puede_eliminar(usuario, documento),
        "congelado": servicios.congelado(documento),
        "permisos": servicios.permisos_de(usuario, documento),
    }
    return render(request, "documentos/documento.html", contexto)


# Lleva un documento a la papelera o lo recupera, y vuelve a donde toca: tras eliminar, a la papelera
# (donde se ve lo eliminado, con «Recuperar»); tras recuperar, a su ficha. Función interna de documento.
def _eliminar_o_recuperar(request, documento, accion):
    if accion == "eliminar":
        servicios.eliminar(request.user, documento)
        return redirect("documentos:papelera")
    servicios.recuperar(request.user, documento)
    return redirect("documentos:documento", documento.pk)


# Ficha de un archivo o de un enlace: el archivo a la vista (PDF e imágenes) o para descargar, con sus
# versiones; o adónde lleva el enlace. Para quien puede: subir otra versión, cambiar el nombre (y el
# destino de un enlace), eliminar o recuperar. Unas 10 consultas.
#   - accion: «version» (con «archivo»), «cambiar» (con «titulo», «url», «documento»), «eliminar» o
#     «recuperar».
def _archivo_o_enlace(request, documento, accion):
    usuario = request.user
    modifica = servicios.puede_modificar(usuario, documento)
    nueva = FormularioDeVersion(request.POST if accion == "version" else None, request.FILES if accion == "version" else None)
    cambio = FormularioDeEnlace(
        request.POST if accion == "cambiar" else None, documentos=_para_enlazar(usuario) if documento.tipo == Documento.ENLACE and modifica else Documento.objects.none(),
        visibilidades=None, solo_nombre=documento.tipo == Documento.ARCHIVO,
        initial={"titulo": documento.titulo, "descripcion": documento.descripcion, "url": documento.url, "documento": documento.enlazado_id},
    )
    error = ""
    try:
        if accion in ("eliminar", "recuperar"):
            return _eliminar_o_recuperar(request, documento, accion)
        if accion == "version" and nueva.is_valid():
            servicios.nueva_version(usuario, documento, nueva.cleaned_data["archivo"])
            return redirect("documentos:documento", documento.pk)
        if accion == "cambiar" and cambio.is_valid():
            datos = cambio.cleaned_data
            servicios.cambiar(
                usuario, documento, datos["titulo"], url=datos.get("url", ""), enlazado=datos.get("documento"), descripcion=datos["descripcion"],
            )
            return redirect("documentos:documento", documento.pk)
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
    versiones = list(documento.archivos.select_related("subida_por")) if documento.tipo == Documento.ARCHIVO else []
    contexto = {
        "documento": documento,
        "versiones": versiones,
        "actual": versiones[0] if versiones else None,
        "se_ve": bool(versiones) and archivos.se_ve_en_el_navegador(versiones[0].extension),
        "es_pdf": bool(versiones) and versiones[0].extension == "pdf",
        "ve_enlazado": documento.enlazado is not None and servicios.ve(usuario, documento.enlazado),
        "cambios": list(documento.cambios.all()[:200]),
        "ancla": buscar_ancla(documento.ancla_tipo, documento.ancla_id) if documento.ancla_tipo else None,
        "modifica": modifica,
        "elimina": servicios.puede_eliminar(usuario, documento),
        "congelado": servicios.congelado(documento),
        "nueva": nueva,
        "cambio": cambio,
        "error": error,
        "permisos": servicios.permisos_de(usuario, documento),
    }
    return render(request, "documentos/archivo_o_enlace.html", contexto)


# Entrega una versión de un archivo (la última, si no se dice cuál) a quien ve el documento: los PDF y las
# imágenes, para verlos en el navegador; lo demás, para descargar. El fichero no tiene dirección pública.
#   - pk: el documento.
#   - numero: la versión (o None: la última).
#   - GET «descargar»: descargar siempre, aunque se pueda ver en el navegador.
def descargar(request, pk, numero=None):
    documento = _documento(request.user, pk, aunque_en_papelera=True)
    versiones = documento.archivos.all()
    version = get_object_or_404(versiones, numero=numero) if numero else versiones.first()
    if version is None:
        raise Http404("Este archivo no tiene versiones.")
    en_el_navegador = archivos.se_ve_en_el_navegador(version.extension) and not request.GET.get("descargar")
    respuesta = FileResponse(
        version.fichero.open("rb"), content_type=version.tipo_mime, as_attachment=not en_el_navegador, filename=version.nombre_original
    )
    # Que el navegador no adivine otro tipo de contenido (nunca ejecuta lo que no es lo que dice ser).
    respuesta["X-Content-Type-Options"] = "nosniff"
    return respuesta


# Pantalla «Documentos → Papelera»: lo eliminado que quien mira puede recuperar, con cuándo se eliminó,
# quién y cuántos días le quedan antes de borrarse de verdad. Al recuperar uno, se va a su ficha.
#   - POST «recuperar»: el número del documento.
def papelera(request):
    usuario = request.user
    if request.method == "POST":
        documento = _documento(usuario, request.POST.get("recuperar", "0") if request.POST.get("recuperar", "").isdigit() else 0, aunque_en_papelera=True)
        servicios.recuperar(usuario, documento)
        return redirect("documentos:documento", documento.pk)
    dias = servicios.dias_en_la_papelera()
    filas = []
    for documento in servicios.papelera_de(usuario):
        quedan = dias - (timezone.now() - documento.en_papelera_desde).days
        filas.append({"documento": documento, "quedan": max(quedan, 0)})
    return render(request, "documentos/papelera.html", {"filas": filas, "dias": dias})


# Pantalla «Plataforma → Espacio para archivos» (solo el superadmin): cuánto pueden ocupar los archivos
# de cada organización y cuánto ocupan ya. La fila «Toda la plataforma» vale para las que no tienen la suya.
#   - POST «organizacion» (vacío: la plataforma) y «megas» (vacío en una organización: quitar la suya).
@requiere_permiso("documentos.espacio")
def espacio(request):
    error = ""
    if request.method == "POST":
        try:
            servicios.poner_espacio(request.POST.get("organizacion", ""), request.POST.get("megas", ""))
        except ValidationError as excepcion:
            error = " ".join(excepcion.messages)
        else:
            return redirect("documentos:espacio")
    contexto = {"filas": servicios.espacios(), "plataforma": servicios.espacio_maximo(None) // 1024 // 1024, "error": error}
    return render(request, "documentos/espacio.html", contexto)


# Pantalla «Escribir»: el título y el texto en Markdown a la izquierda y la vista previa a la derecha, que
# se pone al día mientras se escribe (htmx). Solo para quien tiene la redacción.
# Si hay editor en tiempo real (base/editor.py), el texto se escribe ahí entre varias personas a la vez y
# se guarda solo; quien no tiene la redacción lo sigue en directo, de solo lectura.
#   - GET «sin_directo»: usar el formulario aunque haya editor en tiempo real (si no conecta).
#   - POST «titulo», «descripcion», «texto», «version» (la que tenía al abrir, para no pisar a otra persona)
#     y «nota» (si se pone, la versión queda guardada a mano con ella); con el editor en tiempo real, solo
#     «titulo» y «descripcion» («Guardar versión» va a guardar_version).
def escribir(request, pk):
    usuario = request.user
    documento = _documento(usuario, pk)
    # «?sin_directo=1»: el formulario de siempre (la salida si el editor en tiempo real no responde).
    en_vivo = None if request.GET.get("sin_directo") else editor.pase(usuario, servicios.ANCLA, documento.pk)
    if en_vivo:
        error = ""
        if request.method == "POST":
            try:
                servicios.cambiar_titulo(usuario, documento, request.POST.get("titulo", ""), request.POST.get("descripcion"))
            except ValidationError as excepcion:
                error = " ".join(excepcion.messages)
            else:
                return redirect("documentos:escribir", documento.pk)
        contexto = {"documento": documento, "en_vivo": en_vivo, "error": error}
        return render(request, "documentos/escribir_en_vivo.html", contexto)
    if not servicios.puede_escribir(usuario, documento):
        raise SinPermiso("Solo quien tiene la redacción puede escribirlo (y no si ya está aprobado). Puedes comentarlo en su ficha.")
    error = ""
    titulo, descripcion, texto, version = documento.titulo, documento.descripcion, documento.texto, documento.version
    if request.method == "POST":
        titulo, texto, version = request.POST.get("titulo", "").strip() or documento.titulo, request.POST.get("texto", ""), request.POST.get("version", "0")
        descripcion = request.POST.get("descripcion", "")
        try:
            servicios.guardar(usuario, documento, titulo, texto, version, descripcion=descripcion, nota=request.POST.get("nota", ""))
        except ValidationError as excepcion:
            error = " ".join(excepcion.messages)
        else:
            return redirect("documentos:documento", documento.pk)
    contexto = {
        "documento": documento, "titulo": titulo, "descripcion": descripcion, "texto": texto, "version": version, "vista": texto_a_html(texto), "error": error,
    }
    return render(request, "documentos/escribir.html", contexto)


# «Guardar versión» desde el editor en tiempo real (botón encima del editor; lo pide la isla «editorEnVivo»):
# cierra la versión de ahora con la nota, si la hay, y lo que se escriba después va a una nueva. Responde
# en JSON con el mensaje que se enseña: {"mensaje": …} o {"error": …}.
#   - POST «texto»: lo que hay en el editor de quien pulsa (el editor guarda cada pocos segundos y lo último
#     podría no haber llegado); «nota»: lo que se cambió (opcional).
@require_POST
def guardar_version(request, pk):
    documento = _documento(request.user, pk)
    texto = request.POST.get("texto")
    try:
        version = servicios.guardar_version(request.user, documento, texto, request.POST.get("nota", ""))
    except ValidationError as excepcion:
        return JsonResponse({"error": " ".join(excepcion.messages)}, status=400)
    hora = timezone.localtime(version.cerrada).strftime("%H:%M")
    return JsonResponse({"mensaje": f"Guardada la versión {version.numero} a las {hora}" + (f": «{version.nota}»." if version.nota else ".")})


# Vista previa del texto mientras se escribe: devuelve el HTML del Markdown recibido (lo pide htmx desde
# «Escribir»). Sin consultas.
#   - POST «texto»: lo escrito.
@require_POST
def vista_previa(request):
    if len(request.POST.get("texto", "")) > 200_000:
        raise Http404("Texto demasiado largo.")
    return render(request, "documentos/_vista_previa.html", {"vista": texto_a_html(request.POST.get("texto", ""))})


# Pantalla «Administrar → Mi organización → Documentos»: cuántas personas escriben y comentan a la vez los
# documentos de toda la plataforma (el superadmin), de cada organización y de cada grupo que administra
# quien mira (valen también en sus subgrupos). Cada documento puede tener además los suyos (en sus
# «Opciones»). Vale siempre el más estricto.
#   - GET «nivel»: «» (la plataforma, solo el superadmin), «o<número>» (una organización) o «g<número>» (un grupo).
#   - POST: los campos de FormularioDeLimites.
def limites(request):
    usuario = request.user
    organizaciones = list(organizaciones_con(usuario, "documentos.limitar"))
    grupos = grupos_donde_puede(usuario, "documentos.limitar")
    if not organizaciones and not grupos and not usuario.is_superuser:
        raise SinPermiso(explicar_falta("documentos.limitar"))
    niveles = [("", "Toda la plataforma")] if usuario.is_superuser else []
    niveles += [(f"o{o.pk}", f"Organización: {o.nombre}") for o in organizaciones]
    niveles += [(f"g{g.pk}", f"Grupo: {g.organizacion.nombre} › {g.camino}") for g in grupos]
    elegido = request.GET.get("nivel", niveles[0][0])
    if elegido not in dict(niveles):
        raise SinPermiso(explicar_falta("documentos.limitar"))
    numero = int(elegido[1:]) if elegido else None
    fila = servicios.fila_de_limites(organizacion_id=numero if elegido.startswith("o") else None, grupo_id=numero if elegido.startswith("g") else None)
    formulario = FormularioDeLimites(request.POST or None, instance=fila)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        return redirect(f"{request.path}?nivel={elegido}")
    grupo = next((g for g in grupos if g.pk == numero), None) if elegido.startswith("g") else None
    contexto = {"formulario": formulario, "niveles": niveles, "elegido": elegido, "valen": servicios.limites_de(grupo) if grupo else None, "por_defecto": servicios.POR_DEFECTO}
    return render(request, "documentos/limites.html", contexto)


# Una versión anterior de un documento: su texto y lo que cambia de ella a lo de ahora (líneas quitadas
# en rojo y añadidas en verde). Quien tiene la redacción puede volver a ella (queda como una versión
# nueva). Tres consultas.
#   - POST «accion» = «volver».
def version(request, pk, numero):
    usuario = request.user
    documento = _documento(usuario, pk)
    elegida = get_object_or_404(documento.versiones, numero=numero)
    error = ""
    if request.method == "POST" and request.POST.get("accion") == "volver":
        try:
            servicios.volver_a_version(usuario, documento, numero)
        except ValidationError as excepcion:
            error = " ".join(excepcion.messages)
        else:
            return redirect("documentos:documento", documento.pk)
    diferencias = [
        ("quitada" if linea.startswith("-") else "anadida" if linea.startswith("+") else "igual", linea)
        for linea in difflib.unified_diff(elegida.texto.splitlines(), documento.texto.splitlines(), "versión", "ahora", lineterm="", n=2)
        if not linea.startswith(("---", "+++"))
    ]
    contexto = {
        "documento": documento, "version": elegida, "diferencias": diferencias, "error": error,
        "vuelve": servicios.puede_escribir(usuario, documento) and elegida.texto != documento.texto,
        "vista": texto_a_html(elegida.texto) if documento.formato == Documento.MARKDOWN else None,
    }
    return render(request, "documentos/version.html", contexto)


# Qué se explica arriba de cada pantalla de la biblioteca.
EXPLICACIONES_DE_BIBLIOTECA = {
    "plantilla": (
        "Una plantilla es todo lo que puede llevar un documento de partida: su aspecto (página, letra, títulos, "
        "en Typst) y, si se quiere, un texto de partida (el esqueleto de un acta, por ejemplo). Cada documento "
        "elige la suya en el desplegable «Plantilla» del editor."
    ),
    "membrete": (
        "La cabecera y el pie de página (el de una organización, por ejemplo), en Typst y con imágenes. Cada "
        "documento elige el suyo en el desplegable «Cabecera y pie» del editor, aparte de la plantilla."
    ),
    "imagen": (
        "Imágenes (PNG, JPEG o GIF, de 2 MB como mucho) para los documentos, las plantillas y las cabeceras y pies. "
        "Las sube la administración, en carpetas de su organización (plantillas, grupos…)."
    ),
    "fragmento": (
        "Trozos de texto, de código o de las dos cosas, en carpetas y subcarpetas. Desde el editor se meten en el "
        "documento con un clic («📚 Fragmentos e imágenes»)."
    ),
}


# Pantallas de la biblioteca del editor: «Plantillas de documentos» (plantillas, cabeceras y pies, imágenes)
# y «Enciclopedia de fragmentos». La biblioteca vive en el editor colaborativo (cifrada); aquí solo se le da
# a la persona su pase (con sus ámbitos: toda la plataforma, sus organizaciones y sus grupos) y la isla
# «bibliotecaDelEditor» la pinta. Cualquier persona crea lo suyo y lo comparte con sus grupos o con
# personas; lo común lo cambia el superadmin y lo de cada organización, su admin.
#   - clase: «plantilla», «membrete», «imagen» o «fragmento» (viene de documentos/urls.py).
def biblioteca(request, clase):
    return render(request, "documentos/biblioteca.html", {
        "clase": clase, "en_biblioteca": editor.pase_de_biblioteca(request.user), "explicacion": EXPLICACIONES_DE_BIBLIOTECA[clase],
    })
