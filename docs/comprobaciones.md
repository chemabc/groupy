# Comprobaciones pendientes

Guía para comprobar a mano, paso a paso, lo construido. Para dejarlo todo al día y limpio antes de una
ronda, sigue `docs/arranque.md`, apartado 5; después, la **«Guía rápida de comprobación»** recorre lo más
arriesgado de lo último. Para el detalle, empieza por **«Antes de empezar»**: cada paso
dice primero **cómo saber si ya está hecho** y, solo si no lo está, **qué ejecutar**. Después, una
sección por pieza, en el orden en que se hicieron, con **qué mirar** en cada pantalla.

Marca cada casilla al comprobarla: se recuerda en tu navegador (si borras sus datos, vuelven a salir
sin marcar). Si algo no sale como dice la guía, apunta la pieza y el paso y cuéntaselo a Claude.

**Quién es quién en los datos de ejemplo** (todos con la contraseña `M3n0sL3ctiv4s`):

| Alias | Dónde está | Qué es |
|---|---|---|
| superadmin | ningún grupo | superadmin: lo ve todo salvo lo personal |
| Lince | GRU Henares (y GRU Segre, de ORG Ebro) | admin de GRU Henares y de ORG Tajo |
| Nutria | GRU Henares (y GRU Lozoya) | usuaria normal |
| Garza | GRU Sorbe (subgrupo de GRU Henares) | usuaria normal |
| Tejón | GRU Manzanares | admin de su grupo |
| Zorro | GRU Arga | admin de GRU Arga y de ORG Ebro |

Truco: abre una **ventana privada** (o otro navegador) para tener a dos personas a la vez, por ejemplo
Lince en una y Nutria en otra.

---

## Guía rápida de comprobación

Un recorrido corto (unos 20 minutos) por lo más arriesgado de lo último que se ha hecho. Antes, deja todo al
día y limpio con `docs/arranque.md`, apartado 5. Después, cuenta a Claude qué ha ido bien y qué no (por
ejemplo, «1, 2 y 4 bien; en el 3, tal cosa»): lo comprobado se quita de esta guía y de su sección de abajo.

- [ ] **1. Privacidad** (sección 2). Como **Nutria**, crea un proyecto personal y copia su dirección. Como
  **superadmin**, no sale en ninguna lista y, pegando la dirección, no te deja verlo.
- [ ] **2. Permisos** (sección 10). Como **superadmin**, «Usuarios → Roles y permisos → Explicar un permiso»:
  Nutria, `documentos.crear`, GRU Henares. El razonamiento dice por qué sí o por qué no, y tiene sentido.
- [ ] **3. Consultas secretas** (sección 36).
  - Como **Nutria**, vota en «¿Qué día hacemos la asamblea?», cambia el voto, y arriba sale «🔒 Voto secreto».
  - Como **Lince**, crea una consulta sin «voto secreto» y vota: en los resultados salen los alias.
  - Como **Garza**, propón una consulta: espera dos apoyos y Nutria la ve en «Comunicaciones → Solicitudes».
- [ ] **4. Documentos y editor** (secciones 37, 44, 45 y 46).
  - Como **Lince**, «Participación → Documentos → Nuevo»: crea uno con descripción. En la lista, su **ⓘ** la
    enseña en una ventanita.
  - Abre «Escribir» en el orden del día de diciembre: el **cursor se ve**, también en modo oscuro.
  - En una ventana privada, como **Nutria**, el mismo documento → «Seguir en directo»: dice «No tienes la
    redacción… pero sí comentar». Comenta un trozo: a Lince le sale en amarillo.
  - Como Lince, dale la redacción a Nutria (en la ficha) y escribid los dos a la vez: cada uno ve el cursor
    y el nombre del otro.
  - Como Lince, **💾 Guardar versión** con una nota. En la ficha, «Versiones» la enseña con su fecha, su
    hora y la nota.
  - **Sin conexión:** en una terminal de tu ordenador, `docker stop $(docker ps -q -f name=editor)`. A los 5
    segundos sale el **aviso rojo**. Escribe algo y vuelve a arrancarlo con
    `docker start $(docker ps -aq -f name=editor)`: el aviso se va y lo escrito queda guardado.
- [ ] **5. Del acta a decisiones** (sección 34). En el orden del día, «Crear el acta desde este orden del
  día». En «Acuerdos alcanzados», `- [votación 5-2-0] Huerto en el solar`; aprueba el acta. En
  «Participación → Decisiones» sale como «Votación», «5-2-0».
- [ ] **6. Menú** (sección 46). Arrastra el borde derecho del menú: el ancho se recuerda al recargar y con
  doble clic vuelve al de partida.

El paso 4 y el 5 cambian datos de ejemplo. Para dejarlos como recién hechos, `docs/arranque.md`, paso 5.6.

---

## 0. Antes de empezar

Las órdenes se escriben en la terminal de VS Code, dentro del contenedor, en la carpeta del proyecto.

### 0.1 Librerías de la interfaz instaladas

- [ ] **¿Ya está?** `npm ls --depth=0 mermaid svg-pan-zoom fullcalendar sortablejs` muestra las cuatro
  con su versión (mermaid@11.17.2, svg-pan-zoom@3.6.2, fullcalendar@6.1.22, sortablejs@1.15.7) y
  ninguna sale como «missing» o «UNMET».
  **Si no:**

```bash
# Instala las librerías de JavaScript que dicen package.json y package-lock.json
#     install: llena node_modules con las versiones exactas
npm install
```

### 0.2 Ficheros de la interfaz generados

- [ ] **¿Ya está?** Dos cosas:
  - `ls static/generado/diagramas static/generado/fullcalendar` lista `mermaid.min.js`,
    `svg-pan-zoom.min.js`, `index.global.min.js` y `es.global.min.js`;
  - y esta orden no escribe nada (si escribe plantillas, son más nuevas que los estilos y puede faltar
    alguno):

```bash
# Busca plantillas más nuevas que los estilos compilados
#     -name '*.html': solo las plantillas
#     -newer static/generado/estilos.css: solo las cambiadas después de compilar los estilos
#     -not -path './node_modules/*': sin mirar dentro de las librerías
find . -name '*.html' -newer static/generado/estilos.css -not -path './node_modules/*'
```

  **Si no:**

```bash
# Copia las librerías a static/generado/ y compila el CSS
#     run construir: orden de package.json (herramientas/construir.mjs y Tailwind)
npm run construir
```

### 0.3 Tablas de la base de datos al día (las dos bases)

Hazlo antes que el 0.4: si faltan tablas, la orden del 0.4 falla con «relation "…" does not exist».

- [ ] **¿Ya está?** Estas dos órdenes terminan sin decir nada (si falta alguna migración, la nombran):

```bash
# Comprueba si falta aplicar alguna migración en la base de la plataforma
#     --check: no cambia nada; avisa y termina con error si hay migraciones pendientes
python manage.py migrate --check
# Lo mismo en la base de la bóveda
#     --database=boveda: la base aparte con la identidad real
python manage.py migrate --check --database=boveda
```

  **Si no:**

```bash
# Aplica las migraciones pendientes en las dos bases
python manage.py migrate
python manage.py migrate --database=boveda
```

### 0.4 Datos de ejemplo al día

> **15 de noviembre de 2026:** la migración de las consultas rehace la tabla de papeletas (su número pasa a
> ser al azar) y se pierden las papeletas de los ejemplos. Rehaz los ejemplos (la orden de abajo) aunque la
> comprobación diga `True True`.

Los ejemplos crecen con cada pieza. Los últimos que se añadieron: las webs (portada de la plataforma y de
ORG Tajo, miniwebs de GRU Henares y GRU Jarama, y GRU Arga publicando para GRU Henares), y antes el PDF
«Plano del solar» y el enlace «Carpeta compartida del huerto» en GRU Henares (y, antes, mensajes en las salas de los grupos de Nutria y una
conversación suya, y el proyecto «Huerto comunitario» con dependencias, recursos y etiquetas). Necesita el
0.3 hecho.

- [ ] **¿Ya está?** Esta orden escribe `True True`:

```bash
# Pregunta a la base si están el PDF de ejemplo y las webs de ejemplo
#     shell -c: ejecuta una línea de Python con Django cargado
python manage.py shell -c "from django.apps import apps; D=apps.get_model('documentos','Documento'); P=apps.get_model('publico','Pagina'); print(D.objects.filter(titulo='Plano del solar').exists(), P.objects.filter(titulo='Taller de bicis').exists())"
```

  **Si no** (borra y vuelve a crear los ejemplos; no toca al superadmin). Ojo: borra también lo que hayas
  creado al probar dentro de las organizaciones de ejemplo (eventos, proyectos, recordatorios, peticiones
  de talentos, subgrupos…) y lo de las personas de ejemplo; lo de otras organizaciones no lo toca:

```bash
# Borra los datos de ejemplo de todos los módulos y los crea de nuevo
#     ejemplos borrar / ejemplos crear: orden del módulo «ejemplos»
python manage.py ejemplos borrar && python manage.py ejemplos crear
```

### 0.5 El trabajador (reparte las notificaciones y hace las tareas diarias)

Lee el código al arrancar: después de cada pieza nueva hay que **reiniciarlo** aunque esté en marcha.

- [ ] **¿Está en marcha?** En una terminal **de tu ordenador** (fuera de VS Code):
  `docker ps --format '{{.Names}}' | grep trabajador` muestra un nombre. Dentro del contenedor, otra
  pista: esta orden da `0` (o un número que baja en unos segundos):

```bash
# Cuenta los avisos que esperan en la bandeja de salida
python manage.py shell -c "from eventos_sw.models import AvisoPendiente; print(AvisoPendiente.objects.count())"
```

- [ ] **Reinícialo** (en la terminal de tu ordenador):

