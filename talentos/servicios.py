"""
Operaciones del módulo «talentos»: el catálogo común, los talentos de cada persona y con qué grupos los
comparte, los recuentos de cada grupo (nunca quiénes), las peticiones de talentos y los ofrecimientos.

Privacidad: quién tiene un talento no lo ve nadie más que esa persona. Al ofrecerlo para una petición, su
alias lo ven quien hizo la petición y la administración del grupo (sus admins, los de su organización y
el superadmin).
"""

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q

from base.tablas import forma_de_frase, normalizar
from eventos_sw.servicios import emitir
from grupos.models import AdminDeOrganizacion, Contencion, Pertenencia
from grupos.servicios import grupos_de
from permisos.servicios import exigir

from .models import Compartido, Necesidad, Ofrecimiento, PeticionDeTalentos, Talento, TalentoDePersona

# ── Catálogo ─────────────────────────────────────────────────────────────────────────────────────────


# Busca un talento del catálogo por su nombre o por una de sus palabras relacionadas (sin tildes ni
# mayúsculas), o None.
def buscar(nombre):
    buscado = normalizar(" ".join(nombre.split()))
    if not buscado:
        return None
    exacto = Talento.objects.filter(normalizada=buscado).first()
    if exacto:
        return exacto
    for talento in Talento.objects.filter(relacionadas__icontains=nombre.strip()[:3]):
        if buscado in {normalizar(p) for p in talento.relacionadas.split(",")}:
            return talento
    return None


# Devuelve el talento del catálogo con ese nombre (o relacionada), creándolo si no existe.
#   - nombre: lo escrito.
#   - tipo: Talento.RECURSO o Talento.HABILIDAD (solo si se crea).
#   - usuario: quién lo crea.
@transaction.atomic
def obtener_o_crear(nombre, tipo, usuario=None):
    nombre = " ".join(nombre.split())
    if not nombre or len(nombre) > 60:
        raise ValidationError("Escribe el talento en pocas palabras (60 caracteres como mucho).")
    talento = buscar(nombre)
    if talento is None:
        talento = Talento(nombre=nombre, tipo=tipo, creado_por=usuario)
        talento.save()
    return talento


# Fusiona talentos repetidos en uno: lo de los otros pasa al que se queda (sin duplicar) y sus nombres
# pasan a ser palabras relacionadas. Solo el superadmin (lo comprueba la vista).
#   - destino: el que se queda.
#   - otros: los que desaparecen.
@transaction.atomic
def fusionar(destino, otros):
    otros = [talento for talento in otros if talento.pk != destino.pk]
    for talento in otros:
        for suyo in TalentoDePersona.objects.filter(talento=talento):
            ya, _nuevo = TalentoDePersona.objects.get_or_create(usuario_id=suyo.usuario_id, talento=destino, defaults={"detalle": suyo.detalle})
            for compartido in suyo.compartidos.all():
                Compartido.objects.get_or_create(talento_de_persona=ya, grupo_id=compartido.grupo_id)
        Necesidad.objects.filter(talento=talento).update(talento=destino)
    palabras = [destino.relacionadas] if destino.relacionadas else []
    palabras += [talento.nombre for talento in otros] + [talento.relacionadas for talento in otros if talento.relacionadas]
    Talento.objects.filter(pk__in=[talento.pk for talento in otros]).delete()
    destino.relacionadas = ", ".join(dict.fromkeys(forma_de_frase(p.strip()) for p in ", ".join(palabras).split(",") if p.strip()))
    destino.save()
    return destino


# ── Mis talentos ─────────────────────────────────────────────────────────────────────────────────────


# Añade un talento a una persona (del catálogo o nuevo). Devuelve su TalentoDePersona.
@transaction.atomic
def anadir(usuario, nombre, tipo, detalle=""):
    talento = obtener_o_crear(nombre, tipo, usuario)
    suyo, _nuevo = TalentoDePersona.objects.update_or_create(usuario=usuario, talento=talento, defaults={"detalle": detalle})
    _invalidar()
    return suyo


