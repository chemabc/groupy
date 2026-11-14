# Proyecto: gestión de asambleas, versión 2

Herramienta para grupos de asambleas multinivel: organizaciones y grupos, eventos (reuniones, acciones…),
proyectos y tareas, debates, consultas, ODD y actas colaborativas, registro de decisiones,
comunicaciones e información pública. Rehecha desde cero con lo aprendido en la versión 1.

## Documentación (solo Markdown, en este repositorio)

- `docs/diseno.md`: **documento único** con las premisas, el glosario, la arquitectura y todo lo
  decidido. Léelo antes de proponer nada. Lo que no está marcado como *(por confirmar)* no se
  rediscute salvo que lo pida la persona usuaria.
- `docs/registro-y-validacion.md`: cómo funcionan la bóveda, el pase con firma ciega y los sistemas de
  validación.
- `docs/tutorial.md`: lo que se explica para aprender, paso a paso.
- `docs/arranque.md`: cómo arrancar y probar.
- `docs/comprobaciones.md` y `docs/arquitectura.md`: las **guías de desarrollo** (ver abajo).
- `docs/como-se-hace.md`: «How to?», guías cortas de uso para todo el mundo.

`docs/todo.md` es un boceto de la persona usuaria: no se sigue ni se toma como encargo.

No se usa Google Drive. Al tomar una decisión nueva, añádela a `docs/diseno.md` (con la fecha, el motivo
y lo descartado). Al explicar algo nuevo para aprender, añádelo a `docs/tutorial.md`.

## Forma de trabajar

- Todo en castellano: respuestas, código, comentarios y documentos.
- Las respuestas empiezan con una etiqueta [A-ID], donde ID se incrementa en cada respuesta.
- Método socrático: antes de programar una pantalla o un módulo, propón opciones con pros y contras (una
  recomendada) y pregunta. No programes sin acuerdo.
- Commit al terminar cada pieza acordada, con el mensaje en castellano.
- Cada pantalla nueva llega con su prueba de número de consultas, como mucho unas 15, que no crezca con
  las filas (`PruebaDePantalla.comprobar_consultas`, en `base/pruebas.py`), y se mide con datos de ejemplo.
- Lo que lleva JavaScript propio (Alpine, htmx) se prueba también en un navegador de verdad
  (Playwright, `base/tests/test_navegador.py`) antes de darlo por bueno.

## Guías de desarrollo (mantenerlas al día en cada pieza)

Se ven en «Ayuda → Guía de desarrollo» (comprobaciones) y «Ayuda → Documentación de la plataforma»
(arquitectura), también en el panel de ayuda (? rojo): en desarrollo, cualquier persona con sesión; en
producción, solo el superadmin (`GUIAS_DE_DESARROLLO_PARA_TODOS`). Qué documento va en qué subsección:
`ayuda/documentos.py`. Al añadir algo que se usa a diario, añade su guía corta a `docs/como-se-hace.md`
(«Ayuda → How to?», para todo el mundo).

- **`docs/comprobaciones.md`** («Comprobaciones pendientes»): al terminar cada pieza, añade su sección al
  final, con casillas `- [ ]`, diciendo dónde entrar (menú, con qué usuario de ejemplo) y en qué fijarse.
  Si la pieza necesita algo especial (migrar, `npm install`, `npm run construir`, rehacer los ejemplos,
  reiniciar el trabajador, una orden nueva…), ponlo en «0. Antes de empezar»: **primero cómo comprobar si
  ya está hecho** y después cómo ejecutarlo. Cuando la persona usuaria diga que ha comprobado piezas,
  quítalas de la guía (siguen en git).
- **`docs/arquitectura.md`** («Arquitectura»): al añadir o cambiar un módulo, un componente, una librería
  o un servicio, ponlo al día en la vista global, en su propio diagrama y en los de los módulos con los
  que se relaciona. Cada caja lleva su etiqueta ([Núcleo de Django], [Contrib de Django], [Librería
  Python], [Librería JS], [Servicio], [Servicio externo], [Herramienta], [Configuración], [Módulo · capa],
  [Componente], [Isla JS]) y cada flecha su tipo (`-->` importa, `-.->` contrato, `==>` eventos_sw).
  Las relaciones se sacan del código (imports y contratos), no de memoria.
- Los diagramas son bloques `mermaid`; la prueba `ayuda/tests/test_navegador.py` comprueba que
  todos se dibujan sin errores.

## Normas de código

- Antes de cada orden o función, un comentario que explique qué hace, pensado para alguien que aprende:
  en lenguaje llano y en contexto (qué hace, para qué sirve en la aplicación y desde dónde se usa).
- Cada concepto, tabla (modelo) y campo lleva una descripción en lenguaje llano (docstring,
  `verbose_name`, `help_text`), visible también en la interfaz.
- En bash y docker, cada parámetro se explica en una línea aparte del comentario, empezando por guion y
  con más sangría que la explicación general.
- Claro antes que ingenioso. La plantilla solo pinta; las decisiones, en la vista o en el servicio.
- Código propio: nada de código con licencia GPL.