```bash
# Reinicia el contenedor del trabajador (lo busca por su nombre)
#     docker ps -q: solo los identificadores de los contenedores en marcha
#     -f name=trabajador: solo los que llevan «trabajador» en el nombre
#     docker restart: los para y los vuelve a arrancar
docker restart $(docker ps -q -f name=trabajador)
```

  Si no existe el servicio (contenedor antiguo): en VS Code, «Dev Containers: Rebuild Container». Para
  salir del paso sin él, déjalo en una terminal aparte: `python manage.py procesar_bandeja`.

### 0.6 Tareas diarias

- [ ] Ejecútalas una vez a mano (no pasa nada por repetirlas) y mira que cada una dice un número y no
  un error: `eventos.generar_series`, `solicitudes.caducar` y `limpieza.limpiar`.

```bash
# Ejecuta ahora todas las tareas diarias y dice qué ha hecho cada una
python manage.py tareas_diarias
```

### 0.7 Servidor y pruebas automáticas

- [ ] **¿Ya está el servidor?** http://localhost:8000 abre la entrada. **Si no:**
  `python manage.py runserver 0.0.0.0:8000` (se reinicia solo al cambiar el código).
- [ ] **Pruebas:** `python manage.py test --parallel 4` termina con `OK` (unas 395, en un par de
  minutos). Si dice `skipped=` con muchas, falta Chromium para las pruebas en el navegador:
  `python -m playwright install --with-deps chromium`.
  Si en paralelo salen muchos fallos de golpe con «Ya existe Organización…», suele ser **uno solo** que
  arrastra a los demás (en paralelo, un fallo deja sus datos sin deshacer). Busca en la salida el primer
  «failed:» o pásalas en serie (`python manage.py test`, unos 5 minutos), que dice cuál es.

### 0.75 Redis guarda en disco (urna de las consultas secretas)

- [ ] **¿Ya está?** Esta orden escribe `yes`:
  `python -c "import redis; print(redis.Redis(host='redis').config_get('appendonly')['appendonly'])"`. **Si no:**
  «Dev Containers: Rebuild Container» (el servicio `redis` ahora arranca con `--appendonly yes` y un
  volumen). Mientras tanto todo funciona, pero un reinicio de Redis perdería las papeletas que esperan.

### 0.8 Editor en tiempo real (servicio «editor»)

- [ ] **¿Ya está?** http://localhost:1234/salud dice «bien», y en la terminal del contenedor
  `echo $EDITOR_URL` dice `ws://localhost:1234`. **Si no:** el servicio es nuevo en
  `.devcontainer/docker-compose.yml`. En VS Code, «Dev Containers: Rebuild Container»: instala lo suyo,
  lo arranca solo y le pasa a la plataforma las variables `EDITOR_…`.
- [ ] **Para probarlo sin reconstruir**, en dos terminales del contenedor:

```bash
# Terminal 1: instala, construye y arranca el editor, que llama a la plataforma en localhost:8000
#   - EDITOR_CLAVE: la clave de desarrollo con la que cifra la biblioteca (la misma que en docker)
#   - EDITOR_APLICACIONES: esta plataforma, con el secreto de desarrollo y solo las carpetas «Actas»
cd editor && npm install && npm run construir && \
  EDITOR_CLAVE=p7W1ang9nadfmH153EJnuLo0Uwk64iDtNKd/684axXU= \
  EDITOR_APLICACIONES='{"asambleas":{"secreto":"solo-para-desarrollo-cambiar-en-produccion","url":"http://localhost:8000/editor","carpetas":["Actas"]}}' npm run arrancar
# Terminal 2: arranca la plataforma diciéndole dónde está el editor
#   - EDITOR_URL: el WebSocket que abre el navegador
#   - EDITOR_URL_INTERNA: la dirección desde la que la plataforma le pide cerrar salas
EDITOR_URL=ws://localhost:1234 EDITOR_URL_INTERNA=http://localhost:1234 python manage.py runserver 0.0.0.0:8000
```

- [ ] **¿Llega el editor a la plataforma?** (arreglado en [A-64]) Esta orden escribe `403` (firma no
  válida: la petición llega). Si escribe `400`, Django no acepta el nombre «app»: comprueba que
  `DJANGO_ALLOWED_HOSTS` no está puesto en el contenedor (o que incluye `app`) y reinicia el servidor.

```bash
# Pide a la plataforma, por el nombre que usa el editor dentro de Docker, el texto de una sala (sin firma)
#     -s: sin barra de progreso
#     -o /dev/null: no enseña la respuesta
#     -w "%{http_code}": escribe solo el código de la respuesta
curl -s -o /dev/null -w "%{http_code}\n" "http://app:8000/editor/texto/?sala=x"
```

- [ ] **¿El editor tiene su última versión?** Tras cambios en `editor/` (como los avisos de [A-64]), reinicia
  su contenedor (en VS Code, «Docker: Restart» del servicio `editor`, o «Rebuild Container»): al arrancar
  vuelve a construir el cliente.
- [ ] **¿Tiene biblioteca?** Al arrancar, el editor dice «Editor colaborativo en marcha en el puerto 1234»
  sin «(sin biblioteca: falta EDITOR_CLAVE)». **Si lo dice:** falta `EDITOR_CLAVE` (nueva en
  `.devcontainer/docker-compose.yml`): «Rebuild Container», o arráncalo a mano como arriba.
- [ ] Las pruebas del propio editor: `cd editor && npm run probar` (10 pruebas). Es otro repositorio:
  `git -C editor log --oneline -3`.

### 0.9 Antivirus de los archivos (servicio «antivirus», ClamAV)

- [ ] **¿Ya está?** En la terminal del contenedor, `echo $ANTIVIRUS` dice `antivirus:3310` y esta orden
  escribe `PONG`:

```bash
# Pregunta al antivirus si está despierto (orden PING de ClamAV)
#     -c: ejecuta la línea de Python que va entre comillas
python -c "import socket; s=socket.create_connection(('antivirus',3310),5); s.sendall(b'zPING\0'); print(s.recv(10))"
```

  **Si no:** el servicio es nuevo en `.devcontainer/docker-compose.yml`: «Dev Containers: Rebuild
  Container». La primera vez tarda **unos minutos** en descargar las firmas de virus; mientras, al subir un
  archivo sale «El antivirus no responde». Sin reconstruir (sin `ANTIVIRUS`), los archivos se guardan igual
  pero marcados «sin revisar».

---

## 1. Desarrollo y mantenimiento y trastienda

(Las guías de desarrollo y la documentación están ahora en «Ayuda»: ver la sección 24.)

- [ ] Como **superadmin**: «Desarrollo y mantenimiento» es la última sección del menú y tiene dos
  subsecciones (Pruebas y Trastienda).
- [ ] «Trastienda»: el botón lleva al panel de Django; las fichas tienen Guardar, Guardar y continuar,
  Cancelar y Eliminar.
- [ ] Como **Nutria**: no ve «Desarrollo y mantenimiento» (ni siquiera en desarrollo). Entrar a mano en
  `/mantenimiento/trastienda/` da la pantalla 403 que explica.

## 2. Audiencias (quién ve cada cosa)

- [ ] Como **Lince**: «Administrar → Mi organización → Visibilidad» muestra ORG Tajo con su altura máxima, «toda la
  organización» y «público», cerrados de entrada, y una frase que lo resume.
- [ ] Cambia la altura máxima y guarda: al convocar un evento en GRU Henares, el desplegable «Quién lo
  ve» ofrece más o menos niveles por encima del grupo según esa altura.
- [ ] Algo personal (un proyecto personal de Nutria) no lo ve **ni el superadmin** (ni en listas ni
  entrando por su dirección).

## 3. Menú en tres niveles e importación masiva

- [ ] El menú izquierdo tiene sección y subsección; arriba salen las vistas de la subsección. Al entrar
  por una dirección, la sección se abre sola y la subsección queda marcada.
- [ ] Como **superadmin**, «Desarrollo y mantenimiento → Pruebas → Importar grupos»: descarga la plantilla .ods, ábrela con
  LibreOffice (instrucciones y desplegables), añade dos grupos (uno dentro de otro) y súbela.
- [ ] La vista previa marca los errores por fila; no se crea nada hasta «Confirmar», y luego todo de
  golpe.
- [ ] «Importar usuarios» se niega mientras «Permitir el alta masiva de usuarios» está apagado.

## 4. Datos de ejemplo desde la pantalla

- [ ] Como **superadmin**, «Desarrollo y mantenimiento → Pruebas → Datos de ejemplo»: muestra cuántos hay de cada cosa; «Borrar»
  pide confirmación y deja al superadmin; «Crear» los vuelve a poner. (Si los borras aquí, repite el
  paso 0.4.)

## 5. Bóveda y sección «Usuarios» del superadmin

- [ ] «Usuarios → Bóveda → Personas»: alta provisional de una persona (nombre y correo), corregir sus
  datos y validarla: al validar, el correo desaparece y queda marcada como pase emitido.
- [ ] «Dominios permitidos» por organización; también se ven en la ficha de la organización, con la nota
  de que se guardan en la bóveda.
- [ ] «Alias»: la lista con origen y asamblea base; la ficha de un alias con sus grupos, activar y hacer
  superadmin.

## 6. Etiquetas

- [ ] Como **Lince**, «Administrar → Mi organización → Etiquetas»: crear «  #REUNIÓN   general» la guarda como «Reunion
  general» (primera en mayúscula, sin tildes; la ñ se queda).
- [ ] Palabras relacionadas: buscar por una relacionada encuentra la etiqueta.
- [ ] Fusionar dos marcadas en una; borrar una.
- [ ] Como **Zorro** (ORG Ebro), las etiquetas de ORG Tajo no se sugieren nunca; las comunes sí.

## 7. Tipologías

- [ ] Como **Lince**, «Administrar → Mi organización → Tipologías → De eventos»: el árbol común (Reunión, Acción,
  Recaudatorio, Genérico) y el subtipo propio «Acción de barrio».
