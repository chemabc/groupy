# Arranque y pruebas

## 1. Crear el proyecto nuevo a partir de este kit (una sola vez)

En tu ordenador (Ubuntu), **fuera de VS Code**, abre una terminal:

```bash
# Copia el kit a una carpeta nueva, fuera del proyecto de la versión 1
#     -r: copia la carpeta entera, con sus subcarpetas
#     -T: copia el contenido de nuevo-proyecto/ dentro de la carpeta de destino (incluidos los
#         ficheros ocultos, como .devcontainer y .gitignore), sin crear otra carpeta dentro
#     <carpeta-v1>: ruta de tu proyecto actual en Ubuntu (la que tiene .devcontainer/)
#     ~/asambleas-v2: carpeta del proyecto nuevo; puedes cambiar el nombre
cp -rT <carpeta-v1>/nuevo-proyecto ~/asambleas-v2

# Entra en la carpeta nueva
cd ~/asambleas-v2

# Crea el repositorio de Git con la rama principal «main»
#     -b main: nombre de la rama inicial
git init -b main

# Guarda el primer commit con todo el kit
#     add .: añade todos los ficheros de la carpeta
#     -m: mensaje del commit
git add . && git commit -m "Kit inicial: diseño, contenedor y esqueleto de Django"

# Abre la carpeta en VS Code
#     .: la carpeta actual
code .
```

En VS Code, cuando aparezca el aviso, pulsa **«Reopen in Container»** (o usa la paleta de órdenes:
*Dev Containers: Reopen in Container*). La primera vez tarda unos minutos: construye la imagen, arranca
PostgreSQL y Redis e instala las librerías de Python.

> Los datos de PostgreSQL de la versión 2 van en un volumen distinto del de la versión 1, porque Docker
> le pone el nombre de la carpeta. Las dos versiones pueden convivir.

## 2. Comprobar que funciona

Dentro del contenedor, en la terminal de VS Code:

```bash
# Revisa la configuración de Django sin tocar la base de datos
#     check: busca errores en los ajustes y en el código
python manage.py check

# Arranca el servidor de desarrollo
#     runserver: servidor web de Django para desarrollo
#     0.0.0.0:8000: escucha en todas las direcciones del contenedor, en el puerto 8000
python manage.py runserver 0.0.0.0:8000
```

Abre http://localhost:8000: debe salir la pantalla de entrada (antes, crea las tablas y los usuarios
de ejemplo, como se explica más abajo).

### Los estilos y las librerías de la interfaz

Al crear el contenedor ya se ejecutan `npm install` y `npm run construir`. Si cambias plantillas o
estilos mientras programas, deja en otra terminal:

```bash
# Recompila el CSS cada vez que guardas una plantilla
#     run vigilar: orden definida en package.json (copia htmx y Alpine y vigila con Tailwind)
npm run vigilar
```

Si alguna vez falta `static/generado/` (por ejemplo, tras clonar el repositorio fuera del contenedor):

```bash
# Instala las librerías de la interfaz
#     install: lee package.json y package-lock.json y llena node_modules
npm install
# Genera static/generado/ una vez
#     run construir: copia htmx y Alpine y compila el CSS reducido
npm run construir
```

### La base de datos y los usuarios de ejemplo

```bash
# Crea o pone al día las tablas de la base de datos de la plataforma
#     migrate: aplica las migraciones pendientes de todos los módulos
python manage.py migrate

# Lo mismo en la base de la bóveda (la identidad real), que va aparte
#     --database=boveda: aplica las migraciones en esa base (solo crea las tablas de la bóveda)
python manage.py migrate --database=boveda

# Crea los datos de ejemplo de todos los módulos (solo funciona en desarrollo)
#     ejemplos: orden del módulo «ejemplos»
#     crear: crea los que falten; con «borrar» se quitan
python manage.py ejemplos crear
```

