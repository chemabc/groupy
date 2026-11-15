"""
Pantallas del módulo «documentos»: la lista, crear uno (suelto o colgado de una reunión o un proyecto), la
ficha (leer con la autoría de cada párrafo, el registro de cambios, los acuerdos, comentar, aprobar y dar
la redacción) y escribir (con vista previa al momento).
"""

import difflib

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from audiencias.selector import opciones
from base import editor
from base.anclas import buscar_ancla, leer_ancla
from base.markdown import texto_a_html
from base.tablas import Columna, Filtro, FuenteDeLista, Tabla
from grupos.acceso import grupos_donde_puede
from permisos.servicios import SinPermiso, explicar_falta, organizaciones_con

from . import servicios
from .formularios import FormularioDeDocumentoNuevo, FormularioDeLimites
from .models import Documento

# Máximo de documentos de la lista (se filtran en el navegador).
MAXIMO = 500


# Pantalla «Participación → Órdenes del día y actas»: los documentos que ve quien mira, filtrables al
# momento por tipo, grupo y estado. 2 consultas.
def lista(request):
    documentos = list(servicios.visibles(request.user).select_related("grupo")[:MAXIMO])
    filas = [
        {
            "pk": d.pk, "titulo": d.titulo, "tipo": d.get_tipo_display(), "grupo": d.grupo.nombre,
            "estado": d.get_estado_display(), "fecha": timezone.localtime(d.actualizado).strftime("%d/%m/%Y"),
        }
        for d in documentos
    ]
    tabla = Tabla(
        request,
        identificador="documentos",
        columnas=[Columna("titulo", "Título", enlace="documentos:documento"), Columna("tipo", "Tipo"), Columna("grupo", "Grupo"), Columna("estado", "Estado"), Columna("fecha", "Último cambio")],
        fuente=FuenteDeLista(filas, campos_de_busqueda=["titulo", "grupo"]),
        filtros=[
            Filtro("tipo", "Tipo", opciones=tuple((n, n) for _c, n in Documento.TIPOS)),
            Filtro("estado", "Estado", opciones=tuple((n, n) for _c, n in Documento.ESTADOS)),
        ],
    )
    plantilla = tabla.plantilla_parcial()
    if plantilla:
        return render(request, plantilla, {"tabla": tabla})
    return render(request, "documentos/lista.html", {"tabla": tabla})


# Pantalla «Nuevo documento». Con «?ancla=eventos.evento:12» cuelga de esa reunión (toma su grupo y su
# visibilidad); si no, se elige el grupo arriba y quién lo ve en el formulario.
#   - GET «ancla», «grupo», «tipo»: de qué cuelga, el grupo elegido y el tipo propuesto.
#   - POST: los campos de FormularioDeDocumentoNuevo.
def nuevo(request):
    usuario = request.user
    ancla = leer_ancla(request.GET.get("ancla", ""))
    elemento = buscar_ancla(*ancla) if ancla[0] else None
    grupos = [] if elemento else grupos_donde_puede(usuario, "documentos.crear")
    if elemento is None and not grupos:
        raise SinPermiso(explicar_falta("documentos.crear"))
    grupo = None if elemento else next((g for g in grupos if str(g.pk) == request.GET.get("grupo", "")), grupos[0])
    inicial = {"tipo": request.GET.get("tipo") or (Documento.ODD if ancla[0] == "eventos.evento" else Documento.LIBRE)}
    if elemento is not None:
        inicial["titulo"] = f"{dict(Documento.TIPOS)[inicial['tipo']]}: {elemento}"
    formulario = FormularioDeDocumentoNuevo(request.POST or None, initial=inicial, visibilidades=None if elemento else opciones(grupo))
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            documento = servicios.crear(
                usuario, datos["tipo"], datos["titulo"], grupo=grupo, visibilidad=datos.get("visibilidad", "privado"), ancla=ancla if elemento else (None, None),
                formato=datos["formato"],
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("documentos:escribir", documento.pk)
    contexto = {"formulario": formulario, "elemento": elemento, "grupos": grupos, "grupo": grupo, "ancla": request.GET.get("ancla", "")}
    return render(request, "documentos/nuevo.html", contexto)


# Busca un documento que quien mira puede ver, o da 404 (función interna de las pantallas).
def _documento(usuario, pk):
    documento = get_object_or_404(Documento.objects.select_related("grupo__organizacion", "origen"), pk=pk)
    if not servicios.ve(usuario, documento):
        raise SinPermiso("Este documento no es para ti: solo lo ven las personas a las que llega.")
    return documento


# Ficha de un documento: el texto párrafo a párrafo, cada uno con quién ha contribuido (en claro, entre
# paréntesis); arriba, el registro de cambios plegado; los acuerdos y los temas pendientes de un acta; los
# comentarios; los botones de escribir, crear el acta, aprobar y dar la redacción; sus versiones, sus comentarios en el texto y sus «Opciones». Unas 11 consultas.
#   - POST «accion»: «comentar» (con «texto»), «aprobar», «acta», «dar» (con «alias») o «quitar» (con
#     «persona»).
def documento(request, pk):
    usuario = request.user
    documento = _documento(usuario, pk)
    accion = request.POST.get("accion") if request.method == "POST" else None
    error = ""
    try:
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
    }
    return render(request, "documentos/documento.html", contexto)


# Pantalla «Escribir»: el título y el texto en Markdown a la izquierda y la vista previa a la derecha, que
# se pone al día mientras se escribe (htmx). Solo para quien tiene la redacción.
# Si hay editor en tiempo real (base/editor.py), el texto se escribe ahí entre varias personas a la vez y
# se guarda solo; quien no tiene la redacción lo sigue en directo, de solo lectura.
#   - GET «sin_directo»: usar el formulario aunque haya editor en tiempo real (si no conecta).
#   - POST «titulo», «texto» y «version» (la que tenía al abrir, para no pisar a otra persona); con el
#     editor en tiempo real, solo «titulo».
def escribir(request, pk):
    usuario = request.user
    documento = _documento(usuario, pk)
    # «?sin_directo=1»: el formulario de siempre (la salida si el editor en tiempo real no responde).
    en_vivo = None if request.GET.get("sin_directo") else editor.pase(usuario, servicios.ANCLA, documento.pk)
    if en_vivo:
        error = ""
        if request.method == "POST":
            try:
                servicios.cambiar_titulo(usuario, documento, request.POST.get("titulo", ""))
            except ValidationError as excepcion:
                error = " ".join(excepcion.messages)
            else:
                return redirect("documentos:escribir", documento.pk)
        contexto = {"documento": documento, "en_vivo": en_vivo, "error": error}
        return render(request, "documentos/escribir_en_vivo.html", contexto)
    if not servicios.puede_escribir(usuario, documento):
        raise SinPermiso("Solo quien tiene la redacción puede escribirlo (y no si ya está aprobado). Puedes comentarlo en su ficha.")
    error = ""
    titulo, texto, version = documento.titulo, documento.texto, documento.version
    if request.method == "POST":
        titulo, texto, version = request.POST.get("titulo", "").strip() or documento.titulo, request.POST.get("texto", ""), request.POST.get("version", "0")
        try:
            servicios.guardar(usuario, documento, titulo, texto, version)
        except ValidationError as excepcion:
            error = " ".join(excepcion.messages)
        else:
            return redirect("documentos:documento", documento.pk)
    contexto = {"documento": documento, "titulo": titulo, "texto": texto, "version": version, "vista": texto_a_html(texto), "error": error}
    return render(request, "documentos/escribir.html", contexto)


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
