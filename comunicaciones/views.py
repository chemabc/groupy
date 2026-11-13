"""
Pantallas de la sección «Comunicaciones» (ver docs/diseno.md, apartado 17):

- Notificaciones: la bandeja de cada persona, con filtro por origen. Cada notificación se abre (y queda
  vista), se marca como vista o se borra con su papelera; arriba, «Marcar todas como vistas» y «Limpiar
  las vistas».
- Preferencias: qué tipos de aviso quiere recibir cada persona.

Cada persona solo ve y toca las suyas: todas las consultas filtran por request.user.
"""

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from base.contrato import ORIGENES_DE_AVISO
from base.registro import registro

from . import servicios
from .models import Notificacion

# Cuántas notificaciones se muestran de entrada; «Mostrar más» suma otras tantas.
POR_PAGINA = 50


# Pantalla «Notificaciones». Cuesta 4 consultas, sea cual sea el número de notificaciones.
#   - GET «origen»: muestra solo las de ese origen. «cuantas»: cuántas se muestran.
#   - POST «accion»: vista (con «notificacion»), borrar (con «notificacion»), todas_vistas o limpiar.
def notificaciones(request):
    usuario = request.user
    origen = request.GET.get("origen", "")
    origen = origen if origen in dict(ORIGENES_DE_AVISO) else ""
    accion = request.POST.get("accion") if request.method == "POST" else None
    if accion:
        if accion == "vista":
            servicios.marcar_vistas(usuario, [request.POST.get("notificacion")])
        elif accion == "borrar":
            servicios.borrar(usuario, request.POST.get("notificacion"))
        elif accion == "todas_vistas":
            servicios.marcar_vistas(usuario)
        elif accion == "limpiar":
            servicios.limpiar_vistas(usuario)
        return redirect(f"{reverse('comunicaciones:notificaciones')}?origen={origen}" if origen else "comunicaciones:notificaciones")
    cuantas = request.GET.get("cuantas", "")
    cuantas = max(POR_PAGINA, min(int(cuantas), 1000)) if cuantas.isdigit() else POR_PAGINA
    # Recuento por origen (todas y sin ver), en una sola consulta, para las pestañas de las bandejas.
    recuentos = {
        fila["origen"]: fila
        for fila in Notificacion.objects.filter(usuario=usuario)
        .values("origen")
        .annotate(total=Count("pk"), sin_ver=Count("pk", filter=Q(vista_el__isnull=True)))
        .order_by()
    }
    bandejas = [
        {"codigo": codigo, "nombre": nombre, "total": recuentos[codigo]["total"], "sin_ver": recuentos[codigo]["sin_ver"]}
        for codigo, nombre in ORIGENES_DE_AVISO
        if codigo in recuentos
    ]
    lista = Notificacion.objects.filter(usuario=usuario)
    if origen:
        lista = lista.filter(origen=origen)
    filas = list(lista[: cuantas + 1])
    contexto = {
        "bandejas": bandejas,
        "origen": origen,
        "total": sum(bandeja["total"] for bandeja in bandejas),
        "sin_ver_total": sum(bandeja["sin_ver"] for bandeja in bandejas),
        "hay_vistas": any(bandeja["total"] > bandeja["sin_ver"] for bandeja in bandejas),
        "notificaciones": filas[:cuantas],
        "mas": cuantas + POR_PAGINA if len(filas) > cuantas else None,
    }
    return render(request, "comunicaciones/notificaciones.html", contexto)


# Abre una notificación: la marca como vista y lleva a su enlace (o a la bandeja, si no tiene). Solo
# lleva a direcciones de la propia aplicación.
#   - pk: número de la notificación (de quien la abre).
def abrir(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk, usuario=request.user)
    servicios.marcar_vistas(request.user, [notificacion.pk])
    seguro = url_has_allowed_host_and_scheme(notificacion.enlace, allowed_hosts={request.get_host()})
    return redirect(notificacion.enlace if notificacion.enlace and seguro else "comunicaciones:notificaciones")


# Pantalla «Preferencias»: los tipos de aviso de todos los módulos, agrupados por origen, con una casilla
# para recibirlos o no. Cuesta 3 consultas.
#   - POST: la lista «activados» con los códigos marcados.
def preferencias(request):
    aviso = ""
    if request.method == "POST":
        servicios.poner_preferencias(request.user, request.POST.getlist("activados"))
        aviso = "Preferencias guardadas."
    apagados = servicios.desactivados(request.user)
    grupos = []
    for codigo, nombre in ORIGENES_DE_AVISO:
        tipos = [
            {"codigo": tipo.codigo, "nombre": tipo.nombre, "activado": tipo.codigo not in apagados}
            for tipo in sorted(registro.avisos.values(), key=lambda tipo: tipo.nombre)
            if tipo.origen == codigo
        ]
        if tipos:
            grupos.append({"nombre": nombre, "tipos": tipos})
    return render(request, "comunicaciones/preferencias.html", {"grupos": grupos, "aviso": aviso})
