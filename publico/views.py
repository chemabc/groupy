"""
Pantallas del módulo «publico» (docs/diseno.md, apartado 15):

- Portada pública (sin sesión): la de la plataforma (/portada/) y la de cada organización (/o/<número>/),
  con sus pestañas arriba y «Entrar» a la derecha.
- «🌐 Webs» (con sesión, sin el menú de la izquierda): la web de cada grupo u organización que se puede
  ver, con la barra de camino, las pestañas, «Novedades», «Buscar» y «Jerarquía» (publico/navegacion.py).
- Gestionar (en «Administrar»): las páginas que administra cada cual (crear, escribir, publicar, imágenes)
  y las relaciones de publicación y consumo.
"""

from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from base import editor
from base.markdown import texto_a_html
from grupos.acceso import grupos_donde_puede
from grupos.models import Organizacion
from permisos.servicios import SinPermiso, explicar_falta

from . import navegacion, servicios
from .formularios import FormularioDeImagen, FormularioDePagina, FormularioDeRelacion
from .models import ImagenDePagina, Pagina, RelacionDeConsumo

# ── Portada pública (sin sesión) ─────────────────────────────────────────────────────────────────────


# Portada pública de la plataforma: sus páginas públicas como pestañas (la elegida, o la primera) y la lista
# de organizaciones con portada. Se ve sin sesión. 3 consultas.
#   - pk: la página elegida (o None: la primera).
@login_not_required
def portada(request, pk=None):
    paginas = list(Pagina.objects.filter(publica=True, publicada_el__isnull=False, organizacion__isnull=True, grupo__isnull=True))
    organizaciones = Organizacion.objects.filter(
        pk__in=Pagina.objects.filter(publica=True, publicada_el__isnull=False, grupo__isnull=True).values("organizacion_id")
    ).order_by("nombre")
    return _portada(request, "Asambleas", paginas, pk, list(organizaciones), base=reverse("publico:portada"), ruta="publico:portada_pagina")


# Portada pública de una organización: sus páginas públicas como pestañas. Se ve sin sesión. 3 consultas.
#   - organizacion: su número.
#   - pk: la página elegida (o None: la primera).
@login_not_required
def portada_de_organizacion(request, organizacion, pk=None):
    organizacion = get_object_or_404(Organizacion, pk=organizacion)
    paginas = list(Pagina.objects.filter(publica=True, publicada_el__isnull=False, organizacion=organizacion, grupo__isnull=True))
    if not paginas:
        raise Http404("Esta organización no tiene portada pública.")
    return _portada(
        request, organizacion.nombre, paginas, pk, [], base=reverse("publico:portada_de_organizacion", args=[organizacion.pk]),
        ruta="publico:portada_de_organizacion_pagina", args=[organizacion.pk],
    )


# Lo común a las dos portadas: las pestañas, la elegida y la plantilla pública (sin menús ni sesión).
def _portada(request, nombre, paginas, pk, organizaciones, base, ruta, args=()):
    elegida = next((p for p in paginas if p.pk == pk), None) if pk else (paginas[0] if paginas else None)
    if pk and elegida is None:
        raise Http404("Esa página no existe o no es pública.")
    pestanas = [{"titulo": p.titulo, "url": reverse(ruta, args=[*args, p.pk]) if p is not paginas[0] else base, "activa": p is elegida} for p in paginas]
    contexto = {"nombre": nombre, "pestanas": pestanas, "pagina": elegida, "organizaciones": organizaciones, "volver": reverse("publico:portada")}
    return render(request, "publico/portada.html", contexto)


# Entrega una imagen de una página: a cualquiera si la página es pública y está publicada; si no, a quien
# puede ver la página. 1 o 2 consultas (más las de ver).
#   - pk: la imagen.
@login_not_required
def imagen(request, pk):
    elegida = get_object_or_404(ImagenDePagina.objects.select_related("pagina__grupo"), pk=pk)
    if not servicios.ve(request.user, elegida.pagina):
        raise Http404("Imagen no encontrada.")
    respuesta = FileResponse(elegida.fichero.open("rb"))
    respuesta["X-Content-Type-Options"] = "nosniff"
    return respuesta


# ── «🌐 Webs» (con sesión) ───────────────────────────────────────────────────────────────────────────


# Entrada a «🌐 Webs»: lleva a la web de la asamblea base (o a la primera que se pueda ver). Si no hay
# ninguna, lo dice.
def webs(request):
    mapa = navegacion.mapa_de(servicios.alcance_de(request.user))
    destino = navegacion.inicio_de(request.user, mapa)
    if destino:
        return redirect(destino)
    return _visor(request, mapa, titulo="Webs", vacia=True)