- [ ] Un subtipo muestra los campos heredados (con borde de puntos) y los suyos; los suyos se ordenan
  arrastrando por el asa ⠿ y el orden se queda al recargar.
- [ ] Un tipo común no se puede cambiar (lo dice al intentarlo); uno propio, sí.

## 8. Organizaciones y grupos

- [ ] Como **Nutria**, «Mis grupos»: GRU Henares y GRU Lozoya en árbol, con los grupos que los contienen.
- [ ] Como **Lince**, «Árbol» de ORG Tajo; ficha de GRU Henares: miembros, admins y subgrupos; admitir,
  cambiar el rol, crear un subgrupo, editar y mover.
- [ ] «Relaciones» (colabora con…) e «Invitaciones (N)»: el número del menú baja al responder una.

## 9. Iconos del menú

- [ ] Cada sección y subsección tiene su icono y su color, y no se repite ninguno.

## 10. Roles y permisos

- [ ] Como **superadmin**, «Usuarios → Roles y permisos → Roles»: crear un rol personalizado y marcar
  sus permisos (casillas por módulo). Un rol que alguien tiene no se puede borrar.
- [ ] «Excepciones»: dar a Nutria un permiso suelto en GRU Henares, con motivo.
- [ ] «Explicar un permiso»: elige Nutria, el permiso y el grupo; el razonamiento dice por qué sí o no
  (y la excepción aparece en él).

## 11. Lo que configura cada organización (cierre de la fase 1)

- [ ] «Administrar → Mi organización» agrupa, como pestañas, Datos, Visibilidad, Tipologías, Etiquetas,
  Apoyos y plazos, Lugares y Web pública (cada una solo para quien tiene su permiso). Los niveles de aviso
  y la limpieza están en «Plataforma» (solo el superadmin).

## 12. Notificaciones

Necesita el trabajador (paso 0.5).

- [ ] Como **Lince**, admite a alguien en GRU Henares: a esa persona le llega «te han admitido» en unos
  segundos y el número de «Comunicaciones → Notificaciones (N)» sube al navegar.
- [ ] Bandejas por origen; abrir una notificación la marca vista y lleva a su enlace; papelera;
  «Marcar todas como vistas» y «Limpiar las vistas».
- [ ] «Configuración de mi cuenta → Avisos que recibo»: desactiva un tipo y comprueba que ese aviso ya no
  llega.

## 13. Avisos y conversaciones con la administración

- [ ] Como **superadmin**, «Plataforma → Catálogos comunes → Niveles de aviso»: Información, Atención y Problema con su
  color; uno usado no se borra.
- [ ] Como **Lince**, «Avisos de la administración»: aviso de nivel «Atención» a GRU Henares con «Se
  puede responder». A Nutria le llega con borde de color y un enlace para responder.
- [ ] Como **Nutria**, «Con la administración → Escribir a la administración» (la de GRU Henares).
  Lince la ve en su buzón; al responder firma «Admin de GRU Henares (Lince)»; los mensajes nuevos
  aparecen solos en unos 10 segundos; cambia el estado a «Solucionada».

## 14. Solicitudes con apoyos

- [ ] Como alguien de fuera, pide «Entrar en un grupo» a GRU Henares. Sale en «Comunicaciones →
  Solicitudes → Para apoyar (N)» de sus miembros, y en «Administrar → Por aprobar (N)» de Lince.
- [ ] Hacen falta el sí de la administración (Lince) y 2 apoyos; los apoyos se ven con alias y los
  rechazos solo como número. El sí del superadmin basta solo.
- [ ] «Administrar → Mi organización → Apoyos y plazos»: apoyos y días por plataforma y por organización.

## 15. Lugares

- [ ] Como **Nutria**, «Configuración de mi cuenta → Mis datos → Lugar»: elegir uno (privado), proponer un lugar nuevo o un cambio.
- [ ] Como **superadmin**, «Plataforma → Catálogos comunes → Lugares → Propuestas»: se ve qué cambia antes de aceptar.
- [ ] «Organizaciones y grupos → Mapa de lugares»: el mapa de Leaflet con chinchetas agrupadas; los números de personas solo
  aparecen desde 5.
- [ ] «Importar» desde .ods o .csv en dos pasos; «Administrar → Mi organización → Lugares».

## 16. Talentos

- [ ] Como **Nutria**, «Configuración de mi cuenta → Mis datos → Talentos»: «Furgoneta», compartida con GRU Henares; compártela también con
  GRU Lozoya.
- [ ] «Organizaciones y grupos → Mis grupos → Talentos de mis grupos»: solo números, nunca alias.
- [ ] Como **Lince**, «Peticiones → Pedir talentos» a GRU Henares (Furgoneta, 1). A Nutria le llega
  el aviso; «Lo ofrezco» muestra su alias solo a la administración; «Tengo dudas» abre una conversación.

## 17. Eventos

- [ ] Como **Nutria**, «Mis eventos → Convocar»: grupo, tipo (los campos cambian según la tipología),
  visibilidad, cartel. La ficha muestra el cartel solo a quien ve el evento.
- [ ] Una **Reunión** queda «pendiente de apoyos» y crea una solicitud (2, 5 o 10 apoyos según la
  altura); al aceptarse, se convoca sola y avisa.
- [ ] «¿Vas a ir?»: todos ven el número; los alias, solo quien convoca y quien tiene un cometido.
- [ ] Editar, compartir en redes y cancelar (llega el aviso de cancelación).

## 18. Calendario

- [ ] «Calendario y eventos → Calendario»: mes, semana, día y lista (en el móvil, lista). Cada tipo con su
  color y casillas arriba para ocultarlo; al recargar, los filtros se recuerdan.
- [ ] Arrastra un evento tuyo a otro día: se guarda. Uno ajeno no se puede arrastrar.
- [ ] Pulsa un hueco: abre «Apuntar un recordatorio» con ese día. «Solo yo», «Mi grupo» y, como Lince,
  hasta el padre o el abuelo.
- [ ] «Suscripción»: copia la dirección .ics y ábrela en otra ventana sin sesión: descarga el
  calendario. «Cambiar la dirección» y la vieja deja de funcionar.
- [ ] Las fechas límite de proyectos y tareas salen como días enteros y se arrastran.

## 19. Series de eventos y tareas diarias

- [ ] Al convocar, en «¿Se repite?» elige «Cada semana» hasta dentro de dos meses: se crean las veces de los
  próximos 90 días, cada una con su ficha, a la misma hora de aquí aunque cambie el horario de verano.
- [ ] «Calendario y eventos → Mis eventos → Series»: la ficha de la serie; cambia la hora: las veces futuras sin tocar cambian
  y una que hayas editado a mano se queda como estaba.
- [ ] «Terminar la serie»; una serie de reuniones pide **una sola** solicitud de apoyos.

## 20. Proyectos y tareas

- [ ] Como **Nutria**, «Tareas y proyectos → De mis grupos»: «Huerto comunitario» › «Riego» › «Bomba solar»
  sangrados en árbol.
- [ ] La ficha: camino desde el principal, datos, subproyectos, tareas y cometidos (coordinación,
  documentación, comunicación). «+ Subproyecto» y «Cambiar estado».
- [ ] Como **Garza** (GRU Sorbe): ve el huerto pero no puede gestionarlo; como **Lince** (admin de GRU
  Henares), sí.
- [ ] Kanban del huerto: incluye las tareas de los subproyectos; arrastra una tuya de columna y recarga:
  sigue allí. Las de otra persona no se arrastran.
- [ ] «Tareas y proyectos → Tareas» en kanban y en lista. Encargar una tarea a Garza (por su alias): le llega el aviso.
- [ ] «Personales»: un proyecto personal con subproyecto; no lo ve nadie más, ni el superadmin.

## 21. Limpieza (archivo y borrado)

- [ ] Como **superadmin**, «Plataforma → Limpieza»: los plazos de cada tipo (30 días para archivar,
  365 para borrar; notificaciones 90 y 365). Cambia uno y vuelve «De partida».
- [ ] Prueba rápida: crea un proyecto «Prueba», ponlo en «Finalizado» y ejecuta las dos órdenes de
  abajo (hacen como si hubiera terminado hace 40 días y pasan la limpieza). Desaparece de la lista y
  está en «Configuración de mi cuenta → Archivo → Archivados», con su ficha marcada «Archivado el…».

```bash
# Hace como si el proyecto «Prueba» se hubiera finalizado hace 40 días
python manage.py shell -c "from django.apps import apps; from django.utils import timezone; from datetime import timedelta; apps.get_model('proyectos','Proyecto').objects.filter(titulo='Prueba').update(terminado=timezone.now()-timedelta(days=40))"
# Pasa la limpieza ahora (las tareas diarias se pueden repetir)
python manage.py tareas_diarias
```

- [ ] A quienes lo ven les llega «Se ha archivado un elemento que ves».
- [ ] «Conservar»: queda «conservado por…» y ya no tiene fecha de borrado. Como superadmin, «Dejar de
  conservar» y «Borrar ya»: aparece en «Configuración de mi cuenta → Archivo → Borrados» como poda a mano.
- [ ] Reabrir un proyecto archivado (cambiar su estado) lo devuelve a la lista.

## 22. Dependencias entre tareas y recursos

- [ ] Kanban del huerto: «Elegir el panel» está en «Bloqueada» porque espera a «Presupuesto de tuberías».
  Intenta sacarla: sale el mensaje «espera a…» y vuelve a su sitio.
- [ ] Arrastra «Presupuesto de tuberías» a «Hecha»: el tablero se recarga solo y «Elegir el panel» pasa
  a «Pendiente»; a su responsable le llega «Ya puedes ponerte con…».
- [ ] Devuélvela a «En curso»: «Elegir el panel» vuelve a bloquearse.
- [ ] Ficha de una tarea: «Espera a» y «La esperan»; en «Cambiar», las casillas con las tareas del
  árbol. Hacer que una espere a otra que ya la espera dice «se formaría un círculo».