## Arquitectura (detalle en docs/diseno.md, apartado 3)

- Django 5.2, monolito modular por capas: Base (`base`, `eventos_sw`, `anclas`, `ejemplos`) →
  Identidad (`boveda`, `usuarios`) → Organización (`lugares`, `grupos`, `permisos`, `audiencias`,
  `etiquetas`, `tipologias`, `solicitudes`, `moderacion`) → Funcional (`eventos`, `proyectos`, `debates`,
  `consultas`, `documentos`, `decisiones`, `calendario`, `comunicaciones`, `publico`, `limpieza`,
  `mantenimiento`, `ayuda`, `proximamente`). **Un módulo funcional nunca importa otro**: se relacionan con anclas y
  eventos_sw.
- Cada módulo declara todo lo que aporta en una sola clase (contrato de módulo).
- Visibilidad con audiencias (`audiencia_id`) y permisos precalculados en Redis.
- PostgreSQL con dos bases (plataforma y bóveda, sin ninguna columna que las una), con `jit=off`. Redis.
- Interfaz: plantillas de Django + htmx + Alpine.js + Tailwind. Islas de JavaScript solo para calendario,
  kanban, grafos, mapas y editor.
- «Evento» es la actividad con fecha; los avisos internos del software se llaman «eventos_sw».
- «Rol» es el nivel fijo (superadmin, admin_org, admin_grupo, usuario); «cometido», la función en algo
  concreto (portavoz, coordinación, facilitación, toma de acta…).
- Nada es público por defecto: todo nace privado.
- Menú: al menos dos niveles a la izquierda (sección y subsección) y el tercer nivel arriba (las vistas
  de la subsección). Si no está claro en qué nivel va algo, se pregunta. El orden y la agrupación de
  todas las entradas se decide solo en `config/menu.py` (cada entrada nueva se coloca allí). Lo propio va
  separado de lo que se hace por otras personas: bloques «Administrar» y «Plataforma».
- El modelo de usuario es `usuarios.Usuario` (su nombre visible es el alias). Nada se ve sin sesión.

## Estado

- 12 de noviembre de 2026: **fase 0 terminada** (esqueleto, contrato de módulo, `eventos_sw`, medición,
  plantilla general, tabla filtrable, botón «copiar» y pruebas en el navegador con Playwright).
- 13 de noviembre de 2026: **fase 1 terminada** (ver docs/diseno.md, apartado 19). Hecho: `usuarios` (entrar, salir, «Mi cuenta»
  con preferencias y contraseña), `grupos` (organizaciones, grupos a cualquier profundidad con tabla de
  cierre, pertenencias, asamblea base, admins, relaciones e invitaciones entre organizaciones),
  `permisos` (roles del sistema y personalizados, permisos por defecto en el contrato, excepciones,
  cometidos, caché, `puede`/`exigir`/`@requiere_permiso` y pantalla 403 que explica), la trastienda
  ordenada y explicada, y la orden `python manage.py ejemplos crear` (usuarios: animales y árboles,
  superadmin «superadmin», contraseña `M3n0sL3ctiv4s`; organizaciones «ORG <río>» y grupos «GRU <afluente>»).
  También la sección «Desarrollo y mantenimiento» (módulo `mantenimiento`: documentación de docs/ y
  entrada a la trastienda) y `audiencias` (niveles de visibilidad, configuración por organización y regla
  dura entre organizaciones: nada sin invitación hecha y aceptada con privilegios) e importación masiva de
  grupos y usuarios desde .ods/.csv con plantillas (Desarrollo y mantenimiento → Pruebas), tablas de la
  `boveda` en su base (alta provisional, dominios por organización) y sección «Usuarios» del superadmin
  (módulo `administracion`), y `etiquetas` (de cada organización y comunes, con relacionadas, selector con
  sugerencias en `base`; siempre con la primera letra en mayúscula, el resto en minúsculas y sin
  tildes) y `tipologias` («Configuración → Tipologías»: árbol común del superadmin, subtipos propios de cada
  organización, campos heredados y ordenados arrastrando) y la sección «Organizaciones y grupos» (mis grupos,
  árbol, fichas de grupo y de organización, relaciones e «Invitaciones (N)»), «Usuarios → Roles y permisos»
  (roles con sus permisos, excepciones y «Explicar un permiso»), «Configuración → Visibilidad» y
  «Configuración → Etiquetas» (con `EntradaDeMenu.dentro_de`) e iconos de colores únicos en el menú.
- **Fase 2 en curso.** Hecho: `comunicaciones`, primera pieza (notificaciones en la web: los módulos
  declaran `avisos` en su contrato y `comunicaciones` los reparte desde la bandeja; bandejas por origen,
  papelera, «Limpiar las vistas», preferencias y número sin ver en el menú; servicio `trabajador` en
  docker), avisos de la administración (con niveles de color editables en «Configuración → Niveles de
  aviso») y conversaciones con la administración (buzón compartido, firma «Admin de GRU X (alias)»,
  estado, mensajes nuevos cada 10 s) y `solicitudes` (tipos declarados en el contrato; primero, «Entrar
  en un grupo»: sí de la administración y 2 apoyos, o el sí del superadmin; ajustes en «Configuración →
  Solicitudes»), `lugares` (lista común con mapa Leaflet, propuestas de lugares y de cambios, importación,
  lugar privado de cada persona, recuentos desde 5 y «Configuración → Lugares»). `moderacion` se deja para
  cuando haya contenido. Y `talentos` (catálogo común, mis talentos compartidos por grupo, recuentos sin
  nombres, peticiones con «Lo ofrezco» y «Tengo dudas»). Fase 2 cerrada (salvo `moderacion`).