# La web de un grupo: sus páginas como pestañas (la primera abierta). Si no tiene páginas pero cuelgan de
# él grupos con web, enseña sus subgrupos. Unas 8 consultas.
#   - pk: el grupo.
def grupo(request, pk):
    mapa = navegacion.mapa_de(servicios.alcance_de(request.user))
    elegido = mapa.grupos.get(pk)
    if elegido is None:
        raise Http404("Ese grupo no tiene web, o no la puedes ver.")
    paginas = navegacion.pestanas(mapa, grupo_id=pk)
    pagina = Pagina.objects.get(pk=paginas[0][0]) if paginas else None
    return _visor(request, mapa, titulo=elegido.nombre, grupo=elegido, pagina=pagina)


# Las páginas internas de una organización (de toda ella). Unas 8 consultas.
#   - pk: la organización.
def organizacion(request, pk):
    mapa = navegacion.mapa_de(servicios.alcance_de(request.user))
    elegida = mapa.organizaciones.get(pk)
    if elegida is None:
        raise Http404("Esa organización no tiene web, o no la puedes ver.")
    paginas = navegacion.pestanas(mapa, organizacion_id=pk)
    pagina = Pagina.objects.get(pk=paginas[0][0]) if paginas else None
    return _visor(request, mapa, titulo=elegida.nombre, organizacion_id=pk, pagina=pagina)


# Una página de una web, con la navegación de su dueña. Quien la gestiona puede verla aunque no esté
# publicada (ve el borrador convertido, con un aviso). Unas 8 consultas.
#   - pk: la página.
def pagina(request, pk):
    elegida = get_object_or_404(Pagina.objects.select_related("grupo", "organizacion"), pk=pk)
    alcance = servicios.alcance_de(request.user)
    if not servicios.ve(request.user, elegida, alcance):
        raise Http404("Esa página no existe o no la puedes ver.")
    if elegida.publica and not elegida.grupo_id:
        return redirect(reverse("publico:portada_pagina", args=[pk]) if not elegida.organizacion_id else reverse("publico:portada_de_organizacion_pagina", args=[elegida.organizacion_id, pk]))
    mapa = navegacion.mapa_de(alcance)
    grupo = mapa.grupos.get(elegida.grupo_id) if elegida.grupo_id else None
    return _visor(request, mapa, titulo=elegida.titulo, grupo=grupo or elegida.grupo, organizacion_id=elegida.organizacion_id, pagina=elegida)


# «Novedades»: lo publicado en los últimos días en las webs que se pueden ver; lo nuevo, marcado. Al verlas,
# dejan de contar como nuevas (el número del botón «🌐 Webs» vuelve a cero).
def novedades(request):
    alcance = servicios.alcance_de(request.user)
    lista = servicios.novedades(request.user, alcance)
    servicios.marcar_novedades_vistas(request.user)
    return _visor(request, navegacion.mapa_de(alcance), titulo="Novedades", seccion="novedades", lista=lista)


# «Buscar»: las páginas que se pueden ver (también las públicas) con esas palabras en el título o el texto.
#   - GET «q»: lo buscado.
def buscar(request):
    alcance = servicios.alcance_de(request.user)
    texto = request.GET.get("q", "").strip()[:100]
    lista = []
    if texto:
        consulta = Pagina.objects.filter(servicios.condicion_visibles(alcance, con_publicas=True)).select_related("grupo", "organizacion")
        for palabra in texto.split():
            consulta = consulta.filter(Q(titulo__unaccent__icontains=palabra) | Q(texto_publicado__unaccent__icontains=palabra))
        lista = list(consulta.order_by("-publicada_el")[:100])
    return _visor(request, navegacion.mapa_de(alcance), titulo="Buscar", seccion="buscar", lista=lista, busqueda=texto)


# «Jerarquía»: el mapa de las webs que se pueden ver, como un grafo (cada organización en su caja; los
# grupos de actividad aparte, con flechas de puntos hacia quienes reciben sus páginas).
def jerarquia(request):
    mapa = navegacion.mapa_de(servicios.alcance_de(request.user))
    texto, enlaces = navegacion.grafo(mapa)
    return _visor(request, mapa, titulo="Jerarquía", seccion="jerarquia", grafo=texto, enlaces=enlaces)