- [ ] Ficha del huerto, «Recursos»: tres de ejemplo («Herramientas de cavar», ya conseguido, tachado).
  Apunta uno, márcalo como conseguido y quítalo.
- [ ] Como **Lince**: «Pedir al grupo» en «Mangueras» crea una petición de talentos «Huerto comunitario:
  Mangueras» (4) y el recurso enlaza a ella. Como **Nutria** ese botón no sale.

## 23. Etiquetas de proyectos y tareas modelo

- [ ] El huerto lleva #Huerto y #Barrio en la lista y en la ficha; pulsar una filtra la lista («ver
  todos» lo quita).
- [ ] Editar el proyecto: el selector de etiquetas con sugerencias de ORG Tajo; añade una y guarda.
- [ ] Un proyecto **personal** no tiene campo de etiquetas.
- [ ] Como **superadmin**, «Administrar → Mi organización → Tipologías → De proyectos → Preparación de acción»: tres
  tareas modelo (pedir permiso, preparar el material, difundir), con sus días y «espera a la anterior».
  Como Lince, en un subtipo propio salen como heredadas y se le pueden añadir otras.
- [ ] Nuevo proyecto de «Preparación de acción» con la casilla «Crear las 3 tareas modelo» marcada: las
  tres se crean con fecha límite, la primera pendiente y las otras dos bloqueadas en cadena. Sin la
  casilla, no se crea ninguna.

## 24. Menú en un solo fichero, sección «Ayuda» y panel de ayuda

Antes: `npm run construir` (hay clases nuevas: ver 0.2; si `static/generado/estilos.css` no contiene
`panel-abierto`, no está hecho) y reiniciar el servidor (hay un módulo nuevo, `ayuda`; no tiene tablas).

- [ ] En el bloque de lo propio, las dos últimas secciones son «Ayuda» y «Configuración de mi cuenta»
  (antes «Mi cuenta»); como **superadmin**, «Desarrollo y mantenimiento» es la última de «Plataforma» (ver
  la sección 26).
- [ ] «Ayuda» tiene, por este orden, «How to?», «Documentación de la plataforma» (pestañas Tutorial,
  Arquitectura, Arranque y tests, Registro y validación) y «Guía de desarrollo» (Comprobaciones pendientes,
  Diseño y decisiones).
- [ ] Mover una entrada del menú: en `config/menu.py`, cambia de sitio una línea (por ejemplo, sube
  `"usuarios.cuenta"` al principio), guarda y recarga: el menú cambia. Escribe mal un código y
  `python manage.py check` dice qué pasa. Déjalo como estaba.
- [ ] Arriba a la derecha, junto al ☀/☾, hay un **?** rojo. Al pulsarlo salen las subsecciones de la ayuda
  y, debajo de las que tienen varias, sus pestañas.
- [ ] Elige «Tutorial»: se abre un panel a la derecha y la pantalla principal se estrecha. En el panel,
  arriba, las pestañas de la documentación y «Abrir en grande ↗».
- [ ] Con el panel abierto, navega con el menú de la izquierda y con las pestañas de arriba: solo cambia
  la pantalla principal; el panel se queda donde estaba (no vuelve arriba ni parpadea).
- [ ] En el panel, pulsa otra pestaña (Arquitectura): cambia el panel y no la pantalla principal. Los
  diagramas se dibujan dentro del panel.
- [ ] Arrastra la línea que separa el panel: cambia el ancho y la pantalla principal se adapta. Si lo
  ensanchas mucho, la pantalla principal no se estrecha más y sale una barra de desplazamiento abajo.
  Doble clic en la línea: vuelve al ancho de partida. Con la línea seleccionada (tabulador), las flechas
  ← y → también lo cambian.
- [ ] Recarga la página: el panel sigue abierto, con la misma página y el mismo ancho, sin saltos. Ciérralo
  con ✕ y recarga: sigue cerrado.
- [ ] El **?** gris junto al título de una sección sigue abriendo su **ventana emergente** (no el panel).
  En «Ayuda → How to?», la ventana trae además un recuadro «Ejemplo».
- [ ] En el panel, los botones **−** y **+** achican y agrandan la letra del panel (no la de la pantalla
  principal), del 70 % al 160 %; nada se sale de lado (prueba con «Tutorial», que tiene rutas largas).
  Se recuerda al recargar.
- [ ] «Abrir en grande ↗» lleva la página del panel a la pantalla principal.
- [ ] En un documento, el botón **▸ Índice** pliega y despliega el índice, y se recuerda al recargar. En
  el panel sale plegado de entrada; en la pantalla principal, desplegado. Con el panel abierto y la
  pantalla principal estrecha, el índice del documento principal se pone encima del texto.
- [ ] En el panel, pulsar un título del índice baja hasta él dentro del panel.
- [ ] Las casillas de «Comprobaciones pendientes» son las mismas en el panel y en la pantalla principal
  (marcadas antes de este cambio puede que salgan sin marcar: cambió la dirección de la página).
- [ ] En el móvil (o con la ventana muy estrecha), el panel ocupa toda la pantalla y se cierra con ✕.
- [ ] En el tutorial, el apartado de los mapas muestra «`<script>`» como texto (antes se colaba como
  etiqueta).
- [ ] Como en producción: para el servidor (Ctrl+C) y arráncalo así; entra como **Nutria**: el ? rojo
  solo ofrece «How to?» y `/ayuda/tutorial/` da la pantalla 403 que explica. Al terminar, vuelve a
  arrancarlo como siempre.

```bash
# Arranca el servidor como en producción solo para la ayuda (sin abrir la documentación a todo el mundo)
#     DJANGO_GUIAS_PARA_TODOS=0: la documentación de la plataforma y la guía de desarrollo, solo para el superadmin
#     runserver: servidor web de Django para desarrollo
#     0.0.0.0:8000: escucha en todas las direcciones del contenedor, en el puerto 8000
DJANGO_GUIAS_PARA_TODOS=0 python manage.py runserver 0.0.0.0:8000
```

## 25. Selector de personas en las tareas

Antes: `npm run construir` (hay clases nuevas; ver 0.2) y reiniciar el servidor.

- [ ] Como **Nutria**, «Tareas y proyectos → Proyectos → Huerto comunitario» → nueva tarea. En «Responsable», pulsa
  **Elegir…**: sale «Elegir una persona» con «Aquí: GRU Henares» (Lince con «admin», Nutria con «tú»)
  desplegado y con más color, y debajo los bloques más lejanos, plegados y más suaves, cada uno con su
  número de personas.
- [ ] Nadie de ORG Ebro sale nunca, ni nadie de un grupo que no vea el proyecto.
- [ ] Escribe en el buscador parte de un alias o de un grupo (prueba «sorbe» o «garz», sin tildes): filtra
  al momento, despliega los bloques con coincidencias y oculta el resto. Sin coincidencias, lo dice.
- [ ] Pulsa una persona: la ventana se cierra y queda su pastilla en «Responsable». La × la quita.
- [ ] En «Colaboran», marca dos personas: abajo pone «2 elegidas»; «Listo» las deja como pastillas.
  Crea la tarea y en su ficha salen la responsable y las colaboradoras.
- [ ] En la ficha de una tarea, al cambiarla, el selector sale con las personas que ya tenía.
- [ ] Una tarea suelta nueva («Tareas y proyectos → Tareas → Nueva» en un grupo): cambia «Quién la ve» a «Hasta el grupo
  padre» y vuelve a abrir el selector: aparece el bloque «Un nivel por encima».
- [ ] Como **Lince**, en «Administrar → Grupos que administro → Árbol», pulsa ORG Tajo y desmarca «Los miembros ven la
  lista de miembros de sus grupos». Como **Nutria**, el selector ya no enseña la lista: pide el alias exacto. Escribe uno de otra
  organización (por ejemplo, «Zorro») y crea: dice «No está entre quienes ven esto: Zorro.» (el mismo
  mensaje que con un alias que no existe). Como Lince, sigue viendo la lista. Vuelve a dejarlo como estaba.

## 26. Menú en tres bloques

Antes: `npm run construir` (hay clases nuevas; ver 0.2) y reiniciar el servidor (hay un módulo nuevo,
`proximamente`; no tiene tablas).

- [ ] Como **Nutria** (sin nada que administrar): el menú tiene un solo bloque, sin título: Inicio,
  Calendario y eventos, Comunicaciones, Tareas y proyectos, Participación, Organizaciones y grupos, Ayuda y
  Configuración de mi cuenta. No sale «Administrar» ni «Plataforma».
- [ ] «Inicio»: pestañas «Panel» y «Mis datos», que dicen que aún están vacías y qué tendrán.
- [ ] «Calendario y eventos»: no se despliega a la izquierda; arriba, las pestañas Calendario · Eventos de
  mis grupos · Mis eventos · Convocar. En «Eventos de mis grupos» y «Mis eventos», una segunda fila más
  pequeña (Próximos · Pasados; Mis eventos · Series). El calendario tiene los botones «+ Recordatorio»,
  «Mis recordatorios» y «Suscripción». Al abrir uno de ellos, el menú sigue marcando «Calendario y eventos».
- [ ] «Comunicaciones»: Notificaciones; Conversaciones (pestañas: Con la administración · Con grupos · Con
  personas, estas dos vacías); Solicitudes (pestañas: Enviadas · Para apoyar · Peticiones de talentos ·
  Histórico). En «Con la administración» solo salen tus conversaciones.
- [ ] «Tareas y proyectos»: «Tareas» abre el kanban (la lista es la segunda pestaña). Al entrar en una
  tarea, el menú sigue marcando «Tareas» (antes saltaba a la sección); al entrar en un proyecto,
  «Proyectos».
