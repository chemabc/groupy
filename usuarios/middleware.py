"""
Capas de «usuarios» que pasan por cada petición:
- EntradaObligatoria: impide ver nada sin iniciar sesión.
- ApuntarActividad: apunta el día en que cada persona usa la plataforma.

EntradaObligatoria: impide ver nada sin iniciar sesión (premisa 13: nada es público por defecto).

Se basa en LoginRequiredMiddleware de Django: toda vista exige sesión, salvo las marcadas con
@login_not_required (la pantalla de entrada ya lo está). Lo público (fase 8) se marcará así a propósito.
Está en config/settings.py, en MIDDLEWARE.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.middleware import LoginRequiredMiddleware
from django.http import HttpResponse
from django.utils import timezone
from django.utils.functional import empty


class EntradaObligatoria(LoginRequiredMiddleware):
    """
    Manda a la pantalla de entrada a quien no ha iniciado sesión. Añade dos cosas a la de Django:
    entiende las peticiones de htmx y deja pasar la barra de depuración.
    """

    # Django la llama antes de cada vista. Deja pasar sin mirar la sesión:
    #   - las vistas marcadas con @login_not_required. La de Django carga antes el usuario (una consulta)
    #     aunque la vista no lo necesite; aquí se mira primero la marca y se ahorra esa consulta;
    #   - las direcciones internas de la barra de depuración (solo existen en desarrollo), que el
    #     navegador pide por su cuenta para pintar la barra.
    def process_view(self, request, view_func, view_args, view_kwargs):
        if not getattr(view_func, "login_required", True) or request.path.startswith("/__debug__/"):
            return None
        return super().process_view(request, view_func, view_args, view_kwargs)

    # Respuesta para quien no ha iniciado sesión. Normalmente, una redirección a la entrada. Pero si la
    # petición viene de htmx (por ejemplo, al navegar con la sesión ya caducada), htmx metería la
    # pantalla de entrada dentro de la zona central; con la cabecera HX-Redirect, htmx carga la
    # pantalla de entrada como página entera.
    def handle_no_permission(self, request, view_func):
        redireccion = super().handle_no_permission(request, view_func)
        if request.headers.get("HX-Request") != "true":
            return redireccion
        respuesta = HttpResponse(status=200)
        respuesta["HX-Redirect"] = redireccion.url
        return respuesta


class ApuntarActividad:
    """
    Apunta en el usuario el día en que usa la plataforma (Usuario.ultima_actividad), una sola vez al día: la
    primera petición del día hace una actualización y las demás ninguna. Solo el día, nunca la hora ni qué
    hace. Lo usa la lista de miembros de la administración para marcar a quien lleva tiempo sin actividad
    (grupos/inactividad.py). Va en config/settings.py, en MIDDLEWARE, después de la autenticación.
    """

    # Django la crea una vez al arrancar, con la siguiente capa de la cadena.
    def __init__(self, siguiente):
        self.siguiente = siguiente

    # Django la llama en cada petición. Después de la vista, si esta ya ha cargado a la persona (casi todas
    # las pantallas lo hacen, para el menú) y hoy aún no constaba, lo apunta (con update, sin pasar por
    # save: no toca nada más del usuario). Si la vista no la ha cargado, no la carga solo para esto: no cuesta
    # ninguna consulta de más.
    def __call__(self, request):
        respuesta = self.siguiente(request)
        perezoso = getattr(request, "user", None)
        usuario = getattr(perezoso, "_wrapped", empty)
        if usuario is not empty and usuario.is_authenticated:
            hoy = timezone.localdate()
            if usuario.ultima_actividad != hoy:
                get_user_model().objects.filter(pk=usuario.pk).update(ultima_actividad=hoy)
                usuario.ultima_actividad = hoy
        return respuesta
