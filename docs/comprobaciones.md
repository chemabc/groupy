# Comprobaciones pendientes

Guía para comprobar a mano, paso a paso, lo construido. Empieza por **«Antes de empezar»**: cada paso
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

Los ejemplos crecen con cada pieza. Los últimos que se añadieron: el proyecto «Huerto comunitario» lleva
dependencias, recursos y etiquetas, y el tipo «Preparación de acción» trae tareas modelo. Necesita el 0.3
hecho.

- [ ] **¿Ya está?** Esta orden escribe `True True`:

```bash
# Pregunta a la base si están el huerto con recursos y las tareas modelo de ejemplo
#     shell -c: ejecuta una línea de Python con Django cargado
python manage.py shell -c "from django.apps import apps; P=apps.get_model('proyectos','Proyecto'); T=apps.get_model('tipologias','TareaModelo'); print(P.objects.filter(titulo='Huerto comunitario', recursos__isnull=False).exists(), T.objects.exists())"
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
  y una franja ámbar: Grupos que administro (Árbol · Miembros (vacía) · Invitaciones entre grupos), Buzón de la
  administración (Conversaciones que atiendo · Avisar), Por aprobar, Eventos y talentos (Eventos de mis grupos
  (vacía) · Pedir talentos), Moderación (vacía) y Mi organización (Datos · Visibilidad · Tipologías ·
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

