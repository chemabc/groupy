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
  `mantenimiento`). **Un módulo funcional nunca importa otro**: se relacionan con anclas y
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
  de la subsección). Si no está claro en qué nivel va algo, se pregunta.
- El modelo de usuario es `usuarios.Usuario` (su nombre visible es el alias). Nada se ve sin sesión.

## Estado

- 12 de noviembre de 2026: **fase 0 terminada** (esqueleto, contrato de módulo, `eventos_sw`, medición,
  plantilla general, tabla filtrable, botón «copiar» y pruebas en el navegador con Playwright).
- **Fase 1 en curso** (ver docs/diseno.md, apartado 19). Hecho: `usuarios` (entrar, salir, «Mi cuenta»
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
  organización, campos heredados y ordenados arrastrando). Recuerda `migrate --database=boveda`.
