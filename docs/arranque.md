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

Cada vez que vayas a hacer una ronda de comprobaciones a mano (`docs/comprobaciones.md`), copia y pega estos
tres bloques, en orden. Así te aseguras de que se usa la última versión del código, de que las librerías
están instaladas, de que los servicios han arrancado de nuevo con ese código y de que las dos bases de datos
responden. **Ninguno borra datos.**

**¿Hay que reconstruir el contenedor o la bóveda?** Casi nunca. «Rebuild Container» rehace las imágenes y
lee otra vez `.devcontainer/`: solo hace falta si ha cambiado esa carpeta (el apartado 5.6 dice cómo
saberlo). **La bóveda no se reconstruye nunca:** es una base de datos del servicio `db`, sus datos viven en un
volumen que sobrevive a todo, y se pone al día con sus migraciones (las aplica el bloque 3).

### 5.1 Bloque 1: reiniciar los servicios (en una terminal de tu ordenador, fuera de VS Code)

El **editor** y el **trabajador** leen su código solo al arrancar, así que hay que reiniciarlos después de
cada cambio. Al arrancar, el editor instala lo suyo y vuelve a construir su cliente. `docker` no está dentro
del contenedor: este bloque va en la terminal de Ubuntu.

```bash
# Reinicia el editor y el trabajador (los busca por su nombre)
#     docker ps -q: solo los identificadores de los contenedores en marcha
#     -f name=editor, -f name=trabajador: solo los que llevan ese nombre
#     docker restart: los para y los vuelve a arrancar
docker restart $(docker ps -q -f name=editor) $(docker ps -q -f name=trabajador)
# Espera 20 segundos a que el editor instale y construya lo suyo
sleep 20
# Enseña los servicios: deben salir app, editor, trabajador, db, redis y antivirus, todos con «Up»
#     --format: solo el nombre y el estado («Restarting» quiere decir que algo falla)
docker ps --format '{{.Names}}  {{.Status}}'
```

Si alguno no dice «Up», sus últimos mensajes dicen por qué (cambia `editor` por el nombre del servicio):

```bash
# Las 30 últimas líneas de lo que ha escrito el servicio
#     -a: también los parados
#     --tail 30: solo las últimas 30 líneas
docker logs --tail 30 $(docker ps -aq -f name=editor)
```

### 5.2 Bloque 2: el servidor (en una terminal de VS Code)

Si ya estaba en marcha, páralo con **Ctrl+C** en su terminal y vuelve a arrancarlo, para que empiece limpio.
Deja esta terminal abierta mientras compruebas.

```bash
# Va a la carpeta del proyecto y arranca el servidor de desarrollo
#     runserver: servidor web de Django para desarrollo (se reinicia solo al cambiar el código)
#     0.0.0.0:8000: escucha en todas las direcciones del contenedor, en el puerto 8000
cd /workspace && python manage.py runserver 0.0.0.0:8000
```

### 5.3 Bloque 3: todo al día y comprobado (en otra terminal de VS Code)

Abre otra terminal (el **+** del panel de terminales) y pega:

```bash
# Pone todo al día y comprueba que responde; dice ✔ o ✘ en cada paso (tarda un minuto y medio)
cd /workspace && bash herramientas/al_dia.sh
```

Tiene que acabar en **«Todo bien»**. Debajo de cada ✘ sale el motivo; la tabla de 5.5 dice qué hacer.

### 5.4 En el navegador

Abre http://localhost:8000 y recarga **sin caché**, con **Ctrl+F5** (o Ctrl+Mayús+R): así se cargan el CSS,
el JavaScript y el cliente del editor nuevos. Empieza por la **«Guía rápida de comprobación»**, al principio de
`docs/comprobaciones.md`.

### 5.5 Qué hace `herramientas/al_dia.sh` y qué hacer si un paso falla

Cada línea del script está explicada en el propio fichero. Son estas órdenes (todas dentro del contenedor, en
`/workspace`):