# Pinta el visor de webs (publico/webs.html): barra de camino, pestañas y contenido. Función interna.
#   - mapa: el de navegacion.mapa_de().
#   - titulo: el de la pestaña del navegador.
#   - grupo / organizacion_id: la dueña que se mira, si hay.
#   - pagina: la página abierta, si hay.
#   - seccion: «novedades», «buscar» o «jerarquia», si se mira una de ellas.
#   - otros: lo propio de cada sección (lista, busqueda, grafo, enlaces, vacia).
def _visor(request, mapa, titulo, grupo=None, organizacion_id=None, pagina=None, seccion="", **otros):
    tramos, hijos = navegacion.camino(mapa, grupo=grupo, organizacion_id=organizacion_id) if (grupo or organizacion_id) else ([], [])
    if grupo is not None:
        pestanas = navegacion.pestanas(mapa, grupo_id=grupo.pk)
    elif organizacion_id:
        pestanas = navegacion.pestanas(mapa, organizacion_id=organizacion_id)
    else:
        pestanas = []
    gestiona = pagina is not None and servicios.gestiona(request.user, pagina)
    contexto = {
        "titulo": titulo,
        "tramos": tramos,
        "hijos": hijos,
        "actividad": navegacion.grupos_de_actividad(mapa),
        "pestanas": [{"titulo": t, "url": reverse("publico:pagina", args=[pk]), "activa": pagina is not None and pk == pagina.pk} for pk, t in pestanas],
        "pagina": pagina,
        # Quien la gestiona y aún no está publicada ve su borrador convertido.
        "borrador": texto_a_html(pagina.borrador) if pagina is not None and not pagina.publicada and gestiona else None,
        "gestiona": gestiona,
        "seccion": seccion,
        "novedades": servicios.novedades_sin_ver(request.user) if seccion != "novedades" else 0,
        **otros,
    }
    return render(request, "publico/webs.html", contexto)


# ── Gestionar (Administrar) ──────────────────────────────────────────────────────────────────────────


# Pantalla «Administrar → Webs → Páginas»: las páginas que gestiona quien mira, por dueña, con su estado
# (publicada, borrador, pública) y el formulario para crear otra. Unas 6 consultas.
#   - POST: los campos de FormularioDePagina (crear).
def paginas(request):
    usuario = request.user
    ambitos = servicios.ambitos_de(usuario)
    if not ambitos:
        raise SinPermiso(explicar_falta(servicios.PUBLICAR))
    formulario = FormularioDePagina(request.POST or None, ambitos=ambitos)
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            nueva = servicios.crear(usuario, datos["ambito"], datos["titulo"], datos["orden"], datos["publica"])
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            return redirect("publico:editar", nueva.pk)
    return render(request, "publico/paginas.html", {"paginas": servicios.gestionadas(usuario), "formulario": formulario})


# Busca una página que gestiona quien mira, o da 403 (función interna).
def _gestionada(usuario, pk):
    elegida = get_object_or_404(Pagina.objects.select_related("grupo", "organizacion"), pk=pk)
    if not servicios.gestiona(usuario, elegida):
        raise SinPermiso("Esta página la gestionan la administración de su grupo u organización y el superadmin.")
    return elegida


# Pantalla de una página para quien la gestiona: el borrador (vista previa), lo publicado, publicar o
# retirar, el título, el orden y si es pública, las imágenes (con lo que hay que escribir para ponerlas) y
# borrar. Unas 8 consultas.
#   - POST «accion»: «datos» (FormularioDePagina sin ámbito), «publicar», «despublicar», «imagen» (con el
#     fichero), «quitar_imagen» (con «imagen») o «borrar».
def editar(request, pk):
    usuario = request.user
    elegida = _gestionada(usuario, pk)
    accion = request.POST.get("accion") if request.method == "POST" else None
    datos = FormularioDePagina(
        request.POST if accion == "datos" else None, ambitos=None, publica_posible=bool(elegida.organizacion_id and not elegida.grupo_id),
        initial={"titulo": elegida.titulo, "orden": elegida.orden, "publica": elegida.publica},
    )
    subida = FormularioDeImagen(request.POST if accion == "imagen" else None, request.FILES if accion == "imagen" else None)
    error = ""
    try:
        if accion == "datos" and datos.is_valid():
            servicios.cambiar(usuario, elegida, datos.cleaned_data["titulo"], datos.cleaned_data["orden"], datos.cleaned_data.get("publica", False))
            return redirect("publico:editar", elegida.pk)
        if accion == "publicar":
            servicios.publicar(usuario, elegida)
            return redirect("publico:editar", elegida.pk)
        if accion == "despublicar":
            servicios.despublicar(usuario, elegida)
            return redirect("publico:editar", elegida.pk)
        if accion == "imagen" and subida.is_valid():
            servicios.subir_imagen(usuario, elegida, subida.cleaned_data["imagen"])
            return redirect("publico:editar", elegida.pk)
        if accion == "quitar_imagen":
            servicios.borrar_imagen(usuario, get_object_or_404(elegida.imagenes, pk=request.POST.get("imagen", "0") if request.POST.get("imagen", "").isdigit() else 0))
            return redirect("publico:editar", elegida.pk)
        if accion == "borrar":
            servicios.borrar(usuario, elegida)
            return redirect("publico:paginas")
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
    contexto = {
        "pagina": elegida,
        "vista": texto_a_html(elegida.borrador),
        "cambiado": elegida.publicada and elegida.borrador != elegida.texto_publicado,
        "datos": datos,
        "subida": subida,
        "imagenes": [{"imagen": i, "url": reverse("publico:imagen", args=[i.pk])} for i in elegida.imagenes.all()],
        "en_vivo": editor.activo(),
        "error": error,
    }
    return render(request, "publico/editar.html", contexto)


