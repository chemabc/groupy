"""
Operaciones del módulo «lugares»: elegir el lugar propio, proponer lugares nuevos o cambios, aceptarlos o
rechazarlos (el superadmin), importar la lista desde una hoja y calcular qué ve cada persona (el mapa y
los recuentos, según la configuración de sus organizaciones).
"""

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from base.tablas import normalizar
from eventos_sw.servicios import emitir
from grupos.models import Pertenencia

from .models import ConfiguracionDeLugares, Lugar, LugarDePersona, PropuestaDeLugar

# Campos con los datos de un lugar (los mismos en la lista y en las propuestas).
CAMPOS = ["nombre", "direccion", "url_localizacion", "latitud", "longitud", "telefonos", "correos", "notas"]
# Los recuentos de personas por lugar solo se muestran a partir de este número (docs/diseno.md, 8.2).
MINIMO_PARA_CONTAR = 5


# ── El lugar de cada persona ─────────────────────────────────────────────────────────────────────────


# Elige (o cambia) el lugar de una persona. Devuelve su LugarDePersona.
@transaction.atomic
def elegir(usuario, lugar):
    if not lugar.activo:
        raise ValidationError(f"«{lugar}» ya no está en la lista.")
    eleccion, _nueva = LugarDePersona.objects.update_or_create(usuario=usuario, defaults={"lugar": lugar})
    return eleccion


# Quita el lugar de una persona (por ejemplo, si deja de trabajar allí).
@transaction.atomic
def quitar(usuario):
    LugarDePersona.objects.filter(usuario=usuario).delete()


# ── Propuestas ───────────────────────────────────────────────────────────────────────────────────────


# Propone un lugar nuevo o un cambio en uno que ya existe. Avisa al superadmin («lugares.propuesta»).
# Devuelve la propuesta.
#   - usuario: quien propone.
#   - datos: los campos del lugar (ver CAMPOS).
#   - lugar: el lugar que cambia, o None si es uno nuevo.
#   - motivo: por qué.
@transaction.atomic
def proponer(usuario, datos, lugar=None, motivo=""):
    propuesta = PropuestaDeLugar(propuesta_por=usuario, lugar=lugar, motivo=motivo, **{campo: datos.get(campo) for campo in CAMPOS if campo in datos})
    propuesta.full_clean()
    propuesta.save()
    emitir("lugares.propuesta", propuesta_id=propuesta.pk)
    _invalidar()
    return propuesta


# Acepta una propuesta: crea el lugar (y, si quien lo propuso aún no tiene lugar, pasa a ser el suyo) o
# cambia los datos del lugar. Avisa a quien la propuso. Devuelve el lugar.
#   - propuesta: la propuesta pendiente.
#   - respuesta: lo que se le contesta (opcional).
@transaction.atomic
def aceptar(propuesta, respuesta=""):
    _comprobar_pendiente(propuesta)
    datos = {campo: getattr(propuesta, campo) for campo in CAMPOS}
    if propuesta.lugar_id:
        lugar = propuesta.lugar
        for campo, valor in datos.items():
            setattr(lugar, campo, valor)
        lugar.full_clean()
        lugar.save()
    else:
        lugar = Lugar(**datos)
        lugar.full_clean()
        lugar.save()
        if not LugarDePersona.objects.filter(usuario_id=propuesta.propuesta_por_id).exists():
            LugarDePersona.objects.create(usuario_id=propuesta.propuesta_por_id, lugar=lugar)
    _cerrar(propuesta, PropuestaDeLugar.ACEPTADA, respuesta)
    return lugar


# Rechaza una propuesta, con la explicación para quien la propuso.
@transaction.atomic
def rechazar(propuesta, respuesta):
    _comprobar_pendiente(propuesta)
    _cerrar(propuesta, PropuestaDeLugar.RECHAZADA, respuesta)


# Lanza ValidationError si la propuesta ya se ha revisado.
def _comprobar_pendiente(propuesta):
    if propuesta.estado != PropuestaDeLugar.PENDIENTE:
        raise ValidationError(f"La propuesta ya está {propuesta.get_estado_display().lower()}.")


# Cierra una propuesta con su estado y su respuesta, y avisa a quien la propuso.
def _cerrar(propuesta, estado, respuesta):
    propuesta.estado, propuesta.respuesta, propuesta.revisada_el = estado, respuesta, timezone.now()
    propuesta.save(update_fields=["estado", "respuesta", "revisada_el"])
    emitir("lugares.propuesta_revisada", propuesta_id=propuesta.pk)
    _invalidar()


# Avisa a todas las personas que aún no han elegido lugar (botón del superadmin).
@transaction.atomic
def recordar_a_quien_no_tiene_lugar():
    emitir("lugares.recordatorio")


# ── Importar ─────────────────────────────────────────────────────────────────────────────────────────