- [ ] «Participación»: Debates, Consultas, Órdenes del día y actas y Decisiones, todas vacías.
- [ ] «Organizaciones y grupos»: «Mis grupos» (pestañas: Árboles · Grafo (vacía) · Relaciones · Talentos de
  mis grupos) y «Mapa de lugares».
- [ ] «Configuración de mi cuenta», con submenús a la izquierda: Usabilidad, Mis datos (pestañas: Datos
  (vacía) · Talentos · Lugar), Avisos que recibo, Contraseña y Archivo (pestañas: Archivados · Borrados).
- [ ] Como **Lince** (admin de GRU Henares y de ORG Tajo): debajo sale el bloque «ADMINISTRAR», con su título
  y una franja ámbar: Grupos que administro (Árbol · Miembros · Invitaciones entre grupos), Buzón de la
  administración (Conversaciones que atiendo · Avisar), Por aprobar, Eventos y talentos (Eventos de mis grupos
  · Pedir talentos), Moderación (vacía) y Mi organización (Datos · Visibilidad · Tipologías ·
  Etiquetas · Apoyos y plazos · Lugares · Web pública (vacía)).
- [ ] En cualquier pantalla de «Administrar», arriba sale la banda ámbar «Estás administrando…».
- [ ] Una conversación de Nutria con la administración de GRU Henares: Lince la ve en «Administrar → Buzón de
  la administración», no en sus conversaciones propias. Al abrirla, «← Conversaciones» vuelve al buzón.
- [ ] Una solicitud para entrar en GRU Henares: a Nutria le sale en «Para apoyar» (con Apoyar/Rechazar, sin
  «Dar el sí»); a Lince, además, en «Administrar → Por aprobar» (con «Dar el sí de la administración», sin
  Apoyar). Cada una con su número en el menú.
- [ ] «Mi organización → Datos»: ORG Tajo con el enlace a su ficha (ahí se cambian sus datos).
- [ ] Los números del menú: «Grupos que administro (N)» suma sus pestañas (las invitaciones pendientes), y
  la pestaña lleva también el suyo.
- [ ] Como **superadmin**: además, el bloque «PLATAFORMA» con franja roja: Usuarios, Catálogos comunes
  (Lugares · Talentos · Niveles de aviso), Limpieza y Desarrollo y mantenimiento (con Pruebas, Trastienda y
  Componentes, la demostración que antes estaba en Inicio). Su banda es roja.
- [ ] Mover algo de sitio: en `config/menu.py`, mueve una línea (por ejemplo, `"lugares.mapa"` dentro de
  «Calendario y eventos», como pestaña), recarga y mira el cambio. Déjalo como estaba.


## 27. Árboles de grupos

Antes: `npm run construir` (hay clases nuevas; ver 0.2). No hace falta migrar.

- [ ] Como **Nutria**, «Organizaciones y grupos → Mis grupos → Árboles»: un recuadro por organización. Arriba,
  «ORG Tajo» en una etiqueta violeta; debajo, GRU Tajo y GRU Jarama en gris «(por herencia)», GRU Henares con
  fondo amarillo y «asamblea base», y GRU Lozoya. Cada grupo cuelga del suyo con una raya a la izquierda.
- [ ] No salen grupos que Nutria no ve (por ejemplo, GRU Manzanares, hermano de GRU Henares).
- [ ] Debajo, la leyenda: Organización · Tu asamblea base · En gris. Sin «El grupo que miras».
- [ ] Pulsa un grupo: lleva a su ficha. Arriba de la ficha, el árbol de ORG Tajo con ese grupo en un
  **recuadro rojo** (y GRU Henares sigue en amarillo); la leyenda explica también el recuadro rojo. El
  camino («ORG Tajo › GRU Tajo › …») sigue encima.
- [ ] Como **Lince** (en ORG Tajo y en ORG Ebro): dos árboles, uno al lado del otro (en pantalla ancha caben
  tres por fila). En GRU Henares, «Admin del grupo»; GRU Sorbe cuelga debajo. «ORG Tajo» lleva a la ficha de
  la organización (Lince la administra) y al lado dice «eres admin de la organización».
- [ ] Como **Zorro** (admin de ORG Ebro): toda ORG Ebro, con «administras (y lo de debajo)» solo en GRU Ebro, no
  en cada grupo.
- [ ] Como **superadmin**: «Aún no estás en ningún grupo…»; en la ficha de cualquier grupo, el árbol enseña
  el camino hasta él, con el recuadro rojo.
- [ ] Con el tema oscuro (☾), los colores se siguen leyendo (amarillo, violeta y rojo más apagados).
- [ ] En el móvil (o la ventana estrecha), los árboles van uno debajo de otro.

## 28. Inicio: Panel y Mis datos

Antes: `npm run construir` (hay clases nuevas; ver 0.2) y reiniciar el servidor (hay ficheros nuevos que
se leen al arrancar: `config/inicio.py` y los `inicio.py` de los módulos). No hace falta migrar.

- [ ] Como **Nutria**, «Inicio → Panel»: arriba, dos recuadros, «Comunicaciones» y «Solicitudes»; cada uno
  partido en «Recibidas» y «Enviadas». Debajo, «Mis proyectos abiertos» con Riego, Huerto comunitario y
  Bomba solar, su estado, su grupo y, si tiene, «hasta el …». Pulsa uno: va a su ficha.
- [ ] Como **Garza**, pide entrar en GRU Henares («Comunicaciones → Solicitudes → Enviadas → Pedir
  algo»). En el panel de Garza sale en «Solicitudes → Enviadas»; en el de **Nutria**, en «Recibidas, para
  apoyar (1)», con un punto de color. Al apoyarla, desaparece de su panel.
- [ ] Como **Nutria**, escribe a la administración de GRU Henares: sale en «Comunicaciones → Enviadas, sin
  resolver». Como **Lince**, contéstala desde «Administrar → Buzón de la administración». Como **Nutria**:
  ahora sale en «Recibidas» («respuesta de la administración», con punto) y ya no en «Enviadas».
- [ ] Cada recuadro tiene arriba su botón («Ir a comunicaciones», «Ir a solicitudes», «Ir a proyectos»).
  Si un apartado tiene más de 5 (8 en proyectos), sale «Ver todas (N)».
- [ ] «Inicio → Mis datos»: «Datos públicos» (alias y fecha), «Mis talentos», «Datos privados» (correo,
  cómo se creó la cuenta y el tema, la letra y la densidad) junto a «Mi lugar», y «Mis grupos» con el
  árbol (asamblea base en amarillo, rol junto a cada grupo). Cada recuadro con «Editar»; el de los grupos,
  «Pedir entrar en un grupo».
- [ ] «Editar» de los datos lleva a «Configuración de mi cuenta → Mis datos → Datos» (antes vacía): una tabla
  con cada dato, su valor, quién lo ve y cómo se cambia. Cambia el correo alternativo y guarda: sale
  «Guardado.» y el correo nuevo aparece en Inicio → Mis datos. Un correo mal escrito da un error.
- [ ] El «?» gris de «Mis datos» (en Configuración de mi cuenta) explica sus tres pestañas.
- [ ] En el móvil, los recuadros van uno debajo de otro.
- [ ] Mover un recuadro: en `config/inicio.py`, pon `"lugares.mi_lugar"` en la primera fila de
  `"mis_datos"`, reinicia el servidor y mira el cambio. Déjalo como estaba. Si dejas una tarjeta sin
  colocar, `python manage.py check` da el error `base.E007`.

## 29. Árboles de proyectos

Antes: `npm run construir` (hay clases nuevas; ver 0.2). No hace falta migrar.

- [ ] Como **Nutria**, «Tareas y proyectos → Proyectos → De mis grupos»: un recuadro por proyecto principal
  (en pantalla ancha caben tres por fila). Arriba, «GRU Henares» en una etiqueta verde y «ORG Tajo» al lado.
  Huerto comunitario, Riego y Bomba solar cuelgan uno de otro con rayas a la izquierda.
- [ ] Los proyectos en los que Nutria participa tienen el fondo amarillo. Los finalizados salen en gris.
- [ ] Junto a cada proyecto con tareas, «(hechas/totales)» y una flecha ▸. Al pulsar la flecha (o la
  línea, fuera del título), se despliegan sus tareas: estado y responsable; las hechas, tachadas. La flecha
  gira. Al pulsar el título se va a la ficha del proyecto.
