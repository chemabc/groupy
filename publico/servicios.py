"""
Operaciones del módulo «publico» (docs/diseno.md, apartado 15): quién ve cada página, quién la gestiona,
escribir el borrador (también desde el editor en tiempo real), publicar, las imágenes, las relaciones de
publicación y consumo y las novedades. Las pantallas (publico/views.py y publico/navegacion.py) llaman a
estas funciones.

Quién ve una página publicada:
- de la plataforma o de una organización, marcada «pública»: todo el mundo, también sin sesión;
- de un grupo: quien está en ese grupo o en uno que cuelga de él (de abuelo hacia abajo), quien lo
  administra y, si el grupo publica para otros (relación aceptada), quien está en esos otros o en lo que
  cuelga de ellos;
- interna de una organización: quien está en algún grupo suyo o la administra;
- el superadmin, todo.
"""

from dataclasses import dataclass
from datetime import timedelta

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from base.markdown import texto_a_html
from eventos_sw.servicios import emitir
from grupos.acceso import grupos_donde_puede, grupos_que_administra
from grupos.models import Contencion, Grupo, Organizacion
from grupos.servicios import grupos_de
from permisos.servicios import organizaciones_con, puede

from .models import ImagenDePagina, LecturaDeNovedades, Pagina, RelacionDeConsumo

# Permiso para crear, escribir y publicar páginas (de un grupo o de una organización).
PUBLICAR = "publico.publicar"
# Tipo de ancla de las páginas (para el editor en tiempo real).
ANCLA = "publico.pagina"
# Cuánto tiempo cuentan como novedad las páginas publicadas (días).
DIAS_DE_NOVEDADES = 60
# Formatos de imagen admitidos.
IMAGENES = {"png", "jpg", "jpeg", "webp", "gif"}


# ── Quién ve qué ─────────────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Alcance:
    """Lo que una persona puede ver de las webs internas."""

    # Si lo ve todo (el superadmin).
    todo: bool
    # Grupos cuyas páginas ve: los suyos y los de encima, los que administra y los que publican para ellos.
    grupos: frozenset
    # De ellos, los que ve solo por una relación de publicación y consumo («Grupos de actividad»).
    consumidos: frozenset
    # Organizaciones cuyas páginas internas ve.
    organizaciones: frozenset


# Lo que una persona puede ver de las webs internas. Unas 4 consultas.
#   - usuario: quien mira.
def alcance_de(usuario):
    if usuario.is_superuser:
        return Alcance(True, frozenset(), frozenset(), frozenset())
    propios = grupos_de(usuario) | grupos_que_administra(usuario)
    consumidos = set(
        RelacionDeConsumo.objects.filter(estado=RelacionDeConsumo.ACEPTADA, consumidor_id__in=propios).values_list("productor_id", flat=True)
    ) - propios
    organizaciones = set(Grupo.objects.filter(pk__in=propios).values_list("organizacion_id", flat=True))
    organizaciones |= {organizacion.pk for organizacion in organizaciones_con(usuario, PUBLICAR)}
    return Alcance(False, frozenset(propios | consumidos), frozenset(consumidos), frozenset(organizaciones))


# Condición de las páginas publicadas que ve alguien con ese alcance (sin las públicas de la portada, que
# se ven aparte, salvo que se pidan).
#   - alcance: el de alcance_de().
#   - con_publicas: si se quieren también las de las portadas públicas.
def condicion_visibles(alcance, con_publicas=False):
    publicadas = Q(publicada_el__isnull=False)
    if alcance.todo:
        return publicadas if con_publicas else publicadas & Q(publica=False)
    internas = Q(grupo_id__in=alcance.grupos) | Q(grupo__isnull=True, organizacion_id__in=alcance.organizaciones, publica=False)
    return publicadas & (internas | Q(publica=True) if con_publicas else internas)


# Dice si una persona ve una página publicada (o, si la gestiona, también sin publicar).
#   - usuario: quien mira (puede no tener sesión).
#   - pagina: la página, con su grupo cargado.
#   - alcance: el de la persona, si ya se tiene (para no calcularlo dos veces).
def ve(usuario, pagina, alcance=None):
    if pagina.publica and pagina.publicada:
        return True
    if not usuario.is_authenticated:
        return False
    if gestiona(usuario, pagina):
        return True
    if not pagina.publicada:
        return False
    alcance = alcance or alcance_de(usuario)
    if alcance.todo:
        return True
    if pagina.grupo_id:
        return pagina.grupo_id in alcance.grupos
    return pagina.organizacion_id in alcance.organizaciones