# Prepara la importación de lugares a partir de las filas de una hoja: qué se crea, qué ya existe y qué
# tiene errores. No guarda nada. Devuelve una lista de diccionarios (fila, datos, «estado» y «nota»).
#   - filas: diccionarios con las columnas de la plantilla (ver lugares/views.py, COLUMNAS).
def planear_importacion(filas):
    existentes = {(normalizar(n), normalizar(d)) for n, d in Lugar.objects.values_list("nombre", "direccion")}
    vistos, plan = set(), []
    for numero, fila in enumerate(filas, start=2):
        datos = {campo: (fila.get(campo) or "").strip() for campo in CAMPOS}
        for campo in ("latitud", "longitud"):
            texto = datos[campo].replace(",", ".")
            try:
                datos[campo] = float(texto) if texto else None
            except ValueError:
                datos[campo] = "error"
        clave = (normalizar(datos["nombre"]), normalizar(datos["direccion"]))
        entrada = {"fila": numero, "datos": datos, "estado": "crear", "nota": ""}
        lugar = Lugar(**{campo: valor for campo, valor in datos.items() if valor != "error"})
        try:
            if "error" in (datos["latitud"], datos["longitud"]):
                raise ValidationError("La latitud y la longitud deben ser números (40.4168).")
            lugar.full_clean()
        except ValidationError as error:
            entrada.update(estado="error", nota=" ".join(error.messages))
        else:
            if clave in existentes or clave in vistos:
                entrada.update(estado="existe", nota="Ya hay un lugar con este nombre y esta dirección: no se toca.")
        vistos.add(clave)
        plan.append(entrada)
    return plan


# Crea los lugares de un plan (los que tienen estado «crear»). Todo o nada. Devuelve cuántos.
@transaction.atomic
def importar(plan):
    if any(entrada["estado"] == "error" for entrada in plan):
        raise ValidationError("Hay filas con errores: corrígelas y vuelve a subir la hoja.")
    nuevos = [Lugar(**entrada["datos"]) for entrada in plan if entrada["estado"] == "crear"]
    for lugar in nuevos:
        lugar.save()
    return len(nuevos)


# ── Qué ve cada persona ──────────────────────────────────────────────────────────────────────────────


# Ids de las organizaciones de una persona cuya configuración deja a sus miembros ver algo: el mapa
# (que_ver="mapa") o los recuentos («recuentos»). Sin configuración guardada, sí. 2 consultas.
#   - usuario: quién (no superadmin).
def organizaciones_que_muestran(usuario, que_ver):
    suyas = set(Pertenencia.objects.filter(usuario=usuario).values_list("grupo__organizacion_id", flat=True))
    campo = "mapa_para_miembros" if que_ver == "mapa" else "recuentos_para_miembros"
    cerradas = set(ConfiguracionDeLugares.objects.filter(organizacion_id__in=suyas, **{campo: False}).values_list("organizacion_id", flat=True))
    return suyas - cerradas


# Si una persona ve el mapa y la lista de lugares: el superadmin siempre; los demás, si alguna de sus
# organizaciones lo permite.
def ve_el_mapa(usuario):
    return usuario.is_superuser or bool(organizaciones_que_muestran(usuario, "mapa"))


# Cuántas personas hay en cada lugar, contando solo las de las organizaciones de quien mira que muestran
# recuentos (el superadmin, todas), y solo los lugares con MINIMO_PARA_CONTAR o más. Nunca quiénes.
# Devuelve {id del lugar: número}. Unas 3 consultas.
def recuentos(usuario):
    consulta = LugarDePersona.objects.all()
    if not usuario.is_superuser:
        organizaciones = organizaciones_que_muestran(usuario, "recuentos")
        if not organizaciones:
            return {}
        consulta = consulta.filter(usuario__pertenencias__grupo__organizacion_id__in=organizaciones)
    cuentas = consulta.values("lugar_id").annotate(personas=Count("usuario", distinct=True)).filter(personas__gte=MINIMO_PARA_CONTAR)
    return {fila["lugar_id"]: fila["personas"] for fila in cuentas}


# ── Número del menú ──────────────────────────────────────────────────────────────────────────────────


# «Gestión de lugares (N)»: propuestas pendientes de revisar (solo lo ve quien gestiona los lugares). Se
# guarda en la caché y se borra al proponer o revisar: casi siempre, sin consultas.
#   - usuario: quién (la entrada del menú ya exige el permiso).
def propuestas_pendientes(usuario):
    numero = cache.get("lugares:propuestas_pendientes")
    if numero is None:
        numero = PropuestaDeLugar.objects.filter(estado=PropuestaDeLugar.PENDIENTE).count()
        cache.set("lugares:propuestas_pendientes", numero, 60 * 60 * 24)
    return numero


# Borra de la caché el número de propuestas pendientes cuando termine bien la transacción en curso.
def _invalidar():
    transaction.on_commit(lambda: cache.delete("lugares:propuestas_pendientes"))