Los usuarios de ejemplo son animales y árboles (Lince, Nutria, Encina, Roble…). El superadmin es
**superadmin**. Todos tienen la contraseña `M3n0sL3ctiv4s`, y cada cual puede cambiarla en «Configuración de mi cuenta →
Contraseña». Al entrar da igual escribir el alias con o sin tildes y mayúsculas («buho» entra en
«Búho»). Los datos de ejemplo también se crean y se borran desde **Desarrollo y mantenimiento →
Pruebas → Datos de ejemplo**; borrarlos no toca al superadmin.

Para cargar muchos grupos o usuarios de golpe, entra como superadmin en **Desarrollo y mantenimiento →
Pruebas**: descarga la plantilla (.ods), rellénala con LibreOffice y súbela. Para los usuarios, activa
antes «Permitir el alta masiva de usuarios».

### El trabajador de la bandeja (notificaciones)

Las notificaciones no se crean en el momento: el cambio deja un aviso en la bandeja de salida de
eventos_sw y un **trabajador** lo reparte unos segundos después. En el contenedor de desarrollo hay un
servicio `trabajador` (en `.devcontainer/docker-compose.yml`) que lo hace solo; al añadirlo hay que
**reconstruir el contenedor** (en VS Code: «Dev Containers: Rebuild Container»). Si no está en marcha,
se puede lanzar a mano en otro terminal:

```bash
# Reparte los avisos pendientes y se queda esperando más (Ctrl+C para parar)
#     procesar_bandeja: orden del módulo eventos_sw
#     --una-vez: si se añade, reparte lo pendiente y termina
python manage.py procesar_bandeja
```

El trabajador también hace, la primera vez que da una vuelta cada día, las **tareas diarias** de los
módulos (caducar solicitudes vencidas, crear las siguientes veces de las series de eventos, la limpieza…). Para
lanzarlas a mano en cualquier momento:

```bash
# Ejecuta ahora todas las tareas diarias y dice qué ha hecho cada una
#     tareas_diarias: orden del módulo base
python manage.py tareas_diarias
```

### Los dos repositorios en GitHub

La plataforma y el editor van cada uno a su repositorio de GitHub, en la cuenta `chemabc` (privados):
`gestion-de-asambleas` y `editor-colaborativo`. Las direcciones ya están puestas (`git remote -v` y
`git -C editor remote -v`). Para subirlos la primera vez:

1. En github.com, crea los dos repositorios **vacíos** (sin README) con esos nombres.
2. Inicia sesión desde el contenedor (una vez). Por ejemplo, con un token personal de GitHub con permiso
   `repo`, la primera vez que git lo pida.
3. Sube los dos:

```bash
# Sube la plataforma (rama master) y deja apuntado a dónde va
#   - -u origin master: la rama master va a «origin» y se recuerda para los siguientes git push
git push -u origin master
# Lo mismo con el editor (su rama se llama main)
#   - -C editor: ejecuta git dentro de la carpeta del editor
git -C editor push -u origin main
```

### El editor en tiempo real (otro repositorio)

El editor colaborativo es **un repositorio aparte**, porque lo pueden usar otras aplicaciones. Vive dentro
de la carpeta `editor/` (la plataforma la ignora: ver `.gitignore`), con su propio historial de git. El
servicio `editor` del contenedor lo arranca solo. Si la carpeta no existe, la plataforma funciona igual, con
el formulario de siempre, y la prueba del editor en el navegador se salta.

```bash
# Comprobar que está y en qué versión
#   - git -C editor: ejecuta git dentro de la carpeta del editor
git -C editor log --oneline -1
```

## 3. Seguir con Claude

Abre Claude Code en el contenedor nuevo y pídele: «Lee CLAUDE.md y docs/diseno.md y empecemos la
fase 0». La memoria de Claude (por ejemplo, responder en castellano o documentar solo en Markdown) se
comparte entre los dos contenedores, porque los dos usan el volumen `claude-code-config`.

## 4. Pasar las pruebas