| Paso | Orden | Si sale ✘ |
|---|---|---|
| Versiones | `git log -1` y `git -C editor log -1` | Solo informa. «Cambios sin guardar»: es código sin commit. |
| Librerías de Python | `pip install --user -q -r requirements.txt` | Lee el motivo (suele ser la red). |
| Librerías de la interfaz | `npm install` | Ídem. |
| Interfaz construida | `npm run construir` | Lee el motivo; suele ser un error en una plantilla o en el CSS. |
| Cliente del editor al día | mira si `editor/src` es más nuevo que `editor/publico/cliente.js` | Repite el bloque 1 (reinicia el editor). |
| Tablas de la plataforma | `python manage.py migrate` | Lee el motivo y avisa a Claude. |
| Tablas de la bóveda | `python manage.py migrate --database=boveda` | Ídem. |
| Sin cambios de tablas pendientes | `python manage.py makemigrations --check --dry-run` | Falta una migración en el código: avisa a Claude. |
| Configuración de Django | `python manage.py check` | Lee el motivo y avisa a Claude. |
| Bases y Redis responden | una consulta a cada base y un `ping` a Redis | Repite el bloque 1 o reinicia `db` / `redis` igual que el editor. |
| Redis guarda en disco | `config_get('appendonly')` | «Rebuild Container» (5.6). |
| El editor responde | `curl http://editor:1234/salud` → «bien» | Repite el bloque 1 y mira `docker logs` del editor. |
| La plataforma responde al editor | `curl http://app:8000/editor/texto/?sala=x` → «403» | El servidor no está en marcha (bloque 2). |
| El antivirus responde | PING a `antivirus:3310` → «PONG» | Tras reconstruir tarda unos minutos; si no, reinícialo como el editor. |
| El trabajador reparte los avisos | cuenta la bandeja de avisos: 0 o bajando | Repite el bloque 1 (reinicia el trabajador). |
| Sin avisos fallidos | cuenta los avisos que fallaron 5 veces | Arregla la causa (casi siempre, reiniciar el trabajador) y ejecuta la orden que enseña: los vuelve a poner en cola. |
| Datos de ejemplo | `python manage.py ejemplos crear` | Lee el motivo y avisa a Claude. |
| Tareas diarias | `python manage.py tareas_diarias` | Ídem. |
| El servidor está en marcha | `curl http://localhost:8000/` → 200 o 302 | Bloque 2. |

### 5.6 De vez en cuando

**¿Ha cambiado `.devcontainer/`?** Si esta orden (dentro del contenedor) enseña algún commit desde la última
vez que reconstruiste, en VS Code, `F1` → «Dev Containers: Rebuild Container» y después los bloques 2 y 3.

```bash
# Los commits de los últimos 7 días que han tocado la carpeta del contenedor
#     --since="7 days ago": cambia el plazo por el tiempo desde tu última reconstrucción
#     --oneline: un commit por línea
#     -- .devcontainer: solo los que cambian esa carpeta
cd /workspace && git log --since="7 days ago" --oneline -- .devcontainer
```

**Datos de ejemplo como recién hechos** (las comprobaciones los cambian):

```bash
# Borra los datos de ejemplo de cada módulo y los crea de nuevo
#     ejemplos borrar: quita los datos de ejemplo (lo que hayas creado con las personas de ejemplo puede
#       irse con ellas)
#     ejemplos crear: los crea de nuevo
cd /workspace && python manage.py ejemplos borrar && python manage.py ejemplos crear
```

**Pruebas automáticas** (unos 7 minutos; deben acabar en `OK`):

```bash
# Pasa todas las pruebas, también las del navegador
#     test: crea bases de datos temporales, ejecuta las pruebas y las borra al terminar
#     --noinput: si quedó una base temporal de otra vez, la borra sin preguntar
cd /workspace && python manage.py test --noinput
```
