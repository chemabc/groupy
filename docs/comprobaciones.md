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

- [ ] **¿Ya está?** `ls static/generado/diagramas static/generado/fullcalendar` lista
  `mermaid.min.js`, `svg-pan-zoom.min.js`, `index.global.min.js` y `es.global.min.js`.
  **Si no** (o si has cambiado plantillas y faltan estilos):

```bash
# Copia las librerías a static/generado/ y compila el CSS
#     run construir: orden de package.json (herramientas/construir.mjs y Tailwind)
npm run construir
```

### 0.3 Tablas de la base de datos al día (las dos bases)

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

Los ejemplos han crecido hoy: el proyecto «Huerto comunitario» lleva dependencias, recursos y etiquetas,
y el tipo «Preparación de acción» trae tareas modelo.

- [ ] **¿Ya está?** Esta orden escribe `True True`:

```bash
# Pregunta a la base si están el huerto con recursos y las tareas modelo de ejemplo
#     shell -c: ejecuta una línea de Python con Django cargado
python manage.py shell -c "from django.apps import apps; P=apps.get_model('proyectos','Proyecto'); T=apps.get_model('tipologias','TareaModelo'); print(P.objects.filter(titulo='Huerto comunitario', recursos__isnull=False).exists(), T.objects.exists())"
```

  **Si no** (borra y vuelve a crear los ejemplos; no toca al superadmin):

```bash
# Borra los datos de ejemplo de todos los módulos y los crea de nuevo
#     ejemplos borrar / ejemplos crear: orden del módulo «ejemplos»
python manage.py ejemplos borrar && python manage.py ejemplos crear
```

### 0.5 El trabajador (reparte las notificaciones y hace las tareas diarias)

Lee el código al arrancar: después de los cambios de hoy hay que **reiniciarlo** aunque esté en marcha.

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
- [ ] **Pruebas:** `python manage.py test --parallel 4` termina con `OK` (unas 370). Si dice
  `skipped=` con muchas, falta Chromium para las pruebas en el navegador:
  `python -m playwright install --with-deps chromium`.

---

## 1. Desarrollo y mantenimiento, trastienda y guías

- [ ] Como **superadmin**: «Desarrollo y mantenimiento» tiene cuatro subsecciones (Guías de desarrollo,
  Ayuda y documentación, Pruebas, Trastienda).
- [ ] «Ayuda y documentación»: una pestaña por documento, con el índice a la izquierda; un enlace de un
  documento a otro abre su pestaña.
- [ ] «Trastienda»: el botón lleva al panel de Django; las fichas tienen Guardar, Guardar y continuar,
  Cancelar y Eliminar.
- [ ] Como **Nutria**: ve «Desarrollo y mantenimiento» con **solo** «Guías de desarrollo» (en
  producción no la verá). Entrar a mano en `/mantenimiento/trastienda/` da la pantalla 403 que explica.
- [ ] «Guías de desarrollo → Arquitectura»: los diagramas se dibujan; los botones + y − acercan y
  alejan, ⤢ ajusta, ⛶ pone la pantalla completa (Esc para salir), doble clic acerca y se mueve
  arrastrando. La caja se alarga tirando de su esquina inferior.
- [ ] En esta guía, las casillas se marcan, el recuento de arriba cambia y siguen marcadas al recargar.

## 2. Audiencias (quién ve cada cosa)

- [ ] Como **Lince**: «Configuración → Visibilidad» muestra ORG Tajo con su altura máxima, «toda la
  organización» y «público», cerrados de entrada, y una frase que lo resume.
- [ ] Cambia la altura máxima y guarda: al convocar un evento en GRU Henares, el desplegable «Quién lo
  ve» ofrece más o menos niveles por encima del grupo según esa altura.
- [ ] Algo personal (un proyecto personal de Nutria) no lo ve **ni el superadmin** (ni en listas ni
  entrando por su dirección).

## 3. Menú en tres niveles e importación masiva

- [ ] El menú izquierdo tiene sección y subsección; arriba salen las vistas de la subsección. Al entrar
  por una dirección, la sección se abre sola y la subsección queda marcada.