# Deja un talento de una persona compartido exactamente con estos grupos (de los suyos).
#   - suyo: el TalentoDePersona.
#   - grupos: ids de los grupos.
@transaction.atomic
def compartir(suyo, grupos):
    mios = grupos_de(suyo.usuario)
    ajenos = set(grupos) - mios
    if ajenos:
        raise ValidationError("Solo puedes compartir tus talentos con grupos de los que eres miembro.")
    suyo.compartidos.exclude(grupo_id__in=grupos).delete()
    ya = set(suyo.compartidos.values_list("grupo_id", flat=True))
    Compartido.objects.bulk_create(Compartido(talento_de_persona=suyo, grupo_id=grupo) for grupo in set(grupos) - ya)
    _invalidar()


# Quita un talento a una persona (y deja de compartirlo).
@transaction.atomic
def quitar(usuario, pk):
    TalentoDePersona.objects.filter(usuario=usuario, pk=pk).delete()
    _invalidar()


# ── Recuentos ────────────────────────────────────────────────────────────────────────────────────────


# Cuántas personas comparten cada talento con un grupo o con alguno de sus subgrupos. Nunca quiénes.
# Devuelve una lista de (talento, número), de más a menos. Una consulta.
#   - grupo: el grupo.
def recuento_del_grupo(grupo):
    subarbol = Contencion.objects.filter(antecesor=grupo).values("descendiente_id")
    filas = (
        Compartido.objects.filter(grupo_id__in=subarbol)
        .values("talento_de_persona__talento")
        .annotate(personas=Count("talento_de_persona__usuario", distinct=True))
        .order_by("-personas")
    )
    talentos = Talento.objects.in_bulk([fila["talento_de_persona__talento"] for fila in filas])
    return [(talentos[fila["talento_de_persona__talento"]], fila["personas"]) for fila in filas]


# Ids de las personas que comparten un talento con un grupo o con alguno de sus subgrupos. Para avisar
# de una petición (nunca se muestra).
def quienes_comparten(talento_id, grupo):
    subarbol = Contencion.objects.filter(antecesor=grupo).values("descendiente_id")
    return set(
        Compartido.objects.filter(grupo_id__in=subarbol, talento_de_persona__talento_id=talento_id).values_list("talento_de_persona__usuario_id", flat=True)
    )


# ── Peticiones ───────────────────────────────────────────────────────────────────────────────────────


# Pide talentos a un grupo. Hace falta «talentos.pedir» en el grupo (de entrada, sus admins y los de la
# organización). Avisa a quienes los comparten. Devuelve la petición.
#   - autor: quien pide.
#   - grupo: el grupo.
#   - asunto, descripcion: para qué.
#   - necesidades: lista de (Talento, cantidad).
#   - ancla_tipo, ancla_id: si es para algo concreto (un proyecto), su tipo de ancla y su número.
@transaction.atomic
def pedir(autor, grupo, asunto, descripcion, necesidades, ancla_tipo="", ancla_id=None):
    exigir(autor, "talentos.pedir", grupo=grupo)
    if not necesidades:
        raise ValidationError("Indica al menos un talento que haga falta.")
    peticion = PeticionDeTalentos.objects.create(
        grupo=grupo, autor=autor, asunto=asunto, descripcion=descripcion, ancla_tipo=ancla_tipo, ancla_id=ancla_id
    )
    Necesidad.objects.bulk_create(Necesidad(peticion=peticion, talento=talento, cantidad=cantidad) for talento, cantidad in necesidades)
    emitir("talentos.peticion", peticion_id=peticion.pk)
    _invalidar()
    return peticion


# Dice si una persona ve una petición: es miembro del grupo (también desde un subgrupo), la hizo, o
# atiende su administración.
def ve_la_peticion(usuario, peticion, mios=None):
    mios = grupos_de(usuario) if mios is None else mios
    return peticion.grupo_id in mios or ve_quien_se_ofrece(usuario, peticion)


# Dice si una persona ve quién se ofrece en una petición: quien la hizo, los admins del grupo y de su
# organización, y el superadmin.
def ve_quien_se_ofrece(usuario, peticion):
    if usuario.is_superuser or peticion.autor_id == usuario.pk:
        return True
    if Pertenencia.objects.filter(usuario=usuario, grupo_id=peticion.grupo_id, rol=Pertenencia.ADMIN_GRUPO).exists():
        return True
    return AdminDeOrganizacion.objects.filter(usuario=usuario, organizacion_id=peticion.grupo.organizacion_id).exists()