# Dice si una persona gestiona una página (la escribe, la publica, sube imágenes y la borra): la de un grupo,
# quien tiene «publico.publicar» en él (su admin y los de su organización); la de una organización, sus
# admins; la de la plataforma, el superadmin.
def gestiona(usuario, pagina):
    if not usuario.is_authenticated:
        return False
    if pagina.grupo_id:
        return puede(usuario, PUBLICAR, grupo=pagina.grupo_id)
    if pagina.organizacion_id:
        return puede(usuario, PUBLICAR, organizacion=pagina.organizacion_id)
    return usuario.is_superuser


# Dónde puede crear páginas una persona: lista de (clave, nombre) con «p» (la plataforma, el superadmin),
# «o<número>» (una organización) y «g<número>» (un grupo). Unas 2 consultas.
def ambitos_de(usuario):
    ambitos = [("p", "Portada de la plataforma")] if usuario.is_superuser else []
    ambitos += [(f"o{o.pk}", f"Organización: {o.nombre}") for o in organizaciones_con(usuario, PUBLICAR)]
    ambitos += [(f"g{g.pk}", f"Grupo: {g.organizacion.nombre} › {g.camino}") for g in grupos_donde_puede(usuario, PUBLICAR)]
    return ambitos


# Las páginas que gestiona una persona, con su grupo y su organización, ordenadas por dueña. 2 o 3 consultas.
def gestionadas(usuario):
    consulta = Pagina.objects.select_related("grupo", "organizacion")
    if not usuario.is_superuser:
        grupos = [g.pk for g in grupos_donde_puede(usuario, PUBLICAR)]
        organizaciones = [o.pk for o in organizaciones_con(usuario, PUBLICAR)]
        consulta = consulta.filter(Q(grupo_id__in=grupos) | Q(grupo__isnull=True, organizacion_id__in=organizaciones))
    return list(consulta.order_by("organizacion__nombre", "grupo__nombre", "orden", "pk"))


# ── Crear, escribir y publicar ───────────────────────────────────────────────────────────────────────


# Crea una página (sin publicar). Devuelve la página.
#   - usuario: quien la crea (debe poder gestionar ahí).
#   - ambito: «p», «o<número>» o «g<número>» (ver ambitos_de).
#   - titulo, orden: su nombre y su posición.
#   - publica: si sale en la portada pública (solo la plataforma y las organizaciones).
@transaction.atomic
def crear(usuario, ambito, titulo, orden=10, publica=False):
    if ambito not in dict(ambitos_de(usuario)):
        raise ValidationError("No puedes crear páginas ahí.")
    pagina = Pagina(titulo=titulo.strip(), orden=orden, creada_por=usuario)
    if ambito.startswith("g"):
        grupo = Grupo.objects.get(pk=int(ambito[1:]))
        pagina.grupo, pagina.organizacion = grupo, grupo.organizacion
    elif ambito.startswith("o"):
        pagina.organizacion = Organizacion.objects.get(pk=int(ambito[1:]))
        pagina.publica = publica
    else:
        pagina.publica = True
    pagina.full_clean()
    pagina.save()
    return pagina


# Cambia el título, el orden y si es pública (solo la plataforma y las organizaciones).
#   - usuario: quien la gestiona.
@transaction.atomic
def cambiar(usuario, pagina, titulo, orden, publica):
    _exigir_gestion(usuario, pagina)
    pagina.titulo, pagina.orden = titulo.strip() or pagina.titulo, orden
    if pagina.organizacion_id and not pagina.grupo_id:
        pagina.publica = publica
    pagina.save(update_fields=["titulo", "orden", "publica", "actualizada"])
    _subir_version()


# Guarda el borrador (desde el formulario). Si otra persona lo ha cambiado desde que se abrió (la versión
# no coincide), no se guarda, para no pisar su trabajo.
#   - usuario: quien la gestiona.
#   - texto: el borrador nuevo.
#   - version: la que tenía al abrir.
@transaction.atomic
def guardar(usuario, pagina, texto, version):
    _exigir_gestion(usuario, pagina)
    pagina = Pagina.objects.select_for_update().get(pk=pagina.pk)
    if str(pagina.version) != str(version):
        raise ValidationError("Otra persona ha cambiado el borrador mientras escribías. Copia tu texto, recarga y vuelve a intentarlo.")
    pagina.borrador, pagina.version = texto, pagina.version + 1
    pagina.save(update_fields=["borrador", "version", "actualizada"])
    return pagina


