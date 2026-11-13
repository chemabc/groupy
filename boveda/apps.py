"""
Configuración y contrato del módulo «boveda».
"""

from base.contrato import Capa, ModuloConfig, Permiso


class BovedaConfig(ModuloConfig):
    """
    Contrato del módulo «boveda»: la identidad real, en su propia base de datos. De momento, las tablas y
    el alta provisional por el superadmin; la firma ciega, el sobre y los demás métodos de validación
    llegan en la fase 8. Sus pantallas están en el módulo «administracion».
    """

    name = "boveda"
    verbose_name = "Bóveda de identidad"
    capa = Capa.IDENTIDAD
    descripcion = (
        "Identidad real de las personas (nombre, validación, pases) y dominios de correo permitidos, en una "
        "base de datos aparte, sin ninguna columna que la una con la plataforma."
    )
    permisos = (
        # Sin roles por defecto: solo el superadmin.
        Permiso("boveda.ver", "Ver y gestionar la bóveda: personas reales, su validación y los dominios de correo"),
    )