# Pantalla «Escribir» el borrador de una página: con el editor en tiempo real si lo hay (se guarda solo);
# si no, el formulario con la vista previa al momento.
#   - GET «sin_directo»: usar el formulario aunque haya editor.
#   - POST «texto» y «version» (formulario).
def escribir(request, pk):
    usuario = request.user
    elegida = _gestionada(usuario, pk)
    en_vivo = None if request.GET.get("sin_directo") else editor.pase(usuario, servicios.ANCLA, elegida.pk)
    if en_vivo:
        return render(request, "publico/escribir_en_vivo.html", {"pagina": elegida, "en_vivo": en_vivo})
    error, texto, version = "", elegida.borrador, elegida.version
    if request.method == "POST":
        texto, version = request.POST.get("texto", ""), request.POST.get("version", "0")
        try:
            servicios.guardar(usuario, elegida, texto, version)
        except ValidationError as excepcion:
            error = " ".join(excepcion.messages)
        else:
            return redirect("publico:editar", elegida.pk)
    contexto = {"pagina": elegida, "texto": texto, "version": version, "vista": texto_a_html(texto), "error": error}
    return render(request, "publico/escribir.html", contexto)


# Vista previa del borrador mientras se escribe (la pide htmx). Sin consultas.
#   - POST «texto»: lo escrito.
def vista_previa(request):
    if request.method != "POST" or len(request.POST.get("texto", "")) > 200_000:
        raise Http404("Nada que previsualizar.")
    return render(request, "publico/_vista_previa.html", {"vista": texto_a_html(request.POST.get("texto", ""))})


# Pantalla «Administrar → Webs → Publicación y consumo»: las relaciones de los grupos que administra quien
# mira (propuestas por responder, aceptadas, enviadas) y el formulario para proponer una.
#   - POST «accion»: «proponer» (FormularioDeRelacion), «aceptar» o «cortar» (con «relacion»).
def relaciones(request):
    usuario = request.user
    grupos = grupos_donde_puede(usuario, servicios.PUBLICAR)
    if not grupos and not usuario.is_superuser:
        raise SinPermiso(explicar_falta(servicios.PUBLICAR))
    accion = request.POST.get("accion") if request.method == "POST" else None
    formulario = FormularioDeRelacion(request.POST if accion == "proponer" else None, productores=grupos)
    error = ""
    try:
        if accion == "proponer" and formulario.is_valid():
            datos = formulario.cleaned_data
            servicios.proponer_relacion(usuario, datos["productor"], datos["consumidor"], datos["mensaje"])
            return redirect("publico:relaciones")
        if accion in ("aceptar", "cortar"):
            numero = request.POST.get("relacion", "")
            relacion = get_object_or_404(RelacionDeConsumo, pk=int(numero) if numero.isdigit() else 0)
            (servicios.aceptar_relacion if accion == "aceptar" else servicios.cortar_relacion)(usuario, relacion)
            return redirect("publico:relaciones")
    except ValidationError as excepcion:
        error = " ".join(excepcion.messages)
    mios = {g.pk for g in grupos}
    filas = []
    for relacion in servicios.relaciones_de(usuario):
        filas.append({
            "relacion": relacion,
            "acepta": relacion.estado == RelacionDeConsumo.PROPUESTA and (usuario.is_superuser or relacion.consumidor_id in mios),
        })
    return render(request, "publico/relaciones.html", {"filas": filas, "formulario": formulario, "error": error})
