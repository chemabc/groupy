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
- Cada pantalla nueva llega con su prueba de número de consultas (`assertNumQueries`), como mucho
  unas 15, y se mide con datos de ejemplo.

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

- Django 5.2, monolito modular por capas: Base (`base`, `eventos_sw`, `anclas`, `etiquetas`,
  `tipologias`, `ejemplos`) → Identidad (`boveda`, `usuarios`) → Organización (`lugares`, `grupos`,
  `permisos`, `audiencias`, `solicitudes`, `moderacion`) → Funcional (`eventos`, `proyectos`, `debates`,
  `consultas`, `documentos`, `decisiones`, `calendario`, `comunicaciones`, `publico`, `limpieza`). **Un módulo funcional nunca importa otro**: se relacionan con anclas y
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
- El modelo de usuario será `usuarios.Usuario` (su nombre visible es el alias): **no ejecutar `migrate`
  antes de que exista esa app.**

## Estado

- 12 de noviembre de 2026: esqueleto (contenedor, Django y ajustes de rendimiento). Siguiente paso: el
  resto de la fase 0 (ver docs/diseno.md, apartado 19).
