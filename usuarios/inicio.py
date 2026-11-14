"""
Tarjetas de «Inicio → Mis datos» que aporta «usuarios» (declaradas en usuarios/apps.py; dónde sale cada
una lo decide config/inicio.py):

- «Datos públicos»: lo que de tu cuenta ven las demás personas (el alias y desde cuándo estás).
- «Datos privados»: lo que solo ves tú (y el superadmin, para ayudarte a recuperar la cuenta).

Las dos llevan el botón «Editar», que va a «Configuración de mi cuenta → Mis datos → Datos».
"""

from django.urls import reverse

from base.contrato import ApartadoDeTarjeta, FilaDeResumen, ResumenDeTarjeta


# Resumen de los datos públicos de la cuenta. Sin consultas (todo está en el usuario).
#   - usuario: quien mira.
def datos_publicos(usuario):
    filas = (
        FilaDeResumen(usuario.alias, detalle="alias: tu nombre en la plataforma"),
        FilaDeResumen(f"{usuario.activado_el:%d/%m/%Y}", detalle="en la plataforma desde"),
    )
    return ResumenDeTarjeta(apartados=(ApartadoDeTarjeta(filas=filas),), enlace=reverse("usuarios:datos"), boton="Editar")


# Resumen de los datos privados de la cuenta. Sin consultas. Un tema vacío es el del sistema operativo.
#   - usuario: quien mira.
def datos_privados(usuario):
    filas = (
        FilaDeResumen(usuario.correo_alternativo or "Sin correo alternativo", detalle="correo para avisos y para recuperar la cuenta"),
        FilaDeResumen(usuario.get_origen_display(), detalle="cómo se creó la cuenta"),
        FilaDeResumen(
            f"Tema {(usuario.get_tema_display() or 'del sistema').lower()}, letra {usuario.get_letra_display().lower()}, "
            f"densidad {usuario.get_densidad_display().lower()}",
            reverse("usuarios:preferencias"),
            "cómo ves la plataforma",
        ),
    )
    return ResumenDeTarjeta(apartados=(ApartadoDeTarjeta(filas=filas),), enlace=reverse("usuarios:datos"), boton="Editar")