```bash
# Pasa todas las pruebas, también las de pantalla en Chromium sin interfaz
#     test: crea una base de datos temporal, ejecuta las pruebas y la borra al terminar
python manage.py test
```

Las pruebas de pantalla (`base/tests/test_navegador.py`) usan el CSS ya construido, así que antes
conviene haber ejecutado `npm run construir`. Si Chromium no está instalado, se saltan. Para instalarlo:

```bash
# Descarga el Chromium sin interfaz de Playwright
#     install chromium: solo el navegador Chromium
#     --with-deps: también las librerías del sistema que necesita
python -m playwright install --with-deps chromium
```

## 5. Antes de comprobar: todo al día y limpio

Antes de una ronda de comprobaciones a mano (`docs/comprobaciones.md`), estos pasos aseguran que se usa la
última versión del código, que las librerías están instaladas, que los servicios han arrancado de nuevo
con ese código y que las dos bases de datos responden. Se hacen en este orden; ninguno borra datos.

### 5.1 ¿Hace falta «Rebuild Container»?

**Casi nunca.** Reconstruir el contenedor rehace las **imágenes** (Python, Node, Chromium…) y lee otra vez
`.devcontainer/`. Solo hace falta si ha cambiado algo de esa carpeta (un servicio nuevo, una variable
nueva). **La bóveda no se reconstruye:** es una base de datos dentro del servicio `db`, y sus datos viven en
un volumen (`pgdata`) que sobrevive a reconstruir. Lo que la pone al día son sus migraciones (paso 5.4).

Para saber si ha cambiado `.devcontainer/` desde la última vez que reconstruiste (dentro del contenedor):

```bash
# Lista los commits que han tocado la carpeta del contenedor en los últimos 7 días
#     --since="7 days ago": solo los recientes (pon la fecha de tu última reconstrucción)
#     --oneline: un commit por línea
#     -- .devcontainer: solo los que cambian esa carpeta
git log --since="7 days ago" --oneline -- .devcontainer
```

Si sale alguno: en VS Code, `F1` → «Dev Containers: Rebuild Container». Tarda unos minutos; después,
sigue desde el paso 5.3 (los servicios ya arrancan nuevos).

### 5.2 Reiniciar los servicios (en una terminal de tu ordenador, fuera de VS Code)

El **editor** y el **trabajador** leen su código solo al arrancar: hay que reiniciarlos después de cada
cambio. Al arrancar, el editor instala lo suyo y vuelve a construir su cliente (`editor/publico/cliente.js`).

```bash
# Reinicia el editor y el trabajador (los busca por su nombre)
#     docker ps -q: solo los identificadores de los contenedores en marcha
#     -f name=editor / -f name=trabajador: solo los que llevan ese nombre
#     docker restart: los para y los vuelve a arrancar
docker restart $(docker ps -q -f name=editor) $(docker ps -q -f name=trabajador)

# Comprueba que están todos en marcha: app, editor, trabajador, db, redis y antivirus
#     --format: solo el nombre y el estado («Up …»; si alguno dice «Restarting», algo falla)
docker ps --format '{{.Names}}  {{.Status}}'

# Si alguno falla, sus últimos mensajes dicen por qué
#     --tail 30: solo las 30 últimas líneas
docker logs --tail 30 $(docker ps -aq -f name=editor)
```

### 5.3 Código y librerías al día (en la terminal de VS Code, dentro del contenedor)

```bash
# En qué versión está cada repositorio (el último commit) y si hay cambios sin guardar
#     log -1 --oneline: solo el último commit, en una línea
#     status --short: lo cambiado y sin guardar, si hay algo
#     -C editor: lo mismo dentro de la carpeta del editor (es otro repositorio)
git log -1 --oneline && git status --short
git -C editor log -1 --oneline && git -C editor status --short

# Librerías de Python (si ya están, solo lo comprueba)
#     --user: en la carpeta del usuario
#     -q: sin detalles
#     -r requirements.txt: las de esa lista
pip install --user -q -r requirements.txt

# Librerías de la interfaz y ficheros generados (htmx, Alpine y el CSS con las clases nuevas)
#     install: lee package.json y llena node_modules
#     run construir: copia htmx y Alpine y compila static/generado/estilos.css
npm install && npm run construir
```