- [ ] Como **superadmin**, «Pruebas → Importar grupos»: descarga la plantilla .ods, ábrela con
  LibreOffice (instrucciones y desplegables), añade dos grupos (uno dentro de otro) y súbela.
- [ ] La vista previa marca los errores por fila; no se crea nada hasta «Confirmar», y luego todo de
  golpe.
- [ ] «Importar usuarios» se niega mientras «Permitir el alta masiva de usuarios» está apagado.

## 4. Datos de ejemplo desde la pantalla

- [ ] Como **superadmin**, «Pruebas → Datos de ejemplo»: muestra cuántos hay de cada cosa; «Borrar»
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

- [ ] Como **Lince**, «Configuración → Etiquetas»: crear «  #REUNIÓN   general» la guarda como «Reunion
  general» (primera en mayúscula, sin tildes; la ñ se queda).
- [ ] Palabras relacionadas: buscar por una relacionada encuentra la etiqueta.
- [ ] Fusionar dos marcadas en una; borrar una.
- [ ] Como **Zorro** (ORG Ebro), las etiquetas de ORG Tajo no se sugieren nunca; las comunes sí.

## 7. Tipologías

- [ ] Como **Lince**, «Configuración → Tipologías → De eventos»: el árbol común (Reunión, Acción,
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

## 11. Visibilidad y etiquetas en Configuración (cierre de la fase 1)

- [ ] «Configuración» agrupa Tipologías, Visibilidad, Etiquetas, Niveles de aviso, Solicitudes,
  Lugares y Limpieza (cada una solo para quien tiene su permiso).

## 12. Notificaciones

Necesita el trabajador (paso 0.5).

- [ ] Como **Lince**, admite a alguien en GRU Henares: a esa persona le llega «te han admitido» en unos
  segundos y el número de «Comunicaciones → Notificaciones (N)» sube al navegar.
- [ ] Bandejas por origen; abrir una notificación la marca vista y lleva a su enlace; papelera;
  «Marcar todas como vistas» y «Limpiar las vistas».
- [ ] «Preferencias de aviso»: desactiva un tipo y comprueba que ese aviso ya no llega.

## 13. Avisos y conversaciones con la administración

- [ ] Como **superadmin**, «Configuración → Niveles de aviso»: Información, Atención y Problema con su
  color; uno usado no se borra.
- [ ] Como **Lince**, «Avisos de la administración»: aviso de nivel «Atención» a GRU Henares con «Se
  puede responder». A Nutria le llega con borde de color y un enlace para responder.
- [ ] Como **Nutria**, «Con la administración → Escribir a la administración» (la de GRU Henares).
  Lince la ve en su buzón; al responder firma «Admin de GRU Henares (Lince)»; los mensajes nuevos
  aparecen solos en unos 10 segundos; cambia el estado a «Solucionada».

## 14. Solicitudes con apoyos

- [ ] Como alguien de fuera, pide «Entrar en un grupo» a GRU Henares. Sale en «Solicitudes →
  Pendientes (N)» de sus miembros.
- [ ] Hacen falta el sí de la administración (Lince) y 2 apoyos; los apoyos se ven con alias y los
  rechazos solo como número. El sí del superadmin basta solo.
- [ ] «Configuración → Solicitudes»: apoyos y días por plataforma y por organización.

## 15. Lugares

- [ ] Como **Nutria**, «Lugares → Mi lugar»: elegir uno (privado), proponer un lugar nuevo o un cambio.
- [ ] Como **superadmin**, «Gestión de lugares → Propuestas»: se ve qué cambia antes de aceptar.
- [ ] «Mapa y lista»: el mapa de Leaflet con chinchetas agrupadas; los números de personas solo
  aparecen desde 5.
- [ ] «Importar» desde .ods o .csv en dos pasos; «Configuración → Lugares».

## 16. Talentos

- [ ] Como **Nutria**, «Mis talentos»: «Furgoneta», compartida con GRU Henares; compártela también con
  GRU Lozoya.
- [ ] «Talentos de mis grupos»: solo números, nunca alias.
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

- [ ] «Calendario → Ver el calendario»: mes, semana, día y lista (en el móvil, lista). Cada tipo con su
  color y casillas arriba para ocultarlo; al recargar, los filtros se recuerdan.
- [ ] Arrastra un evento tuyo a otro día: se guarda. Uno ajeno no se puede arrastrar.
- [ ] Pulsa un hueco: abre «Apuntar un recordatorio» con ese día. «Solo yo», «Mi grupo» y, como Lince,
  hasta el padre o el abuelo.
- [ ] «Suscripción»: copia la dirección .ics y ábrela en otra ventana sin sesión: descarga el
  calendario. «Cambiar la clave» y la dirección vieja deja de funcionar.
- [ ] Las fechas límite de proyectos y tareas salen como días enteros y se arrastran.

## 19. Series de eventos y tareas diarias

- [ ] Al convocar, elige «Repetir cada semana» hasta dentro de dos meses: se crean las veces de los
  próximos 90 días, cada una con su ficha, a la misma hora de aquí aunque cambie el horario de verano.
- [ ] «Mis eventos → Series»: la ficha de la serie; cambia la hora: las veces futuras sin tocar cambian
  y una que hayas editado a mano se queda como estaba.
- [ ] «Terminar la serie»; una serie de reuniones pide **una sola** solicitud de apoyos.

## 20. Proyectos y tareas

- [ ] Como **Nutria**, «Proyectos → De mis grupos»: «Huerto comunitario» › «Riego» › «Bomba solar»
  sangrados en árbol.
- [ ] La ficha: camino desde el principal, datos, subproyectos, tareas y cometidos (coordinación,
  documentación, comunicación). «+ Subproyecto» y «Cambiar estado».
- [ ] Como **Garza** (GRU Sorbe): ve el huerto pero no puede gestionarlo; como **Lince** (admin de GRU
  Henares), sí.
- [ ] Kanban del huerto: incluye las tareas de los subproyectos; arrastra una tuya de columna y recarga:
  sigue allí. Las de otra persona no se arrastran.
- [ ] «Mis tareas» en lista y en kanban. Encargar una tarea a Garza (por su alias): le llega el aviso.
- [ ] «Personales»: un proyecto personal con subproyecto; no lo ve nadie más, ni el superadmin.

## 21. Limpieza (archivo y borrado)

- [ ] Como **superadmin**, «Configuración → Limpieza»: los plazos de cada tipo (30 días para archivar,
  365 para borrar; notificaciones 90 y 365). Cambia uno y vuelve «De partida».
- [ ] Prueba rápida: crea un proyecto «Prueba», ponlo en «Finalizado» y ejecuta las dos órdenes de
  abajo (hacen como si hubiera terminado hace 40 días y pasan la limpieza). Desaparece de la lista y
  está en «Archivo → Archivados», con su ficha marcada «Archivado el…».

```bash
# Hace como si el proyecto «Prueba» se hubiera finalizado hace 40 días
python manage.py shell -c "from django.apps import apps; from django.utils import timezone; from datetime import timedelta; apps.get_model('proyectos','Proyecto').objects.filter(titulo='Prueba').update(terminado=timezone.now()-timedelta(days=40))"
# Pasa la limpieza ahora (las tareas diarias se pueden repetir)
python manage.py tareas_diarias
```

- [ ] A quienes lo ven les llega «Se ha archivado un elemento que ves».
- [ ] «Conservar»: queda «conservado por…» y ya no tiene fecha de borrado. Como superadmin, «Dejar de
  conservar» y «Borrar ya»: aparece en «Archivo → Borrados» como poda a mano.
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
- [ ] Como **superadmin**, «Configuración → Tipologías → De proyectos → Preparación de acción»: tres
  tareas modelo (pedir permiso, preparar el material, difundir), con sus días y «espera a la anterior».
  Como Lince, en un subtipo propio salen como heredadas y se le pueden añadir otras.
- [ ] Nuevo proyecto de «Preparación de acción» con la casilla «Crear las 3 tareas modelo» marcada: las
  tres se crean con fecha límite, la primera pendiente y las otras dos bloqueadas en cadena. Sin la
  casilla, no se crea ninguna.