# Ofrece un talento para una petición abierta. Hace falta ser miembro del grupo y tener ese talento.
# Avisa a la administración. Devuelve el ofrecimiento.
@transaction.atomic
def ofrecer(usuario, necesidad, mensaje=""):
    peticion = necesidad.peticion
    if peticion.estado != PeticionDeTalentos.ABIERTA:
        raise ValidationError("La petición ya está cerrada.")
    if peticion.grupo_id not in grupos_de(usuario):
        raise ValidationError(f"Solo pueden ofrecerse los miembros de {peticion.grupo}.")
    if not TalentoDePersona.objects.filter(usuario=usuario, talento_id=necesidad.talento_id).exists():
        raise ValidationError(f"Para ofrecer «{necesidad.talento}», añádelo antes a tus talentos.")
    ofrecimiento, nuevo = Ofrecimiento.objects.get_or_create(necesidad=necesidad, usuario=usuario, defaults={"mensaje": mensaje})
    if nuevo:
        emitir("talentos.ofrecimiento", ofrecimiento_id=ofrecimiento.pk)
    _invalidar()
    return ofrecimiento


# Retira el ofrecimiento de una persona para un talento de una petición.
@transaction.atomic
def retirar(usuario, necesidad):
    Ofrecimiento.objects.filter(necesidad=necesidad, usuario=usuario).delete()
    _invalidar()


# Cierra (o vuelve a abrir) una petición. Quien la hizo o quien atiende su administración.
@transaction.atomic
def cambiar_estado(usuario, peticion, estado):
    if not ve_quien_se_ofrece(usuario, peticion):
        raise ValidationError("Solo quien hizo la petición o su administración pueden cerrarla.")
    peticion.estado = estado
    peticion.save(update_fields=["estado"])
    _invalidar()


# ── Número del menú ──────────────────────────────────────────────────────────────────────────────────


# «Peticiones (N)»: peticiones abiertas de sus grupos que piden un talento que la persona comparte (con
# ese grupo o un subgrupo) y a las que aún no se ha ofrecido. Sin consultas si está en la caché.
def peticiones_para(usuario):
    clave = f"talentos:peticiones:v{_version()}:{usuario.pk}"
    numero = cache.get(clave)
    if numero is None:
        compartidos = Compartido.objects.filter(talento_de_persona__usuario=usuario)
        # Pares (grupo con el que comparte, talento), para saber a qué peticiones llega.
        pares = set(compartidos.values_list("grupo_id", "talento_de_persona__talento_id"))
        if not pares:
            numero = 0
        else:
            antecesores = {}
            for antecesor, descendiente in Contencion.objects.filter(descendiente_id__in={g for g, _t in pares}).values_list("antecesor_id", "descendiente_id"):
                antecesores.setdefault(descendiente, set()).add(antecesor)
            llega = Q(pk__in=[])
            for grupo, talento in pares:
                llega |= Q(peticion__grupo_id__in=antecesores.get(grupo, {grupo}), talento_id=talento)
            ya = Ofrecimiento.objects.filter(usuario=usuario).values("necesidad__peticion_id")
            numero = (
                Necesidad.objects.filter(llega, peticion__estado=PeticionDeTalentos.ABIERTA)
                .exclude(peticion_id__in=ya)
                .values("peticion_id").distinct().count()
            )
        cache.set(clave, numero, 60 * 60 * 24)
    return numero


# Versión de los números del menú (sube con cualquier cambio).
def _version():
    cache.add("talentos:version", 1, None)
    return cache.get("talentos:version", 1)


# Sube la versión cuando termine bien la transacción en curso.
def _invalidar():
    # Función interna: sube el número (o lo crea si la caché estaba vacía).
    def subir():
        try:
            cache.incr("talentos:version")
        except ValueError:
            cache.set("talentos:version", 2, None)

    transaction.on_commit(subir)