# Publica el borrador: guarda una foto convertida en HTML seguro (base/markdown.py), que es lo que se ve.
# La primera vez avisa a quienes la pueden ver (eventos_sw «publico.publicada»). Devuelve la página.
#   - usuario: quien la gestiona.
@transaction.atomic
def publicar(usuario, pagina):
    _exigir_gestion(usuario, pagina)
    # Se relee el borrador: pudo cambiar en el editor en tiempo real desde que se cargó la página.
    pagina.borrador = Pagina.objects.select_for_update().values_list("borrador", flat=True).get(pk=pagina.pk)
    if not pagina.borrador.strip():
        raise ValidationError("El borrador está vacío: escribe algo antes de publicar.")
    primera = not pagina.publicada
    pagina.texto_publicado, pagina.html = pagina.borrador, str(texto_a_html(pagina.borrador))
    pagina.publicada_el, pagina.publicada_por = timezone.now(), usuario
    pagina.save(update_fields=["texto_publicado", "html", "publicada_el", "publicada_por", "actualizada"])
    if primera and not pagina.publica:
        emitir("publico.publicada", pagina_id=pagina.pk, autor_id=usuario.pk)
    _subir_version()
    return pagina


# Retira lo publicado (deja de verse; el borrador se queda).
@transaction.atomic
def despublicar(usuario, pagina):
    _exigir_gestion(usuario, pagina)
    pagina.html, pagina.texto_publicado, pagina.publicada_el = "", "", None
    pagina.save(update_fields=["html", "texto_publicado", "publicada_el", "actualizada"])
    _subir_version()


# Borra una página con sus imágenes (también sus ficheros).
@transaction.atomic
def borrar(usuario, pagina):
    _exigir_gestion(usuario, pagina)
    ficheros = [imagen.fichero.name for imagen in pagina.imagenes.all()]
    pagina.delete()
    transaction.on_commit(lambda: borrar_ficheros(ficheros))
    _subir_version()


# Sube una imagen a una página. Comprueba el formato y el tamaño (Django y Pillow comprueban además que
# sea de verdad una imagen). Devuelve la imagen.
#   - usuario: quien gestiona la página.
#   - subida: el archivo del formulario.
@transaction.atomic
def subir_imagen(usuario, pagina, subida):
    from django.conf import settings

    _exigir_gestion(usuario, pagina)
    extension = subida.name.rsplit(".", 1)[-1].lower() if "." in subida.name else ""
    if extension not in IMAGENES:
        raise ValidationError("Solo imágenes PNG, JPG, WebP o GIF.")
    if subida.size > settings.TAMANO_MAXIMO_DE_IMAGEN:
        raise ValidationError(f"La imagen ocupa demasiado: como mucho, {settings.TAMANO_MAXIMO_DE_IMAGEN // 1024 // 1024} MB.")
    imagen = ImagenDePagina(pagina=pagina, nombre=subida.name[:200], subida=timezone.now())
    imagen.fichero = subida
    imagen.full_clean()
    imagen.save()
    return imagen


# Borra una imagen de una página (y su fichero).
@transaction.atomic
def borrar_imagen(usuario, imagen):
    _exigir_gestion(usuario, imagen.pagina)
    nombre = imagen.fichero.name
    imagen.delete()
    transaction.on_commit(lambda: borrar_ficheros([nombre]))


# Borra ficheros guardados; si alguno ya no está, sigue.
def borrar_ficheros(nombres):
    from django.core.files.storage import default_storage

    for nombre in nombres:
        try:
            default_storage.delete(nombre)
        except OSError:
            pass


# Lanza ValidationError si la persona no gestiona la página.
def _exigir_gestion(usuario, pagina):
    if not gestiona(usuario, pagina):
        raise ValidationError("Solo la administración de su grupo u organización (o el superadmin) gestiona esta página.")


# ── Editor en tiempo real (TextoEditable «publico.pagina») ───────────────────────────────────────────


# Qué puede hacer una persona con el borrador en el editor: escribir si la gestiona; si no, nada.
def permiso_en_editor(usuario, numero):
    pagina = Pagina.objects.filter(pk=numero).select_related("grupo").first()
    return "escribir" if pagina is not None and gestiona(usuario, pagina) else ""


# El borrador con el que empieza la sala del editor y su versión.
def texto_para_editor(numero):
    pagina = Pagina.objects.get(pk=numero)
    return pagina.borrador, pagina.version


# Lo que el editor necesita además: Markdown y el título.
def opciones_para_editor(numero):
    return {"formato": "markdown", "titulo": Pagina.objects.get(pk=numero).titulo}


# Guarda lo escrito en el editor en tiempo real. Devuelve la versión nueva.
@transaction.atomic
def guardar_desde_editor(numero, texto, alias, version=None):
    pagina = Pagina.objects.select_for_update().get(pk=numero)
    if texto != pagina.borrador:
        pagina.borrador, pagina.version = texto, pagina.version + 1
        pagina.save(update_fields=["borrador", "version", "actualizada"])
    return pagina.version


# ── Publicación y consumo ────────────────────────────────────────────────────────────────────────────