- [ ] Las etiquetas (#Barrio…) siguen saliendo y filtran la lista.
- [ ] «Personales»: los proyectos personales, también en recuadros, con la etiqueta «Personal» arriba.
- [ ] Ficha de **Riego**: arriba, el camino («Proyectos › Huerto comunitario › Riego») y debajo el árbol
  entero de Huerto comunitario, con Riego en un **recuadro rojo**. La leyenda explica también el rojo. Ya
  no hay listas aparte de subproyectos y de tareas (lo dice el árbol); «+ Tarea» está junto a «Kanban».
- [ ] En el móvil, los recuadros van uno debajo de otro.

## 30. Ficha de una tarea: camino y cambiar sobre lo escrito

Antes: `npm run construir` (hay clases nuevas; ver 0.2) y reiniciar el servidor. No hace falta migrar.

- [ ] Como **Nutria**, abre una tarea de **Bomba solar** (dentro de Riego, dentro de Huerto comunitario).
  Arriba: «Tareas › Huerto comunitario › Riego › Bomba solar › la tarea», con los tres proyectos en
  violeta; cada uno lleva a su ficha.
- [ ] Una tarea suelta de un grupo: el camino lleva el grupo, en verde. Una personal: «Personales».
- [ ] Pulsa el **título**: se convierte en un cuadro con el título de ahora. Cámbialo y pulsa Intro: se
  guarda sin recargar la página (el resto no parpadea). Recarga: sigue cambiado.
- [ ] Lo mismo con el **estado** (un desplegable), la **fecha** (si la tiene) y la **descripción** (si la
  tiene). Escape o «Cancelar» lo dejan como estaba.
- [ ] Borra el título entero y guarda: sale un error en rojo y el cuadro sigue abierto.
- [ ] El ✎ junto a la responsable (o a «Colaboran» o «Espera a») abre «Completar o cambiar todo» y baja
  hasta él. Dentro, todos los valores de ahora ya escritos.
- [ ] Una tarea sin fecha: «Para el» no sale arriba; se pone en el desplegable.
- [ ] Como alguien que ve la tarea pero no puede cambiarla (ni es responsable, ni colabora, ni gestiona
  el proyecto): los datos no se pueden pulsar y no sale el desplegable.

## 31. Árbol de tipologías con el aspecto de los demás árboles

Antes: `npm run construir` (ver 0.2) y reiniciar el servidor.

- [ ] Como **Lince**, «Administrar → Mi organización → Tipologías → De proyectos»: arriba del árbol, «Tipos
  de proyectos» en violeta; los subtipos cuelgan de su tipo con rayas a la izquierda.
- [ ] Crea un subtipo de ORG Tajo («+ Nuevo tipo o subtipo»): sale en amarillo (lo puedes cambiar); los
  comunes, sin fondo.
- [ ] Pulsa un tipo: queda con el recuadro rojo y a la derecha salen sus campos, como antes.
- [ ] Como **superadmin**: todos los tipos en amarillo (los puede cambiar todos).
- [ ] «De eventos»: igual, con «Tipos de eventos».

## 32. Grafo de grupos

Antes: reiniciar el servidor (cambia interfaz.js: recarga la página con Ctrl+F5).

- [ ] Como **Lince**, «Organizaciones y grupos → Mis grupos → Grafo»: una caja violeta por organización
  (ORG Tajo y ORG Ebro), con sus grupos unidos por flechas. GRU Henares en amarillo; lo que administra, con
  borde ámbar; los grupos de más arriba, en gris.
- [ ] Las relaciones de «Relaciones» salen como flechas de puntos con su texto.
- [ ] Botones + − ⤢ ⛶: acercan, alejan, ajustan y ponen a pantalla completa. Se puede arrastrar.
- [ ] Al pulsar un grupo se va a su ficha (al arrastrar el dibujo, no).
- [ ] Como **Nutria**: solo su rama (GRU Tajo › GRU Jarama › GRU Henares y GRU Lozoya).

## 33. Participación: lo común («Cuelga de aquí»)

Antes: migrar (0.3: hay cuatro módulos nuevos), rehacer los ejemplos (0.4: ahora traen un orden del día,
un acta aprobada, un debate y una consulta), `npm run construir` (0.2) y reiniciar el servidor y el
trabajador (0.5: hay una tarea diaria nueva, `consultas.cerrar`).

- [ ] El menú «Participación» tiene Debates, Consultas, Órdenes del día y actas y Decisiones. Al pulsar
  «Participación» se abren los debates. Ya no dicen que están vacías.
- [ ] En la ficha de un evento o de un proyecto, abajo, el recuadro **«Cuelga de aquí»** con tres columnas
  (órdenes del día y actas, debates, consultas), cada una con su «+ …» para crear uno colgado de ahí.

## 34. Órdenes del día y actas

- [ ] Como **Nutria**, «Participación → Documentos»: el orden del día y el acta de noviembre (y
  el de diciembre en borrador). Se filtra por tipo y estado al momento.
- [ ] El acta: «sale de» su orden del día; arriba, «Registro de cambios (3)», plegado. Detrás de cada
  párrafo, en claro, «(Lince)». Abajo, los dos acuerdos («ya están en el registro de decisiones») y el tema
  pendiente con «Proponer debate» (lleva al formulario con la pregunta escrita).
- [ ] Nutria puede comentar el orden del día de diciembre, pero no escribirlo (no le sale «Escribir»).
- [ ] Como **Lince**, orden del día de diciembre → «Escribir»: el texto a la izquierda y la vista previa a la
  derecha, que cambia mientras escribes. Guarda: en la ficha, el párrafo cambiado lleva «(Lince)» y el
  registro, una línea más.
- [ ] Abre «Escribir» en dos pestañas, guarda en una y luego en la otra: la segunda avisa de que otra
  persona ha guardado (no pisa nada).
- [ ] «Dar» la redacción a Nutria: ya le sale «Escribir». Como mucho 10 personas de partida (se cambia en «Opciones»
  y en «Administrar → Mi organización → Documentos»).
- [ ] «Crear el acta desde este orden del día»: copia los puntos y añade Asistentes, Acuerdos alcanzados y
  Temas. Escribe un acuerdo «- [votación 5-2-0] …» y aprueba: ya no se puede escribir y el acuerdo sale en
  «Decisiones» con forma «Votación» y detalle «5-2-0».

## 35. Debates

- [ ] Como **Nutria**, «Participación → Debates → ¿Dónde hacemos el huerto?»: arriba, la pregunta, quién
  facilita y 🤝. Debajo, las dos clasificaciones y las tres opciones en columnas (en el móvil se deslizan).
- [ ] Cada opción y cada argumento con sus botones ⭐ 👍 👎 ⛔ (los argumentos, también 🔁 🚫) y su número.
  Pulsa 👍: se marca y suma 1; vuelve a pulsarlo: se quita. ⭐ y ⛔ piden una justificación, que sale bajo la
  opción **sin nombre**.
- [ ] Los argumentos llevan alias; «Responder» cuelga una respuesta debajo. «+ Argumento», a favor o en contra.
- [ ] «Opciones propuestas»: la de consenso de Garza espera 👍 y lo explica. Nutria (que apoyaba el solar)
  le da 👍: aún no basta. Como **Lince**, da 👍 a «En la azotea» y después a la de consenso: ahora vienen de
  opciones distintas y pasa a columna. Desde ese momento, todo el mundo vuelve a tener sus intervenciones.
- [ ] Como **Lince** (facilita): «Dar la facilitación», «Ampliar a» (solo opciones más amplias) y «Cerrar el
  debate» con una conclusión: sale arriba en verde y en «Decisiones».
- [ ] «Proponer un debate»: queda «esperando apoyos» (solo lo ves tú) y sale en «Comunicaciones →
  Solicitudes»; cuando lo apoyan dos personas del grupo, se abre.
- [ ] Como **Zorro** (admin de ORG Ebro) o **superadmin**: «Administrar → Mi organización → Debates», los
  límites. Pon 1/3 intervenciones: tu segundo argumento sale marcado en ámbar («pasado del límite») y el
  tercero ya no se publica.
- [ ] Como **Lince** (admin de GRU Henares): «Administrar → Mi organización → Debates» deja elegir «Grupo:
  ORG Tajo › … GRU Henares». Pon 300 palabras de límite duro: debajo dice cuánto vale ahora en ese grupo,
  juntando niveles.
- [ ] Como Lince, en la ficha de «¿Dónde hacemos el huerto?» (facilita), «Límites de este debate»: pon 5
  palabras de límite duro. Un argumento de más de 5 palabras ya no se publica. Como **Nutria** (no
  facilita), ese recuadro no sale.

## 36. Consultas y decisiones

- [ ] Como **Nutria**, «Inicio → Panel»: «Consultas por votar» con «¿Qué día hacemos la asamblea?».
- [ ] La consulta: vota. Se puede cambiar el voto (lo dice); vota otra vez y cambia. En una consulta sin
  cambio de voto, sale el aviso en ámbar y te pide confirmar antes de votar.
- [ ] Los resultados dicen «se verán al cerrar». En el calendario sale «Cierra: ¿Qué día…?».
- [ ] Arriba de la consulta, en verde, «🔒 Voto secreto» con la explicación. Crea otra (como Lince) sin
  marcar «voto secreto»: sale en ámbar «👁 Voto público» y, en los resultados, debajo de cada respuesta,
  los alias de quien la ha votado.
- [ ] Como **Lince** (admin de GRU Henares), «Nueva consulta»: al elegir «En una fecha» sale la fecha de
  publicación; «En tiempo real», el aviso de que influye. Créala con la apertura en el futuro y añade
  preguntas (única, múltiple, abierta); se pueden quitar hasta que se abra.
- [ ] Cuando se cierre (o pon el cierre en el pasado en la trastienda y abre la ficha): resultados en
  barras; el desglose por grupos solo con 10 votos o más; y el resultado en «Decisiones».
- [ ] Como **Garza** (miembro, sin administrar), «Nueva consulta»: el botón dice «Proponer». En su ficha le
  pones preguntas y «Pedir apoyos al grupo»; la ficha dice «Esperando los apoyos» y las preguntas ya no se
  cambian. Como **Nutria**, no la ves en la lista, pero sí en «Comunicaciones → Solicitudes», con las
  preguntas. Con dos apoyos se abre y ya se vota.
- [ ] «Participación → Decisiones»: «Vigentes» y «Todas», filtrables por cómo y por grupo. En una ficha, como
  Lince, «Sustituida por…» otra más nueva: sale de «Vigentes» y sigue en «Todas», con el aviso en ámbar.

## 37. Editor en tiempo real (actas entre varias personas)

Necesita el paso 0.8.
- [ ] Como **Lince**, «Participación → Documentos → Orden del día de la asamblea de
  diciembre» y «Escribir». Arriba sale «En directo» y tu alias en color; a la izquierda, el cuadro; a la
  derecha, la vista previa, que cambia mientras escribes.
- [ ] En otro navegador (o en una ventana privada), entra como **Nutria** (sin redacción) y abre el mismo
  documento. En la ficha sale «Seguir en directo»: pone «No tienes la redacción: no puedes escribir, pero sí
  comentar» y ves escribir a Lince al momento, pero no puedes cambiar el texto.
- [ ] Como Lince, en la ficha, dale la redacción a Nutria. Nutria vuelve a la ficha y pulsa «Escribir»: ya
  puede escribir. Escribid los dos a la vez: cada uno ve el texto y el cursor del otro, con
  su nombre.
- [ ] Dejad de escribir unos segundos y abrid la ficha: el texto está guardado. Los párrafos que habéis
  tocado los dos dicen «(Lince, Nutria)», y el registro de cambios, «Lince, Nutria».
- [ ] Aprueba el documento como Lince: quien estaba escribiendo se desconecta y, al volver, ya no lo puede
  cambiar.
- [ ] **Barra de formato:** selecciona una palabra y pulsa **B**: queda entre `**`. Prueba el título, la
  lista y la tabla.
- [ ] **Vista Typst:** apagada, no hay panel. Al pulsarla, sale al lado el resultado compilado y se pone al
  día poco después de escribir. Vuelve a pulsarla: se esconde. «Previsualizar» la enseña una vez y «PDF»
  descarga el documento.
- [ ] **Comentarios:** como Nutria (sin redacción), selecciona un trozo y «💬 Comentar». A Lince le sale
  resaltado en amarillo; al pulsarlo, el bocadillo con el comentario. Responde y pulsa «✓ Resuelto»: el
  resalte se va. «↓ 💬» salta al siguiente.
- [ ] **Typst a mano:** «Nuevo documento» con «Se escribe en: Typst». Los botones de la barra ponen marcas
  de Typst (`*negrita*`, `== Título`) y la ficha enseña el texto tal cual.
- [ ] **Límites:** como Lince, en la ficha del documento, «Opciones» → 1 persona escribiendo. Dar la
  redacción a otra persona ya no deja. Y si dos con la redacción abren «Escribir», la segunda entra a leer,
  con un aviso arriba.
- [ ] «Administrar → Mi organización → Documentos»: los mismos límites por plataforma (superadmin),
  organización y grupo.
- [ ] **Comentarios registrados:** después de comentar en el editor, la ficha del documento tiene
  «Comentarios en el texto», con el trozo en amarillo, quién, las respuestas y si está resuelto.
- [ ] **Versiones:** en la ficha, «Versiones». Abre una anterior: a la izquierda su texto; a la derecha, lo
  que ha cambiado desde entonces (rojo, lo que se quitó; verde, lo nuevo). «Volver a esta versión» (solo
  quien redacta) cambia el texto y lo deja como otra versión; si alguien estaba en el editor, se reconecta
  y ve el texto vuelto.
- [ ] Para el editor (`docker stop` del servicio o Ctrl+C) y abre «Escribir» en otro borrador: pone
  «Conectando…». Abajo, «Escribir sin directo» abre el formulario de siempre.

## 38. Biblioteca del editor: plantillas, fragmentos, cabeceras y pies, e imágenes

Necesita el paso 0.8 (con biblioteca).
- [ ] Como **superadmin**, «Participación → Plantillas de documentos → Plantillas». «📁 Nueva carpeta»:
  solo deja llamarla **Actas** (lo dice abajo); de quién es: «Toda la plataforma». Guárdala.
- [ ] Dentro de «Actas», «＋ Nueva plantilla»: un nombre, en «Aspecto» `#set heading(numbering: "1.")`
  y en «Texto de partida» un esqueleto (`## Asistentes`, `## Orden del día`…). «Previsualizar» enseña
  cómo queda. Guárdala.
- [ ] «Imágenes»: carpeta «ORG …» (de la organización) y «Subir imagen» con un PNG. Sale en el árbol con
  su miniatura y, en su ficha, cómo ponerla en Markdown y en Typst. Prueba a subir un fichero que no sea
  una imagen: no deja.
- [ ] «Cabeceras y pies»: una nueva con la imagen en la cabecera (`#image("/imagenes/…", height: 1.2cm)`,
  copia el número de la ficha de la imagen) y un texto en el pie. «Previsualizar».
- [ ] Como **Lince** (sin administrar nada), en «Plantillas» ves la de «Actas» pero de **solo lectura**. Dentro
  de «Actas» crea tu propia plantilla: es «Solo yo». Compártela con uno de tus grupos («Compartir con…») y
  con una persona (escribe «Nut» y elige a Nutria).
- [ ] Como **Nutria**, ves la plantilla de Lince (de solo lectura). Una persona de otra organización no la ve.
- [ ] «Participación → Enciclopedia de fragmentos»: como superadmin, carpeta «Actas» y subcarpetas; como
  Lince, un fragmento tuyo («## Ruegos y preguntas»).
- [ ] En un documento **vacío**, «Escribir»: arriba salen los desplegables **Plantilla** y **Cabecera y pie**.
  Elige la plantilla: aparece su texto de partida. Elige la cabecera y pie y enciende la «Vista Typst»:
  sale con la imagen, el aspecto y el pie. Quien lo tenga abierto a la vez ve el mismo cambio.
- [ ] «📚 Fragmentos e imágenes»: pulsa el fragmento y la imagen: se meten donde está el cursor.
- [ ] Quien solo comenta o lee ve los desplegables, pero no puede cambiarlos ni meter nada.
- [ ] El cifrado: en el contenedor, `ls editor/datos/biblioteca` y `head -c 200 editor/datos/biblioteca/indice.cif`:
  no se lee ningún nombre.

## 39. Eventos: listas filtrables y los de los grupos que administro

No necesita nada especial (sin tablas nuevas).
- [ ] Como **Nutria**, «Calendario y eventos → Eventos de mis grupos»: los eventos salen en una tabla con
  fecha y hora, evento, tipo, grupo, estado y cuántos van. Prueba los desplegables (Tipo, Grupo, Estado),
  escribe una palabra y pulsa el título de una columna para ordenar. «Pasados»: lo mismo con los ya
  celebrados.
- [ ] «Mis eventos»: pestañas **Próximos · Pasados · Series**, con la columna «Mi papel» (Convoco, Voy,
  Quizá) y su filtro.
- [ ] Como **Lince** (admin de GRU Henares), «Administrar → Eventos y talentos → Eventos de mis grupos»:
  pestañas Próximos · Esperan apoyos · Pasados · Cancelados, con los eventos de GRU Henares y de sus
  subgrupos (no los de otras organizaciones).
- [ ] Como Nutria, convoca una **reunión** en GRU Henares (queda esperando apoyos). Como Lince, sale en
  «Esperan apoyos» con «0/2»; ábrela: ves la ficha aunque aún no esté convocada.
- [ ] En la ficha de un evento de su grupo que convocó otra persona, Lince ve «Editar» y «Cancelar» y ve
  cuántos van, pero **no quiénes**. Cancélalo: pasa a «Cancelados».
- [ ] Como Nutria (no administra nada), «Administrar» no sale y `/eventos/administrados/` da «No puedes».

## 40. Miembros de los grupos que administro e inactividad

Antes: `python manage.py migrate` (tabla `LimiteDeInactividad` y campo `ultima_actividad` del usuario; ver 0.3).
- [ ] Como **Lince** (admin de GRU Henares), «Administrar → Grupos que administro → Miembros»: una fila por
  persona y grupo, de GRU Henares y sus subgrupos. Las filas de un grupo que no es la asamblea base de esa
  persona salen **más tenues**. Filtra por grupo, rol, asamblea base o actividad.
- [ ] En una fila de GRU Henares: cambia el rol («Cambiar») y saca a alguien («Sacar», con confirmación).
  Arriba sale lo que ha pasado. Las filas de los subgrupos no tienen controles (el permiso de admitir es del
  propio grupo).
- [ ] **En bloque:** marca dos filas, elige «Sacar del grupo» y «Aplicar a las marcadas». Como admin de grupo
  no sale «Cambiar el rol a Admin del grupo»; como admin de la organización, sí.
- [ ] «+ Admitir a una persona»: elige grupo, alias y rol.
- [ ] **Inactividad:** en la trastienda (o con `python manage.py shell`), pon a una persona
  `ultima_actividad` de hace 45 días: en «Miembros» sale «Sin actividad (más de 30 días)». No se ve el día.
- [ ] «Administrar → Mi organización → Inactividad»: como superadmin, «Toda la plataforma» con los días y el
  mínimo. Como Lince, su grupo: no deja bajar del mínimo ni subir de los días de la plataforma. «Quitar»
  vuelve a lo de arriba.

## 41. Conversaciones con grupos y con personas

Antes: `python manage.py migrate` (tablas de las salas, conversaciones entre personas y bloqueos; ver 0.3) y
rehacer los ejemplos (0.4). El trabajador debe estar en marcha para que llegue el aviso de un bloqueo.
- [ ] Como **Nutria**, «Comunicaciones → Conversaciones → Con grupos»: sus grupos (GRU Henares, GRU
  Lozoya…), con el último mensaje y un número verde si hay nuevos. El menú dice «Con grupos (N)».
- [ ] Entra en la sala de GRU Henares: los mensajes propios a la derecha, en verde azulado. Escribe uno.
- [ ] Abre la misma sala como **Lince** en otra ventana y escribe: en la de Nutria aparece solo, en unos
  10 segundos, sin perder lo que estuviera escribiendo.
- [ ] Como **Garza** (está en GRU Sorbe, no en GRU Henares), abre la dirección de la sala de GRU Henares:
  no entra (403). Tampoco el **superadmin**.
- [ ] Como **Nutria**, «Con personas → Escribir a una persona»: «Elegir…» enseña las personas de sus grupos,
  agrupadas por grupo. Elige a una y escribe. Probando con el alias de alguien que no comparte grupo (por
  ejemplo, Zorro), dice que no compartes grupo.
- [ ] Como esa persona, el menú dice «Con personas (1)»; al abrir la conversación, baja.
- [ ] Pulsa **Bloquear** (pide confirmación): desaparece el formulario y sale «Desbloquear a …». La otra
  persona ve «Esta conversación está bloqueada» y no puede escribir; en su lista sale «Bloqueada».
- [ ] Como **superadmin**, en «Notificaciones» (bandeja «Sistema»): «X ha bloqueado a Y en las
  conversaciones entre personas». No hay forma de leer la conversación.
- [ ] «Desbloquear»: vuelven a poder escribirse.

## 42. Archivos, enlaces y papelera; documentos en tareas, debates y consultas

Antes: `python manage.py migrate` (0.3), `npm run construir` (hay clases nuevas: 0.2), rehacer los ejemplos
(0.4) y, para el antivirus, el 0.9.
- [ ] Como **Lince**, «Participación → Documentos»: salen juntos textos, el PDF «Plano del solar» y el enlace
  «Carpeta compartida del huerto». Prueba los desplegables (Tipo, Formato, Cuelga de, Grupo, Estado) y
  **«Último cambio» desde… hasta…**: las filas se esconden al momento.
- [ ] Abre «Plano del solar»: el PDF se ve dentro de la página; «Abrir» y «Descargar». Arriba dice si lo
  revisó el antivirus («sin revisar» si no hay).
- [ ] «Subir otra versión» con otro PDF: en «Versiones» salen las dos y se abre cada una.
- [ ] Botón **«Subir un archivo»**: arriba sale el aviso de Microsoft. Prueba a subir un `.docx`: no lo
  guarda y explica cómo pasarlo a PDF u odt. Renombra un `.exe` a `.pdf`: dice que no lo parece.
- [ ] **«Enlazar»**: uno a una dirección de Drive y otro a un documento de aquí (desplegable). En la ficha,
  el de fuera se abre aparte.
- [ ] En la ficha de un **debate**, de una **consulta**, de una **tarea** y de un **proyecto** sale el
  recuadro «Cuelga de aquí» con «+ Documento, archivo o enlace». Sube un PDF a una tarea del huerto: sale
  también en la ficha del **proyecto**, con «de «nombre de la tarea»».
- [ ] **Congelado:** sube un PDF a una consulta que aún no se ha abierto (se puede cambiar); cuando se abra
  la votación, su ficha dice «❄ Congelado» y no deja subir versión, renombrar ni eliminar (sí añadir otro).
- [ ] **Papelera:** «Eliminar» un documento (pide confirmación) lleva a «Documentos → Papelera», con los días
  que le quedan; «Recuperar» lo devuelve. Como **Nutria**, un documento de Lince no tiene «Eliminar».
- [ ] Como **superadmin**, «Plataforma → Espacio para archivos»: el espacio de toda la plataforma (2048 MB de partida) y
  el de cada organización, con lo que ocupa. «Plataforma → Limpieza» tiene una fila nueva, «Documentos en
  la papelera» (30 días).
- [ ] Con el antivirus en marcha (0.9), sube el fichero de prueba EICAR (un texto que todos los antivirus
  reconocen; búscalo como «EICAR test file», guárdalo como `eicar.txt`): dice que ha encontrado un virus y
  no lo guarda.

## 43. Portada pública y miniwebs

Antes: `python manage.py migrate` (0.3), `npm run construir` (0.2) y rehacer los ejemplos (0.4).
- [ ] **Sin sesión** (ventana privada), abre http://localhost:8000/: va a la **portada**, con las pestañas
  «Bienvenida» y «Cómo participar», «Entrar» a la derecha y, abajo, «ORG Tajo». Pulsa ORG Tajo: su portada
  con «Quiénes somos». La página interna «Normas de convivencia» no sale.
- [ ] Como **Nutria**, arriba sale el botón **«🌐 Webs»** (con un número: las novedades). Al pulsarlo se abre
  la web de GRU Henares **sin el menú de la izquierda**: «Calendario de la huerta». Arriba, el camino «ORG
  Tajo › GRU Tajo › GRU Jarama › GRU Henares»; GRU Jarama tiene su página «Asambleas de zona».
- [ ] **Grupos de actividad ▾**: GRU Arga (de ORG Ebro), con «Taller de bicis» (publica para GRU Henares).
- [ ] «Novedades» (el número del botón vuelve a cero), «Buscar» (prueba «habas») y **«Jerarquía»**: el grafo
  con ORG Tajo en su caja y GRU Arga aparte, con una flecha de puntos «publica para». Pulsa un grupo.
- [ ] Como **Garza** (GRU Sorbe, debajo de GRU Henares) también ve «Calendario de la huerta». Como **Tejón**
  (GRU Manzanares) no la ve: su camino va por GRU Jarama, y GRU Henares no sale.
- [ ] Como **Lince**, «Administrar → Webs → Páginas»: crea una página en GRU Henares, «Escribir» (en directo si
  el editor está en marcha), sube una imagen y pon en el texto lo que sale al lado («Copiar»). Nadie la ve
  hasta «Publicar»; al publicar, Nutria recibe una notificación. Cambia el borrador: lo publicado no cambia
  hasta «Volver a publicar». «Retirar» la quita.
- [ ] Como **Lince**, «Administrar → Webs → Publicación y consumo»: sale la relación de GRU Arga, aceptada.
  «Cortar» y, como Nutria, el tramo «Grupos de actividad» desaparece. Como **Zorro**, propón otra vez para
  GRU Henares: Lince recibe un aviso y la acepta.
- [ ] Como **superadmin**, crea una página de «Portada de la plataforma»: sale en la portada sin sesión.

## 44. Editor que no abría textos y «Lo que puedes hacer» en los documentos

Antes: el 0.8 (sobre todo «¿Llega el editor a la plataforma?» y reiniciar el editor).
- [ ] Como **Nutria**, abre «Documento: ¿Dónde hacemos el huerto?» → «Escribir»: entra en directo («En
  directo») y lo que escribes se guarda solo. Lo mismo con un documento nuevo.
- [ ] Si algo falla al entrar, el aviso dice **por qué**: «el pase…» (caducado, otra sala) o «el editor no
  consigue el texto de la aplicación…» (no es cosa de tu permiso).
- [ ] «Participación → Documentos»: arriba, «C (crear): puedes crear documentos en…». Columna **«Puedo»** con
  R U D en verde; en uno de Lince, U y D tachados, y al pasar el ratón dice por qué. Filtro «Puedo
  cambiarlo: No».
- [ ] Abre ese documento de Lince: el recuadro **«Lo que puedes hacer»** sale abierto, con «✘ Cambiarlo: Solo
  lo escriben quienes tienen su redacción…» y las salidas: pedírsela a Lince (lleva a escribirle), a la
  administración de su grupo (conversación con el asunto puesto) o comentar.
- [ ] Como una persona sin grupos (o sin permiso de crear), la lista dice «No puedes crear documentos» con
  la explicación, y no salen los botones de crear.


## 45. Cursor del editor en modo oscuro

Antes: reinicia el editor para que se rehaga su cliente (o, sin reiniciar, `npm run construir` en `editor/`;
para saber si ya está, busca «ec-seleccion» en `editor/publico/cliente.js`). Recarga la página con Ctrl+F5.
- [ ] Como **Nutria**, en modo oscuro, abre «Documento: ¿Dónde hacemos el huerto?» → «Escribir»: al pulsar en
  el cuadro **se ve el cursor** (claro) y al seleccionar, la selección en violeta suave, con el texto legible.
- [ ] Como **superadmin** (que no tiene la redacción), en ese mismo documento: el aviso dice «No tienes la
  redacción: no puedes escribir, pero sí comentar…», no «Solo lectura».

## 46. Escribir durante horas, descripción, notas de versión y ancho del menú

Antes:
- Migración nueva de documentos (0.3): `python manage.py showmigrations documentos` debe tener marcada
  `[X] 0005_descripcion_y_notas_de_version`; si no, `python manage.py migrate`.
- Clases nuevas (0.2): si `static/generado/estilos.css` no contiene `ancho-del-menu`, `npm run construir`.
- Cliente del editor (0.8): si `editor/publico/cliente.js` no contiene `ec-sin-conexion`, reinicia el
  editor (o `npm run construir` dentro de `editor/`). Recarga con Ctrl+F5.
- [ ] Como **Nutria**, «Participación → Documentos → Nuevo»: sale el campo «Descripción». Crea uno con
  descripción; en la lista sale **ⓘ** junto al nombre: al pulsarlo, una ventanita con la descripción (se
  cierra con Escape o pulsando fuera). Los que no tienen descripción, sin ⓘ. Buscar una palabra de la
  descripción lo encuentra.
- [ ] En «Escribir», bajo el título, la descripción; «Cambiar el título y la descripción» la guarda. En la
  ficha sale bajo el título. En un archivo o un enlace, «Cambiar» también la tiene.
- [ ] En «Escribir» (en directo), escribe algo y pulsa **💾 Guardar versión**: pide «Qué has cambiado
  (opcional)»; con Intro sale «Guardada la versión N a las HH:MM: «…»». En la ficha, «Versiones» enseña esa
  versión con su nota; lo que escribas después va a una versión nueva aunque no pasen 10 minutos. Sin
  directo (`?sin_directo=1`), el cuadro «Nota de la versión» junto a «Guardar» hace lo mismo.
- [ ] Sin conexión: con el documento abierto en «Escribir», para el editor (en una terminal de tu ordenador,
  `docker stop $(docker ps -q -f name=editor)`). A los 5 segundos sale el **aviso rojo** «Sin conexión con el
  editor desde las…». Escribe algo; al intentar cerrar la pestaña, el navegador pregunta. Arranca el editor
  (`docker start $(docker ps -aq -f name=editor)`): el aviso se va solo y lo escrito llega a la plataforma.
- [ ] Repite, pero cierra la pestaña antes de arrancar el editor. Al abrir otra vez el documento sale «Hay
  texto escrito sin conexión»: al desplegarlo, el texto, «Copiar el texto» y «Descartar».
- [ ] El **menú de la izquierda**: arrastra su borde derecho para ensancharlo o estrecharlo (entre 160 y 480
  píxeles); al recargar, sigue igual; doble clic en el borde, vuelve al ancho de partida. Con el menú plegado
  (☰) el borde no sale.