- 13 de noviembre de 2026: **fase 3 terminada.** Hecho: `eventos` (convocar con el selector de visibilidad y los campos de la
  tipología; reuniones con solicitud de apoyos 2/5/10; cartel privado; «¿Vas a ir?» con alias solo para
  quien convoca y los cometidos; cometidos; compartir; cancelar) y `calendario` (FullCalendar con las
  fuentes de cada módulo, filtros por tipo, arrastrar lo propio, recordatorios y suscripción .ics con
  clave secreta) y series de eventos (cada semana, cada mes…; cada vez es un evento propio creado a 90
  días vista; las cambiadas a mano no se tocan; series de reuniones con una sola solicitud) con tareas
  diarias en el trabajador (`TareaDiaria`).
- **Fase 4 en curso.** Hecho: `proyectos`, primera pieza (proyectos de grupo y personales con
  subproyectos a cualquier profundidad, cometidos, tareas en proyecto, sueltas o personales, kanban con
  SortableJS, fechas límite en el calendario) y `limpieza` (tarea diaria: archiva lo terminado a los 30 días,
  avisa 15 días antes de borrar a los 365, «Conservar», poda del superadmin, registro de borrados,
  notificaciones viejas fuera; plazos en «Configuración → Limpieza») y dependencias entre tareas (bloqueo y desbloqueo solos, sin
  círculos) y recursos de cada proyecto (con «Pedir al grupo» como petición de talentos), etiquetas de los proyectos de
  grupo (filtran la lista) y tareas modelo de cada tipología de proyecto (se crean al crear el proyecto).
  **Fase 4 cerrada** (la documentación por bloques irá con `documentos`; el chat, con el tiempo real).
- 13 de noviembre de 2026: **guías de desarrollo** («Comprobaciones pendientes» y «Arquitectura», con
  diagramas Mermaid ampliables) en «Desarrollo y mantenimiento».
- 14 de noviembre de 2026: **menú en un solo fichero y ayuda** ([A-31]): `config/menu.py` decide el orden
  y la agrupación del menú (se quitan `orden` y `dentro_de`); módulo `ayuda` (sección «Ayuda»: How to?,
  Documentación de la plataforma, Guía de desarrollo) con los documentos de docs/; ? rojo en la cabecera
  y panel de ayuda a la derecha (no se vuelve a pintar al navegar, separador arrastrable, se recuerda) e
  índice plegable. Y selector de personas común ([A-35]: `base` SelectorDePersonas/CampoDePersonas, isla
  `selectorDePersonas`, `audiencias/cercania.py`), de entrada en la responsable y colaboran de las tareas.
  Y el **menú en tres bloques** ([A-37], [A-38]): lo propio, «Administrar» y «Plataforma» (`Bloque` y
  `Pestanas` en `base/disposicion.py`, usados en `config/menu.py`), con las herramientas que faltan en el
  módulo `proximamente`. Siguen las piezas acordadas en [A-37]: Inicio (panel y mis datos), árboles de
  grupos con colores y grafo, proyectos (rejilla, migas de pan y tarea editable) y eventos. Después, fase 5
  (`documentos` y `decisiones`), pendiente de las preguntas de [A-30].
  Y los **árboles de grupos** ([A-40]: `grupos/arboles.py`, en «Mis grupos → Árboles» y arriba de la ficha de
  cada grupo; asamblea base en amarillo, organización en violeta, grupo que se mira en rojo). E **Inicio**
  ([A-40]): Panel (dashboard que resume comunicaciones, solicitudes y proyectos abiertos) y Mis datos
  (Inicio enseña y «Configuración de mi cuenta → Mis datos → Datos» edita), con `TarjetaDeInicio` en el
  contrato, la función en el `inicio.py` de cada módulo y la colocación en `config/inicio.py`. Y los
  **árboles de proyectos** ([A-44]: `proyectos/arboles.py`, rejilla de 3 columnas, tareas plegadas con
  «(hechas/totales) ▸», amarillo si participas, rojo el que se mira). Y la **ficha de tarea** ([A-44]: camino con los
  proyectos en violeta, lo escrito se cambia encima con htmx en `proyectos:tarea_campo`, lo demás en el
  desplegable «Completar o cambiar todo»). Y el **árbol de tipologías** con el mismo aspecto (amarillo lo que
  se puede cambiar, rojo el elegido). Siguen el grafo de grupos y eventos; después, fase 5 (`documentos` y
  `decisiones`), pendiente de las preguntas de [A-30].
  Recuerda `migrate --database=boveda`.