# Propone que un grupo publique para otro. Lo hace quien gestiona las páginas del que publica.
#   - usuario: quien propone.
#   - productor, consumidor: los dos grupos.
#   - mensaje: por qué, para quien tiene que aceptarlo.
@transaction.atomic
def proponer_relacion(usuario, productor, consumidor, mensaje=""):
    if not puede(usuario, PUBLICAR, grupo=productor):
        raise ValidationError("Solo la administración del grupo que publica propone la relación.")
    if productor.pk == consumidor.pk:
        raise ValidationError("Un grupo no publica para sí mismo.")
    if Contencion.objects.filter(antecesor=productor, descendiente=consumidor).exists():
        raise ValidationError("Ese grupo ya cuelga del que publica: ya ve sus páginas.")
    relacion, nueva = RelacionDeConsumo.objects.get_or_create(
        productor=productor, consumidor=consumidor, defaults={"propuesta_por": usuario, "mensaje": mensaje.strip()[:300]}
    )
    if not nueva:
        raise ValidationError("Esa relación ya existe (propuesta o aceptada).")
    emitir("publico.relacion_propuesta", relacion_id=relacion.pk)
    return relacion


# Acepta una relación propuesta. Lo hace la administración del grupo que recibe.
@transaction.atomic
def aceptar_relacion(usuario, relacion):
    if not puede(usuario, PUBLICAR, grupo=relacion.consumidor_id):
        raise ValidationError("Solo la administración del grupo que recibe acepta la relación.")
    relacion.estado, relacion.aceptada_por, relacion.aceptada_el = RelacionDeConsumo.ACEPTADA, usuario, timezone.now()
    relacion.save(update_fields=["estado", "aceptada_por", "aceptada_el"])
    _subir_version()


# Corta (o rechaza) una relación. Lo hace la administración de cualquiera de los dos grupos.
@transaction.atomic
def cortar_relacion(usuario, relacion):
    if not (puede(usuario, PUBLICAR, grupo=relacion.productor_id) or puede(usuario, PUBLICAR, grupo=relacion.consumidor_id)):
        raise ValidationError("Solo la administración de uno de los dos grupos corta la relación.")
    relacion.delete()
    _subir_version()


# Las relaciones en las que participa la administración de una persona (como grupo que publica o que
# recibe), con sus grupos. 3 consultas.
def relaciones_de(usuario):
    consulta = RelacionDeConsumo.objects.select_related("productor__organizacion", "consumidor__organizacion", "propuesta_por")
    if not usuario.is_superuser:
        grupos = [g.pk for g in grupos_donde_puede(usuario, PUBLICAR)]
        consulta = consulta.filter(Q(productor_id__in=grupos) | Q(consumidor_id__in=grupos))
    return list(consulta)


# ── Novedades ────────────────────────────────────────────────────────────────────────────────────────


# Las páginas internas publicadas hace poco que ve una persona, de la más nueva a la más antigua, cada una
# con «nueva» (si se publicó después de la última vez que miró). Unas 6 consultas.
#   - usuario: quien mira.
#   - alcance: el suyo, si ya se tiene.
def novedades(usuario, alcance=None):
    alcance = alcance or alcance_de(usuario)
    desde = timezone.now() - timedelta(days=DIAS_DE_NOVEDADES)
    paginas = list(
        Pagina.objects.filter(condicion_visibles(alcance), publicada_el__gte=desde).select_related("grupo", "organizacion").order_by("-publicada_el")[:100]
    )
    vistas_hasta = LecturaDeNovedades.objects.filter(usuario=usuario).values_list("vistas_hasta", flat=True).first()
    for pagina in paginas:
        pagina.nueva = vistas_hasta is None or pagina.publicada_el > vistas_hasta
    return paginas


# Apunta que una persona ha mirado las novedades (lo publicado antes deja de contar como nuevo).
def marcar_novedades_vistas(usuario):
    LecturaDeNovedades.objects.update_or_create(usuario=usuario, defaults={"vistas_hasta": timezone.now()})
    cache.delete(_clave(usuario.pk))


# Número de novedades sin mirar, para el botón «🌐 Webs» de la cabecera. Se guarda en la caché (diez
# minutos, o hasta que se publica algo); sin consultas si está.
def novedades_sin_ver(usuario):
    clave = _clave(usuario.pk)
    numero = cache.get(clave)
    if numero is None:
        numero = sum(1 for pagina in novedades(usuario) if pagina.nueva)
        cache.set(clave, numero, 600)
    return numero


# Clave de la caché con el número de novedades de una persona (con la versión de las webs).
def _clave(usuario_id):
    cache.add("publico:version", 1, None)
    return f"publico:novedades:v{cache.get('publico:version', 1)}:{usuario_id}"


# Sube la versión de las webs cuando termine bien la transacción: los números de novedades dejan de valer.
def _subir_version():
    # Función interna: sube el número (o lo crea si la caché estaba vacía).
    def subir():
        try:
            cache.incr("publico:version")
        except ValueError:
            cache.set("publico:version", 2, None)

    transaction.on_commit(subir)