### 5.4 Bases de datos al día y funcionando

```bash
# Pone al día las tablas de la plataforma
#     migrate: aplica las migraciones que falten (si no falta ninguna, no hace nada)
python manage.py migrate

# Lo mismo en la base de la bóveda (va aparte)
#     --database=boveda: aplica solo en esa base
python manage.py migrate --database=boveda

# Comprueba que el código no tiene cambios de tablas sin migración y que los ajustes están bien
#     makemigrations --check --dry-run: dice «No changes detected» sin crear nada
#     check: revisa la configuración de Django
python manage.py makemigrations --check --dry-run && python manage.py check

# Pregunta a las dos bases y a Redis si responden: escribe «default asambleas», «boveda boveda» y «Redis: True»
#     shell -c: ejecuta el Python que va entre comillas con Django ya cargado
python manage.py shell -c "
from django.db import connections
import redis
for nombre in ('default', 'boveda'):
    with connections[nombre].cursor() as cursor:
        cursor.execute('select current_database()')
        print(nombre, cursor.fetchone()[0])
print('Redis:', redis.Redis(host='redis').ping())
"
```

### 5.5 Los demás servicios responden

```bash
# El editor: escribe «bien»
#     -s: sin barra de progreso
curl -s http://editor:1234/salud; echo

# La plataforma vista desde el editor: escribe «403» (la petición llega; falta la firma, y está bien)
#     -o /dev/null: no enseña la respuesta
#     -w "%{http_code}": escribe solo el código de la respuesta
curl -s -o /dev/null -w "%{http_code}\n" "http://app:8000/editor/texto/?sala=x"

# El antivirus: escribe «b'PONG\x00'» (la primera vez tras reconstruir tarda unos minutos)
#     -c: ejecuta la línea de Python que va entre comillas
python -c "import socket; s=socket.create_connection(('antivirus',3310),5); s.sendall(b'zPING\0'); print(s.recv(10))"

# El trabajador: escribe 0 (o un número que baja en unos segundos)
python manage.py shell -c "from eventos_sw.models import AvisoPendiente; print(AvisoPendiente.objects.count())"
```

### 5.6 Datos de ejemplo y servidor

```bash
# Crea los datos de ejemplo que falten (no toca lo que ya hay)
#     ejemplos crear: orden del módulo «ejemplos»
python manage.py ejemplos crear

# Opcional: si quieres empezar con los datos de ejemplo como recién hechos, bórralos y créalos de nuevo
#     ejemplos borrar: quita los datos de ejemplo de cada módulo (lo que hayas creado con las personas
#       de ejemplo puede irse con ellas)
python manage.py ejemplos borrar && python manage.py ejemplos crear

# Ejecuta las tareas diarias una vez (series, solicitudes caducadas, limpieza)
#     tareas_diarias: orden del módulo base
python manage.py tareas_diarias
```

El **servidor** se reinicia solo al cambiar el código, pero si llevaba tiempo en marcha conviene pararlo
(Ctrl+C en su terminal) y arrancarlo de nuevo:

```bash
# Arranca el servidor de desarrollo
#     runserver: servidor web de Django para desarrollo
#     0.0.0.0:8000: escucha en todas las direcciones del contenedor, en el puerto 8000
python manage.py runserver 0.0.0.0:8000
```

### 5.7 En el navegador

- Abre http://localhost:8000 y recarga **sin caché**: **Ctrl+F5** (o Ctrl+Mayús+R). Así se cargan el CSS, el
  JavaScript y el cliente del editor nuevos.
- Opcional: las pruebas automáticas (`python manage.py test`, unos 7 minutos) deben acabar en `OK`.

Ya puedes empezar por la **Guía rápida de comprobación**, al principio de `docs/comprobaciones.md`.
