# Imagen base: Python 3.13 oficial de Docker Hub sobre Debian 13 «trixie», versión reducida «slim»
FROM python:3.13-slim-trixie

# Datos del usuario sin privilegios con el que se trabaja dentro del contenedor
#     USUARIO: nombre del usuario
#     UID: número de usuario; 1000 coincide con el primer usuario de Ubuntu, así los ficheros creados son tuyos
#     GID: número de grupo, con el mismo criterio que UID
ARG USUARIO=dev
ARG UID=1000
ARG GID=1000

# Instala las herramientas del sistema y borra la lista de paquetes descargada
#     apt-get update: descarga la lista actualizada de paquetes de Debian
#     apt-get install -y: instala sin pedir confirmación
#     --no-install-recommends: instala solo lo imprescindible
#     git: control de versiones
#     curl, ca-certificates: descargas seguras por HTTPS
#     build-essential: compiladores para librerías de Python con partes en C
#     libpq-dev: cabeceras de PostgreSQL para compilar el conector psycopg
#     postgresql-client: comando psql para consultar la base de datos a mano
#     openssl, poppler-utils: comprobar firmas y extraer texto de PDF (validación de documentos)
#     nodejs, npm: necesarios para Claude Code, Tailwind CSS y las islas en React
#     sudo: permite al usuario dev hacer tareas de administración dentro del contenedor
#     rm -rf /var/lib/apt/lists/*: borra la lista de paquetes para que la imagen ocupe menos
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git curl ca-certificates build-essential libpq-dev postgresql-client \
      openssl poppler-utils nodejs npm sudo \
 && rm -rf /var/lib/apt/lists/*

# Crea el grupo y el usuario sin privilegios
#     groupadd --gid: crea el grupo con el número indicado
#     useradd --uid --gid: crea el usuario con ese número y en ese grupo
#     --create-home: crea su carpeta personal /home/dev
#     --shell /bin/bash: intérprete de comandos por defecto
RUN groupadd --gid ${GID} ${USUARIO} \
 && useradd --uid ${UID} --gid ${GID} --create-home --shell /bin/bash ${USUARIO}

# Permite a dev usar sudo sin contraseña (solo en el contenedor de desarrollo, nunca en producción)
#     echo "..." > /etc/sudoers.d/dev: escribe la regla en un fichero propio de sudo
#     ALL=(ALL) NOPASSWD:ALL: puede ejecutar cualquier orden como root sin pedir contraseña
#     chmod 0440: deja el fichero en solo lectura, como exige sudo para aceptarlo
# Crea la carpeta de configuración de Claude Code con dev como dueño, para que el volumen nazca con ese dueño
#     mkdir -p: crea la carpeta y las intermedias si faltan
#     chown -R dev:dev: cambia el dueño (usuario y grupo) a dev
RUN echo "${USUARIO} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USUARIO} \
 && chmod 0440 /etc/sudoers.d/${USUARIO} \
 && mkdir -p /home/${USUARIO}/.claude \
 && chown -R ${USUARIO}:${USUARIO} /home/${USUARIO}/.claude

# Variables de entorno de Python
#     PYTHONDONTWRITEBYTECODE=1: no crea ficheros .pyc dentro del proyecto
#     PYTHONUNBUFFERED=1: muestra la salida de Python al instante
#     PATH: añade la carpeta donde pip instala los programas del usuario
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/dev/.local/bin:$PATH

# Carpeta de trabajo por defecto dentro del contenedor
WORKDIR /workspace

# A partir de aquí todo se ejecuta como el usuario sin privilegios, nunca como root
USER ${USUARIO}