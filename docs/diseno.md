# Diseño y decisiones: gestión de asambleas, versión 2

Documento único del proyecto. Reúne las notas de la persona usuaria (`notas_humanas_para_el_nuevo_proyecto/`),
lo aprendido en la versión 1 (`para-el-nuevo-proyecto/`) y las respuestas a las dudas de la fusión
(12 de noviembre de 2026). Cuando hay conflicto, **mandan las notas de la persona usuaria**.

**Cómo se mantiene:** cada decisión nueva se añade aquí, en su sección, con la fecha, el motivo y lo
descartado. Lo marcado como *(por confirmar)* lo decidió Claude a falta de respuesta, y se puede reabrir.
El funcionamiento de la identidad está explicado aparte, en [registro-y-validacion.md](registro-y-validacion.md).

---

## 1. Premisas (mandan sobre todo lo demás)

1. **Rapidez.** El servidor responde muy rápido; todo está optimizado.
2. **Modularidad extrema.** Eventos, proyectos y tareas, debates, consultas y actas son herramientas
   casi independientes: cualquiera se puede colgar de un proyecto, de una tarea, etc. sin condicionar
   las tablas de las demás ni complicar las consultas.
3. **Sensación de ligereza.** La aplicación parece ligera y tarda poco en hacer lo que se le pide.
4. **Filtrar cualquier tabla al momento**, por palabras o por categorías. Si hay demasiadas filas para
   tenerlas en memoria, se busca en el servidor.
5. **Limpieza.** Hay un mecanismo configurable para archivar y borrar lo que ya no sirve.
6. **Pantallas limpias, claras, compactas y muy interactivas.** Si algo se puede arrastrar, se arrastra.
   Se buscan los menos clics posibles.
7. **Dos menús en el ordenador:** a la izquierda, secciones y subsecciones (plegable); arriba, las vistas
   de la sección elegida. Diseño minimalista y útil.
8. **Dos dimensiones también en el móvil.**
9. **Ayuda «?» en cada sección**, que explica en contexto para qué sirve y qué significa cada dato.
10. **El menú no salta:** al pulsar una opción, aunque se recargue la página, el menú sigue donde estaba.
11. **Anonimato.** La identidad real nunca se puede deducir desde la plataforma. Si comodidad y anonimato
    chocan, gana el anonimato.
12. **Participación lo más horizontal posible.** Cualquier persona puede iniciar cosas; los admin cuidan,
    no filtran.
13. **Nada es público por defecto.** Todo nace privado y se abre a propósito.

---

## 2. Glosario cerrado (un concepto, un nombre)

| Término | Qué es | En el código |
|---|---|---|
| **Organización** | Ámbito abstracto, jurídico. Agrupa grupos y es independiente de las demás organizaciones. Tiene al menos un grupo | `Organizacion` |
| **Grupo** | Colectivo real y concreto: asamblea, grupo de trabajo, comisión… Puede contener otros grupos | `Grupo` |
| **Asamblea de centro** | Un grupo que ha elegido un lugar de la lista de lugares | `Grupo` con `lugar` |
| **Usuario** | La persona dentro de la plataforma, siempre con seudónimo. Su nombre visible es su **alias** | `usuarios.Usuario` (campo `alias`) |
| **Persona** | La identidad real; solo existe en la bóveda | `boveda.Persona` |
| **Lugar** | Sitio externo con dirección y mapa (colegio, centro de salud, local) | `Lugar` |
| **Pertenencia** | Que un usuario está en un grupo, con su rol allí | `Pertenencia` |
| **Rol** | Nivel fijo de poder: superadmin, admin_org, admin_grupo, usuario (y el público, sin cuenta) | `Rol` |
| **Cometido** | Función en algo concreto: portavoz de una organización, coordinación de un proyecto, facilitación de un debate, toma de acta, Logística en una acción, custodio de identidad… | `Cometido` |
| **Tipología** | Tipo de proyecto o de evento, en árbol, con su plantilla de campos | `Tipologia` |
| **Evento** | Actividad con fecha: reunión, acción, recaudatorio… | `eventos.Evento` |
| **Recordatorio** | Anotación libre en el calendario, sin módulo detrás | `calendario.Recordatorio` |
| **eventos_sw** | Avisos internos entre módulos del software («tarea hecha», «debate abierto») | `eventos_sw` |
| **Proyecto / Tarea** | Trabajo organizado; la tarea es atómica y tiene una persona responsable | `Proyecto`, `Tarea` |
| **Debate** | Una pregunta con varias opciones en columnas | `Debate` |
| **Opción** | Una postura del debate (una columna) | `Opcion` |
| **Argumento** | Texto a favor o en contra de una opción, o en respuesta a otro argumento | `Argumento` |
| **Voto** | Icono que una persona pone en una opción o en un argumento | `Voto` |
| **Intervención** | Cualquier cosa que escribe una persona en un debate (cuenta para los límites) | — |
| **Consulta** | Formulario y votación con resultados | `Consulta` |
| **Documento** | Orden del día (ODD) o acta escritos en el editor colaborativo | `Documento` |
| **Decisión** | Acuerdo tomado en una reunión, un debate o una consulta, copiado al registro común | `Decision` |
| **Solicitud** | Petición que necesita apoyos (abrir un debate, convocar una reunión, abrir una opción…) | `Solicitud`, `Apoyo` |
| **Audiencia** | Quién puede ver algo | `Audiencia` |
| **Ancla** | Referencia genérica «tipo + id» a cualquier objeto | `ancla_tipo`, `ancla_id` |
| **Etiqueta** | Palabra normalizada para clasificar y buscar (una sola base, con grupos por módulo) | `Etiqueta`, `GrupoDeEtiquetas` |
| **Talento** | Recurso o habilidad de un usuario, que comparte con quien elige | `Talento` |
| **Comunicación** | Notificación, mensaje o chat | módulo `comunicaciones` |
| **Información pública** | Portada y banco de recursos públicos de cada organización | módulo `publico` |
| **Ocultación provisional** | Contenido señalado por un admin: se ve en otro color, con aviso, hasta que se resuelve | `Ocultacion` |

---

## 3. Arquitectura

### 3.1 Base técnica **[heredada de la versión 1]**

- Python 3.13 + Django 5.2 (LTS), monolito modular.
- PostgreSQL 17, con dos bases: plataforma y bóveda.
- Redis 8, para la caché, el tiempo real y las colas.
- Plantillas de Django + htmx + Alpine.js + Tailwind. Islas de JavaScript solo donde hace falta.
- Licencias libres compatibles; **nada de GPL**. Las librerías de la interfaz se sirven desde el propio
  servidor, sin CDN.
- Contenedor de desarrollo (devcontainer) con PostgreSQL y Redis.
- **Cookies con nombre propio** (12 de noviembre de 2026): `asambleas2_sesion` y `asambleas2_csrf`.
  - *Motivo:* el navegador reparte las cookies por servidor (`localhost`), no por puerto. Con los
    nombres de Django por defecto, la versión 2 recibía la sesión de la versión 1 y fallaba al leerla
    (la barra de depuración la consulta). Más adelante, iniciar sesión en una versión cerraría la de la
    otra.

### 3.2 Capas y módulos

| Capa | Módulo | Qué hace |
|---|---|---|
| Base | `base` | Contrato de módulo y registro de módulos, diseño de la interfaz, tabla filtrable, botón «copiar» de los campos |
| Base | `eventos_sw` | Avisos internos: síncronos (misma transacción) y asíncronos (bandeja de salida + trabajador) |
| Base | `anclas` | Referencias «tipo + id» y huecos en las fichas para colgar cosas de otros módulos |
| Base | `ejemplos` | Datos de ejemplo reversibles por módulo |
| Identidad | `boveda` | Identidad real, validación, pases con firma ciega, rondas de revalidación |
| Identidad | `usuarios` | Usuario con seudónimo, preferencias (tema, letra, densidad), recuperación y **talentos** |
| Organización | `lugares` | Lista de lugares con mapa; importación desde Excel; propuestas de lugares nuevos; validación del lugar de cada usuario |
| Organización | `grupos` | Organizaciones, grupos, relaciones, tabla de cierre, pertenencias y admisiones |
| Organización | `permisos` | Roles, cometidos, permisos declarados por cada módulo, permisos precalculados, registro de acciones de los admin |
| Organización | `etiquetas` | Etiquetas de una a tres palabras, de cada organización y comunes, con palabras relacionadas; sugerencias y fusión. *(Movido de Base a Organización el 13 de noviembre de 2026, porque cada organización tiene las suyas.)* El selector, genérico, está en `base` |
| Organización | `tipologias` | Árbol de tipologías de proyectos y de eventos, con campos personalizados que heredan los subtipos. Las comunes, del superadmin; cada organización puede añadir subtipos propios. *(Movido de Base a Organización el 13 de noviembre de 2026, porque cada organización tiene las suyas.)* |
| Organización | `audiencias` | «Quién puede ver esto», calculado una vez por persona |
| Organización | `solicitudes` | Solicitudes con apoyos |
| Organización | `moderacion` | Avisos, denuncias y ocultaciones provisionales |
| Funcional | `eventos` | Eventos con tipologías (reunión, acción, recaudatorio…) y series periódicas |
| Funcional | `proyectos` | Proyectos, subproyectos, tareas (también sueltas y personales), dependencias |
| Funcional | `debates` | Opciones en columnas, argumentos, votos, límites, base de conocimiento |
| Funcional | `consultas` | Formularios, votación (una persona, un voto) y resultados |
| Funcional | `documentos` | Editor colaborativo de ODD y actas (Markdown + tiempo real); el servidor de tiempo real va aparte |
| Funcional | `decisiones` | Registro común de decisiones |
| Funcional | `calendario` | Junta lo que tiene fecha; recordatorios libres; .ics personal y público |
| Funcional | `comunicaciones` | Notificaciones, mensajes de admins y superadmin, conversaciones y chat anclable |
| Funcional | `publico` | Portada y banco de recursos públicos por organización |
| Funcional | `limpieza` | Archivado y borrado programados y configurables |
| Funcional | `administracion` | Pantallas del superadmin que juntan varios módulos: «Usuarios» (personas de la bóveda, dominios permitidos y alias); más adelante, organizaciones y tipologías |
| Funcional | `mantenimiento` | Sección «Desarrollo y mantenimiento» del superadmin: documentación de `docs/` convertida en páginas, entrada a la trastienda y, más adelante, la salud del sistema |

**Regla de dependencias:** Base no depende de nada. Identidad depende de Base. Organización depende de
Base y del modelo de usuario (`get_user_model()`). Funcional depende de Base y Organización, y **nunca de
otro módulo funcional**: se relacionan con anclas y eventos_sw.

**Ejemplo:** una consulta termina. `consultas` emite `consultas.cerrada`. `decisiones` lo escucha y copia
el resultado al registro, y `comunicaciones` avisa a quienes votaron. Ninguno importa al otro.

### 3.3 Contrato de módulo

Cada módulo declara **en una sola clase** (en su `apps.py`) todo lo que aporta: permisos y cometidos,
anclas, huecos en fichas, eventos con fecha para el calendario, eventos_sw que emite y que escucha, grupos
de etiquetas, tipos de elemento que se pueden limpiar, datos de ejemplo, entradas de menú y textos de
ayuda «?». El registro se lee **una vez al arrancar**. Nada de buscar ficheros por su nombre.

**Cómo se declara (12 de noviembre de 2026).**
- El contrato **es la propia configuración del módulo**: la clase de `apps.py` hereda de
  `base.contrato.ModuloConfig` (que hereda de `AppConfig`) y rellena sus apartados con fichas
  inmutables (`Permiso`, `Escucha`, `EntradaDeMenu`…).
  - *Motivo:* es literalmente «una sola clase en `apps.py`», y Django ya la carga al arrancar.
  - *Descartado:* una clase `Contrato` en un fichero aparte (dos clases por módulo y buscar el fichero por
    su nombre) y los decoradores repartidos por el código (lo que aporta un módulo no se vería de un
    vistazo).
- **Todos los apartados se declaran desde ya**, vacíos por defecto. Se podrán ajustar cuando llegue el
  módulo que los usa.
- Todo código declarado empieza por la etiqueta del módulo (`eventos.convocar_reunion`). Las funciones y
  los modelos de otros módulos se nombran **como texto**, nunca importándolos.
- `base/registro.py` reúne los contratos en `BaseConfig.ready()` y apunta los errores de declaración.
  `base/comprobaciones.py` los muestra con las comprobaciones de Django (`manage.py check`), junto con
  las funciones y los modelos nombrados que no existen.
- La regla de capas se vigila con una prueba (`base/tests/test_dependencias.py`) que lee el código de
  cada módulo y falla si un módulo importa otro de una capa superior, o un funcional importa otro funcional.
- En `INSTALLED_APPS` los módulos del proyecto se escriben con la ruta de su configuración
  (`base.apps.BaseConfig`).

### 3.4 Visibilidad: audiencias **[con cuidado: es una pieza central]**

**Qué puede elegir quien publica algo** (un proyecto, un evento, un debate o **cada bloque de información
dentro de una ficha**):

| Nivel | Quién lo ve |
|---|---|
| **Privado** (por defecto) | Solo las personas implicadas: quien lo creó, la persona responsable, quien tiene un cometido o está inscrita, y las personas invitadas una a una |
| **Semiprivado**, eligiendo el ámbito: | |
| · Mi grupo | Las personas del grupo y de todos sus subgrupos |
| · Grupo padre | Todas las personas del grupo padre y de **todos sus descendientes** (incluye los grupos hermanos) |
| · Grupo abuelo (y así hacia arriba) | Igual, desde el abuelo |
| · Toda la organización | Todas las personas de todos los grupos de la organización |
| · Grupos concretos | Uno o varios grupos elegidos de la lista, cada uno con sus descendientes |
| **Público** | Cualquiera, también sin cuenta, y siempre sin alias. Aparece en el banco de información pública |

- Cada **organización configura** qué niveles se ofrecen (por ejemplo, hasta qué altura se puede subir o
  si se permite lo público).
- Todo es **privado por defecto**. Un bloque de una ficha puede ser más abierto o más cerrado que la ficha
  (por ejemplo, un proyecto semiprivado con su cartel público).
- **Cómo se calcula sin coste.** Cada elección se guarda como una **audiencia**: una fila con su
  composición (grupos con descendientes, personas, organización o público). Dos elecciones iguales
  comparten la misma fila. Cada objeto y cada bloque guarda solo un número, `audiencia_id`.
  - Por cada usuario se calcula una vez el conjunto de audiencias que ve, con unas 3 consultas, y se
    guarda en Redis con un número de versión. Se recalcula solo cuando cambian sus pertenencias o una
    audiencia.
  - Las listas se filtran con `audiencia_id__in=ids`. Para saber si se ve un bloque basta con una
    comprobación en memoria.
  - Lo que cuelga de algo (un debate en una tarea) toma por defecto la audiencia de su ancla.
- La pantalla de elección explica en una frase a quién llega cada opción y cuántas personas son (solo si
  son 5 o más).

**Cómo está hecho `audiencias` (13 de noviembre de 2026).**
- **Regla dura entre organizaciones** (a petición de la persona usuaria, al responder 1A): una audiencia
  nunca incluye grupos ni personas de otra organización, salvo que lo concreto (el ancla: un proyecto…)
  tenga una invitación **hecha por alguien con permiso** del grupo que invita y **aceptada por alguien con
  permiso** del grupo invitado. Se comprueba en el propio módulo, la pida quien la pida. Entran el grupo
  invitado y sus subgrupos, no los grupos que lo contienen. Solo cuenta para esa cosa: la audiencia con
  invitados no se comparte con nada más. Por eso **invitar a otra organización pasa a ser solo de los
  admins** (`grupos.invitar`: admin del grupo y admin de la organización; migración
  `permisos/0003`). *(Pendiente: qué pasa con lo ya compartido si algún día se puede anular una
  invitación aceptada.)*
- **Tablas:** `Audiencia` (tipo, huella, organización dueña, ancla si es de una sola cosa y si es
  personal), `GrupoDeAudiencia` (grupo con todos sus subgrupos) y `PersonaDeAudiencia`.
- **Lo privado (2A):** una audiencia propia por cosa, con la lista de personas implicadas, que mantiene el
  módulo (`anadir_personas`, `quitar_personas`). Lo **personal** (proyectos y tareas personales) es de una
  sola persona y ni el superadmin lo ve.
- **Se comparten las iguales (3A):** por su huella («grupos:3,7», «organizacion:2», «publica»).
- **Configuración por organización (4A):** `ConfiguracionDeVisibilidad` con la altura máxima, si permite
  «toda la organización» y si permite lo público. Sin configuración, la más cerrada: hasta el grupo
  padre, sin toda la organización y sin lo público. La ajusta el admin de la organización
  (`audiencias.configurar`) o el superadmin.
- **Uso:** `audiencia_para(nivel, grupo, altura, grupos, personas, ancla)` crea la audiencia de lo que
  se publica; `filtrar_visibles(consulta, usuario)` deja en una lista solo lo visible; `puede_ver` para una
  cosa; `describir(audiencia)` da la frase («Lo ven las personas de GRU Jarama y de sus subgrupos (12
  personas).»).
- **Coste:** 2 consultas por persona para calcular lo que ve, guardado en la caché con versión y
  invalidado con señales (sus pertenencias, sus audiencias privadas; mover grupos o crear audiencias de
  grupos, de organización o pública invalida a todo el mundo).
- El superadmin ve todo menos lo personal de otras personas.

### 3.5 Permisos precalculados

- `permisos_de(usuario)` devuelve `{grupo: {códigos}}` y se guarda en la caché con versión. Se invalida al
  cambiar pertenencias, roles, cometidos o excepciones.
- Reglas simplificadas:
  - roles por grupo y por organización;
  - la pertenencia se hereda hacia los grupos que contienen al suyo;
  - admin_grupo y admin_org **no se heredan**;
  - las excepciones son solo individuales.
- «Explicar permiso» (el razonamiento paso a paso) se usa solo en las pantallas de soporte, con una
  prueba que asegura que decide igual que la forma rápida.

**Cómo está hecho `permisos` (12 de noviembre de 2026).**
- **Roles en una tabla que ajusta el superadmin** (`Rol` y `PermisoDeRol`). Cada módulo declara en su
  contrato los roles que tienen cada permiso por defecto (`Permiso(..., roles=("admin_grupo",))`), y
  `sincronizar_permisos()` se los da **solo la primera vez** que aparece el permiso (`PermisoConocido`):
  si después el superadmin se lo quita a un rol, no vuelve. Se ejecuta sola tras cada `migrate`.
  *Descartado:* los permisos solo en el código (cambiar algo obligaría a programar).
- **Roles personalizados** (a petición de la persona usuaria; cambia los «cinco roles fijos» del
  apartado 5): el superadmin puede crear roles de grupo (por ejemplo, «Tesorería») y poner o quitar
  permisos a cualquier rol, también a los del sistema (`usuario`, `admin_grupo`, `admin_org`, que no se
  pueden borrar). Un rol personalizado se da cambiando el rol de una pertenencia, y vale solo en ese
  grupo. *(Roles personalizados de organización y «qué rol tendrá por defecto el admin de cada grupo u
  organización»: más adelante, con las pantallas de nombrar admins.)*
- **El cálculo** (`permisos_de`) sigue las reglas de arriba: el rol `usuario` en sus grupos y en los que
  los contienen; su rol de cada grupo solo allí; `admin_org` en la organización y en todos sus grupos;
  después las **excepciones individuales** (`ExcepcionDePermiso`: dar o quitar un permiso en un grupo;
  quitar gana); y los **cometidos**. Unas 7 consultas, sea cual sea el número de grupos, y a la caché
  (`permisos:<id>:v<versión>`).
- **Invalidación:** con señales de Django (`permisos/senales.py`), para cubrir también la trastienda.
  Cambiar pertenencias, admins, excepciones o cometidos borra el cálculo de esa persona; cambiar grupos,
  roles o sus permisos sube la versión de todos. Siempre al terminar bien la transacción.
- **Cometidos aparte del mapa por grupos** (`Cometido`: persona, código, ancla y el grupo donde vive
  aquello). `tiene_cometido(usuario, código, tipo, id)`, y cada cometido declara en el contrato los
  permisos que da sobre eso concreto (`puede(..., ancla=("debates.debate", 7))`).
  `cometidos_en_grupo(grupo)` da los de la gente de un grupo y sus subgrupos, para que sus miembros vean
  quién hace qué (petición de la persona usuaria). *(Su visibilidad la afinará `audiencias`: un cometido
  en algo privado solo lo verá quien vea ese algo.)*
- **Errores que explican:** `exigir()` y el decorador `@requiere_permiso` lanzan `SinPermiso` con un texto
  como «Para editar los datos del grupo en «GRU Henares» hace falta el permiso «grupos.editar_grupo». Lo
  tienen estos roles: … Puedes pedírselo a: Lince (admin de GRU Henares), Zorro (admin de ORG Tajo), el
  superadmin.». Se muestra en la pantalla 403, dentro de la zona central (htmx la pinta gracias al
  ajuste `responseHandling`).
- **Pantallas «Usuarios → Roles y permisos» (13 de noviembre de 2026).** Subsección de «Usuarios», a
  petición de la persona usuaria («al fin y al cabo son roles de usuarios»). *Descartado:* una sección
  propia (apartado 5.1) y una subsección de «Configuración». Permiso `administracion.roles`, de entrada
  solo del superadmin. Tres vistas arriba:
  - **Roles:** lista con dónde vale cada uno, cuántos permisos tiene y cuántas personas lo tienen, y
    alta de roles personalizados (de grupo, sin permisos al nacer). En la ficha de cada rol, sus permisos
    como casillas agrupadas por módulo; guardar vale al momento para todo el mundo (se sube la versión
    de la caché). Un rol personalizado se borra solo si nadie lo tiene; los del sistema, nunca.
  - **Excepciones:** lista de todas, alta (alias, grupo, permiso, dar o quitar y motivo; si ya había
    una para lo mismo, se sustituye) y baja.
  - **Explicar un permiso:** persona, grupo y permiso → los pasos en lenguaje llano
    (`explicar_permiso`). Una prueba recorre personas, grupos y todos los permisos (con rol
    personalizado y excepciones de los dos tipos) y comprueba que decide igual que `puede()`.
  - *(Pendiente: que el admin de la organización dé excepciones en sus grupos, con
    `permisos.dar_excepciones`, desde la ficha del grupo; y los cometidos, cuando algún módulo los
    declare.)*
- `grupos` ya usa `exigir` para invitar (`grupos.invitar`, por defecto cualquier miembro) y para
  responder a una invitación (`grupos.responder_invitacion`, por defecto el admin del grupo).

### 3.6 Presupuesto de rendimiento

| Regla | Cómo se comprueba |
|---|---|
| Como mucho unas 15 consultas por pantalla, y que no crezcan con el número de filas | Una prueba por pantalla con `assertNumQueries` |
| `jit=off` en PostgreSQL y conexiones persistentes | Ajustes de la base de datos |
| Cálculos por persona en la caché, con versión | Redis |
| Contadores guardados (apoyos, inscritos, votos, recursos) | Se actualizan con eventos_sw, no se cuentan en cada lista |
| Listas de hasta **500 filas** (el superadmin puede bajar el límite): se filtran en el navegador. Con más, en el servidor mientras se escribe (htmx, 300 ms de espera) | Componente común de tabla |
| Pruebas rápidas | Cifrado de contraseñas rápido en las pruebas y factorías pequeñas |
| Herramientas de desarrollo | django-debug-toolbar |

**Cómo se mide (12 de noviembre de 2026).**
- Cada prueba de pantalla hereda de `base.pruebas.PruebaDePantalla` y llama a
  `comprobar_consultas(url, n, crear_mas_datos)`. La ayuda hace una visita de calentamiento y después
  comprueba tres cosas: que la pantalla hace **exactamente** `n` consultas, que `n` no pasa de 15 y que,
  tras añadir más filas con `crear_mas_datos`, sigue haciendo `n`. `crear_mas_datos` solo puede ser
  `None` en pantallas sin listas.
  - *Motivo:* así se comprueban a la vez el tope y que el número no crezca con las filas, y queda escrito
    el coste exacto de cada pantalla.
  - *Descartado:* solo un tope de 15 (no detecta una consulta por fila mientras haya pocas filas) y solo el
    `assertNumQueries` exacto (no comprueba qué pasa con más filas).
- **django-debug-toolbar** (BSD-3) se activa siempre que `DEBUG` esté encendido, salvo en las pruebas.
  Desde el contenedor el navegador no llega por 127.0.0.1, así que no se filtra por dirección.
- En las pruebas (`PROBANDO` en los ajustes), la caché va en memoria y las contraseñas se cifran con
  MD5, que es rápido.

### 3.7 eventos_sw

- **Síncronos:** lo que debe ocurrir en la misma transacción (invalidar la caché, copiar la audiencia).
- **Asíncronos:** notificaciones, correos y Telegram. El aviso se guarda en una «bandeja de salida»
  dentro de la transacción y un trabajador lo procesa (Celery o RQ, por decidir al llegar ahí).

**Cómo funciona (12 de noviembre de 2026).**
- Se emite con `emitir("consultas.cerrada", consulta_id=7, grupo_id=3)` (`eventos_sw/servicios.py`),
  **dentro de `transaction.atomic()`**: fuera de una transacción da error.
  - *Motivo:* sin transacción, un fallo de un receptor dejaría el cambio guardado a medias.
- El nombre debe estar en el `emite` de algún contrato. Los datos son **valores simples** (JSON), nunca
  objetos, porque los asíncronos se guardan en una tabla. Ambas cosas se comprueban siempre.
- Cada receptor recibe los datos como parámetros con nombre (`def copiar(consulta_id, **resto)`). El modo
  (síncrono o asíncrono) lo elige quien escucha, en su `Escucha`.
- **Bandeja de salida:** la tabla `AvisoPendiente`, con una fila por cada escucha asíncrona, guardadas
  todas con una sola consulta. Al entregarse bien, la fila se borra. Si falla, se reintenta a los 1, 2,
  4 y 8 minutos, y al 5.º fallo queda marcada como «fallida» para revisarla a mano (de momento, en la
  trastienda).
- **Trabajador provisional:** la orden `python manage.py procesar_bandeja`, que usa
  `SELECT … FOR UPDATE SKIP LOCKED` para que varios procesos no se pisen. Cuando se decida entre Celery y
  RQ, solo cambiará quién la llama.
  - *Descartado por ahora:* decidir ya Celery o RQ (pieza grande que nadie usa hasta la fase 2) y ejecutar
    los asíncronos en el mismo proceso al guardar (escondería fallos y se comportaría distinto en el
    servidor real).

### 3.8 API

Django Ninja (MIT), que llama a los mismos servicios que las vistas. La usarán el bot, las islas de
JavaScript y una posible aplicación móvil.

---

## 4. Interfaz

- **Todas las pantallas, también las del superadmin, se hacen en la interfaz propia**, con el mismo
  diseño. El panel de Django queda solo como trastienda técnica de emergencia.
- **Ordenador:** menú izquierdo con secciones y subsecciones (plegable) y menú superior con las vistas de
  la sección. El menú conserva su posición al recargar: se navega con htmx y la posición se guarda en el
  navegador.
- **Móvil:** barra inferior con las secciones y, bajo la cabecera, una fila de pestañas deslizable con
  las vistas de la sección.
- **Arriba, en pequeño**, en todas las pantallas: el alias del usuario que ha iniciado sesión.
- **Ayuda «?»** en la cabecera de cada sección. Los textos los declara cada módulo en su contrato.
- **Tema claro u oscuro**, con un icono arriba a la derecha en todas las vistas. Cada persona elige el
  tipo de letra, el tamaño, el color del tema y la densidad (compacta o cómoda). El admin_org puede
  adaptar los colores a su organización.
- **Tipología y fechas en todas las listas** de proyectos y de eventos.
- **Botón «copiar»** en cada campo editable, para pegarlo en otro sitio (por ejemplo, del proyecto de
  preparación al evento de la acción).
- **Selector de etiquetas** en cada módulo donde corresponda.
- **Fragmentos con htmx:** filtros, paginación y formularios devuelven solo lo que cambia. La dirección
  conserva los filtros.
- **Acciones sin salir de la ficha:** panel lateral o ventana para crear, apuntarse, apoyar…
- **Respuesta inmediata** en los botones (voy, voto, mover tarjeta): se cambia en pantalla y se deshace si
  el servidor dice que no.
- **Arrastrar** donde tenga sentido: kanban, calendario, columnas, orden de los puntos.
- **Islas de JavaScript:** calendario (FullCalendar, MIT), kanban (SortableJS, MIT), grafos (Cytoscape.js,
  MIT), mapas (Leaflet, BSD-2, con `referrerPolicy` correcto para OpenStreetMap) y editor (Yjs, MIT).
- **Errores que explican:** si falta un permiso, se dice cuál y quién puede darlo.

**Cómo está hecha la plantilla general (12 de noviembre de 2026).**
- **Librerías servidas por el propio servidor**, instaladas con npm en versiones exactas: Tailwind 4.3.3,
  htmx 2.0.11 y Alpine 3.17.5. `npm run construir` las deja en `static/generado/` (que no se guarda en
  Git y se regenera al crear el contenedor).
  - *Descartado:* el ejecutable suelto de Tailwind (npm hace falta igualmente), Tailwind 3 y htmx 4
    (demasiado reciente y con muchos cambios).
- **El menú no salta porque no se vuelve a pintar.** Los enlaces se siguen con htmx (`hx-boost`), que pide
  solo la zona central (`#zona`) y la sustituye. El servidor sabe que basta con la zona por las cabeceras
  `HX-Request` y `HX-Target: zona`. Las páginas heredan de `interfaz.plantilla`, que vale `base/zona.html`
  o `base/pagina.html` (la página entera, que envuelve la zona). Las vistas no tienen que hacer nada.
  Qué secciones están plegadas, si el menú está plegado y hasta dónde se había bajado se guardan en el
  navegador, para recuperarlo al recargar. El plegado del menú entero es el atributo `data-menu` de
  `<html>` (variante `plegado:` de Tailwind). Lo aplica el script de la cabecera antes de pintar, así
  que no salta al recargar, y la zona central ocupa todo el ancho que queda libre.
  - *Descartado:* cargar siempre la página entera y recuperar después la posición (parpadeo en cada clic y
    se envía todo de nuevo).
- **Botón «atrás»:** htmx no guarda copias de las páginas (`historyCacheSize: 0`). Al volver, pide la
  página entera al servidor. La capa `base.middleware.VariarSegunHtmx` añade `Vary: HX-Request, HX-Target`
  para que el navegador no confunda la zona suelta con la página.
- **La sección y la vista actuales salen de la dirección:** el registro sabe a qué entrada del menú lleva
  cada ruta (`registro.rutas`). Lo usa `base/contexto.py`, que da a todas las plantillas el menú, la
  sección, las vistas, la ayuda y el título, sin ninguna consulta.
- **La ayuda «?» viene ya en la página**, en una ventana de Alpine: abrirla no cuesta ninguna petición.
- **Tema, letra y densidad** son atributos de `<html>` (`data-tema`, `data-letra`, `data-densidad`), cada
  uno con tres valores (ampliado el 12 de noviembre de 2026, a petición de la persona usuaria):
  - tema **claro**, **día** (claro con más contraste: fondo blanco y la escala de grises redefinida
    más oscura, para que los recuadros se distingan bien) y **oscuro**. El botón de la cabecera pasa
    por los tres;
  - letra **pequeña**, **normal** y **grande**;
  - densidad **cómoda**, **compacta** y **supercompacta**.
  Un script en la cabecera de la página los aplica antes de pintar, para que no haya destello. La letra
  grande sube el tamaño base (todo va en `rem`) y la densidad compacta reduce `--spacing` (Tailwind
  calcula con ella todos los espacios). Se guardan en el navegador y, con sesión, también en la cuenta
  (apartado 7.1).
- **Color de marca** `--color-marca` (clases `text-marca`, `bg-marca`…), que cada organización podrá
  redefinir.
- **Sección «Inicio» de demostración** en el contrato de `base`, con las vistas «Estructura» y
  «Componentes», mientras no haya otros módulos.

**Menú en tres niveles (13 de noviembre de 2026, a petición de la persona usuaria).** El menú izquierdo
tiene **al menos dos niveles** (sección y subsección, con `EntradaDeMenu.subsecciones`), y el tercer
nivel son las **vistas del menú superior** de cada subsección. Ejemplo: «Desarrollo y mantenimiento» →
«Pruebas» (izquierda) → «Importar grupos» · «Importar usuarios» (arriba). Al entrar en una subsección,
su sección se abre sola en el menú izquierdo. Cuando no esté claro en qué nivel va algo, se pregunta.
La entrada en la que se está lleva fondo; la sección que la contiene, solo el texto en color (más
discreto, a petición de la persona usuaria).

**Iconos de colores (13 de noviembre de 2026, a petición de la persona usuaria).** Cada sección y cada
subsección lleva un icono distinto y un color distinto (`EntradaDeMenu.icono` y `EntradaDeMenu.color`),
para reconocerlas de un vistazo. El icono es un símbolo de texto de un solo color («⇄», «✉»), pintado
con su color sobre un fondo del mismo color muy claro (más claro aún en el tema oscuro). Tras el símbolo
va `&#xFE0E;`, que pide dibujarlo como texto y no como emoji (un emoji no toma el color). Si dos entradas
repiten icono o color, o una no tiene icono, `manage.py check` da el error `base.E005`. *Descartado:*
emoji de colores (no se pueden teñir y cada sistema los dibuja distinto) y una librería de iconos SVG
(otra dependencia, por ahora innecesaria).

**Tabla filtrable (12 de noviembre de 2026).**
- **Componente propio** (`base/tablas.py` y `base/templates/base/tabla.html`). La vista crea una `Tabla`
  con sus columnas (`Columna`), su fuente (`FuenteDeConsulta` para un QuerySet o `FuenteDeLista` para
  datos en memoria) y sus desplegables de categoría (`Filtro`). La plantilla solo la incluye.
  - *Descartado:* django-tables2 y django-filter (no filtran en el navegador ni cambian solos de modo, y
    habría que rehacer sus plantillas igualmente) y una isla de JavaScript (las islas se reservan para
    calendario, kanban, grafos, mapas y editor).
- **El modo se decide con una sola consulta:** se piden 501 filas. Si llegan 500 o menos, van todas a
  la página y el componente `tablaLocal` de Alpine filtra y ordena en el navegador, sin peticiones. Si
  llega la 501, se filtra en el servidor: htmx manda la búsqueda 300 ms después de dejar de escribir y
  se cargan 100 filas, con un botón **«Mostrar más»** (por ahora, en lugar de páginas numeradas).
  - Coste: 1 consulta en el navegador; en el servidor, 3 la página entera (tanteo, recuento y filas) y
    2 cada petición de htmx.
- **Búsqueda sin tildes ni mayúsculas, palabra a palabra** (deben aparecer todas). En el navegador,
  con `normalizar()`, que hace lo mismo en Python y en JavaScript. En el servidor, con la extensión
  `unaccent` de PostgreSQL (migración `base/0001_unaccent`). Se busca en los mismos campos
  (`campos_de_busqueda`) en los dos modos.
- **Filtro por columna** (12 de noviembre de 2026, a petición de la persona usuaria): bajo el título de
  cada columna hay un cuadro de texto; la fila se ve si la celda contiene lo escrito, sin importar tildes
  ni mayúsculas. Se combina con el buscador general (que se mantiene) y con los desplegables. Las
  columnas pueden desactivarlo con `Columna(filtrable=False)`.
  - En el navegador y con `FuenteDeLista` se compara con el texto tal como se ve (fechas DD/MM/AAAA).
    Con `FuenteDeConsulta`, los campos de texto usan `unaccent` y los demás se comparan como texto de
    PostgreSQL (las fechas, AAAA-MM-DD).
  - En el servidor, escribir en un filtro sustituye **solo las filas** (`tabla-<id>-cuerpo`) y el recuento
    (con `hx-swap-oob`), no la cabecera, para no perder el cuadro en el que se escribe. Cambiar el orden
    sí sustituye la tabla entera. `hx-sync` descarta una respuesta vieja si llega una petición nueva.
- **Los filtros van en la dirección**, con el identificador de la tabla delante (`eventos-q`,
  `eventos-orden=-fecha`…), así que caben varias tablas en una página. Los parámetros que no
  corresponden (una columna que no existe, una categoría que no está entre las opciones) se ignoran.
  - *Limitación conocida:* con dos tablas en la misma página, filtrar en el servidor una de ellas
    reescribe la dirección solo con sus filtros. No afecta a las pantallas con una sola tabla.

**Botón «copiar» y explicación de cada campo (12 de noviembre de 2026).**
- **Automático en todos los formularios:** `FORM_RENDERER = "base.formularios.Renderizador"` pinta cada
  campo con `base/templates/base/campo.html`: etiqueta, campo, botón «copiar», explicación
  (`help_text`, siempre visible) y errores. La clase `CampoLigado` decide qué campos llevan botón: todos,
  salvo casillas, opciones, ficheros, contraseñas y campos ocultos.
  - *Descartado:* una etiqueta `{% boton_copiar %}` puesta a mano (es fácil olvidarla).
- Copia con el portapapeles del navegador y, si no lo permite (por ejemplo, sin https desde la red
  local), con el método antiguo. En un desplegable copia el texto de la opción elegida.

---

## 5. Roles y cometidos

**Cinco roles** fijos: superadmin, admin_org, admin_grupo, usuario y público. Todo lo demás son
**cometidos** de una cosa concreta (proyecto, debate, evento u organización): portavoz, coordinación,
facilitación, toma de acta, papeles de una acción, custodio de identidad…

**Caducidad de admin_org y admin_grupo:** la fija el superadmin en la configuración. Por defecto es
**indefinida**. Para no perder la horizontalidad, el grupo ve cuánto tiempo lleva cada admin, y **cada 4
meses** sus miembros reciben la pregunta «¿renovamos a los admin?».

### 5.1 Superadmin

Una marca en el usuario, no un rol de grupo.
- Ve todo y puede crear, editar y borrar cualquier cosa. También puede **podar** contenido para ahorrar
  espacio (ver apartado 14.3).
- **Excepción:** no puede leer desde la interfaz el **contenido personal privado** (proyectos y tareas
  personales) ni las **conversaciones entre otras personas**. Solo puede hacerlo ante una denuncia,
  dejando registro y avisando a las personas afectadas, igual que con el sobre de identidad.
- Valida la identidad (de momento, con un botón). Admite usuarios en grupos y organizaciones.
- Crea organizaciones y nombra a su admin_org. Crea grupos y nombra a su admin_grupo.
- Aprueba el borrado de grupos y la incorporación de lugares propuestos.
- Fija los límites generales (debates, apoyos, caducidades, limpieza, visibilidad).
- Ajusta los permisos de cada rol.
- Envía mensajes personalizados a un usuario o a un conjunto filtrado (p. ej., «todos los usuarios sin
  lugar elegido»).
- Edita la portada pública.

**Sus pantallas** (menú izquierdo):
- **Usuarios**
  - Personas (bóveda): «Persona 3f2a9c1e», estado de validación y método, y pases emitidos. El nombre
    solo se ve dentro de la ficha.
  - Usuarios: ficha tipo cuadro de mando con sus grupos (en árbol), lugar, correo alternativo, proyectos,
    tareas y eventos; y «activado el día X».
- **Organizaciones y grupos**
  - Árbol organización → grupos → subgrupos, con ámbito geográfico y número de usuarios.
  - Mapa: al pulsar, los datos aparecen a la derecha con un enlace.
  - Ficha con datos, subgrupos, usuarios por rol (filtrable) y recuento de talentos.
  - Peticiones de borrado y relaciones entre grupos (lista y grafo).
- **Lugares:** lista, mapa, importación y propuestas pendientes.
- **Tipologías y plantillas** de proyectos, de eventos y de documentos.
- **Debates:** lista, base de conocimiento (búsqueda por palabras y etiquetas) y configuración.
- **Proyectos y tareas:** árbol de proyectos, con búsqueda por nombre, grupo, palabras y etiquetas.
- **Lo que es público:** lista de todo lo publicado, para ocultarlo si hace falta.
- **Moderación:** avisos, denuncias y ocultaciones.
- **Roles y permisos.**
- **Configuración:** servidores de correo, permisos de los admin, aspecto, límites, visibilidad, limpieza y
  caducidad de los admin.
- **Ayuda y referencias:** instrucciones de desarrollo, estructura del software, pendientes y procesos de
  registro y validación (los documentos de `docs/`).
- **Salud del sistema:** consultas y tiempos por pantalla, espacio ocupado y usuarios pendientes de
  revalidar.

### 5.2 Admin_org

No se hereda: se asigna por organización.
- Crea grupos y subgrupos, edita sus datos y pide borrarlos (lo aprueba el superadmin).
- Admite usuarios en la organización, siempre dentro de un grupo. Ve sus datos de usuario, pero no su
  lugar.
- Ve **qué talentos hay** en la organización y cuántas personas los ofrecen, **nunca quién**. Puede
  **pedir un talento**: la petición llega a quienes lo comparten y cada persona decide si responde.
- Crea proyectos, eventos, debates y consultas **de toda la organización**, que llegan a todos sus usuarios.
- Avisa, denuncia y **oculta de forma provisional** (apartado 5.6).
- Ajusta los límites dentro de los del superadmin (solo puede ser más estricto), los niveles de
  visibilidad que se ofrecen y los colores de su organización.
- Envía mensajes a los usuarios de su organización.
- Ve la lista de lo que se ha hecho público en su organización.
- Sus pantallas son como las del superadmin, sin datos sensibles y sin poder borrar usuarios.

### 5.3 Admin_grupo: cuida, no filtra

- Gestiona la estructura: datos del grupo, quién entra y quién sale, subgrupos, relaciones con otros
  grupos y roles. Puede pedir que se borre el grupo.
- Tiene 1 voto en la admisión de usuarios en su grupo.
- Avisa, denuncia y **oculta de forma provisional** (apartado 5.6).
- Designa a otras personas para facilitar un debate, además de quien lo abrió.
- Amplía la visibilidad de los recordatorios del calendario de su grupo a los grupos padre y abuelo.
- Envía mensajes a los usuarios de su grupo y ve la lista de lo que su grupo ha hecho público.
- Para todo lo demás es una persona más: también necesita apoyos para abrir debates y convocar reuniones.
- **Cada acción suya queda en un registro visible** para todo el grupo.

### 5.4 Usuario

- Participa en todo lo que llega de su grupo y de los grupos que lo contienen.
- **Solicita** abrir debates y convocar reuniones (apartado 6).
- Crea proyectos, tareas, eventos (que no sean reuniones), consultas y recordatorios del calendario. Edita lo
  suyo y aquello en lo que tiene un cometido.
- Tiene **tareas personales** y **proyectos personales** (marcados como «privado e individual»): no los
  ve nadie más y no se publican.
- Decide **con qué grupos y proyectos comparte cada talento**.
- Elige su **lugar** de la lista, o **propone uno nuevo** con sus datos (lo incorpora el superadmin).
- Escribe a su admin o al superadmin y empieza una conversación.
- Asume cometidos que rotan: facilitación, toma de acta, coordinación, papeles de una acción.

### 5.5 Público (sin iniciar sesión)

- Portada de la plataforma para elegir organización, y portada de cada organización.
- Banco de información pública de cada organización (apartado 15).
- Nunca ve alias.

### 5.6 Moderación: avisos y ocultación provisional

- Admin_grupo y admin_org pueden **avisar** de una infracción y **ocultar de forma provisional** un
  contenido.
- Lo ocultado **no desaparece**: sigue visible para quienes ya tenían acceso, **en otro color y con un
  aviso** que dice quién lo señaló y por qué.
- Siempre se avisa a quien lo escribió, al admin_org y al superadmin. Queda en el registro del grupo.
- El superadmin resuelve: retira la ocultación o borra el contenido.

### 5.7 Custodio de identidad (cometido de organización, para la versión 2 de la bóveda)

Persona que guarda **un trozo de la llave** que abre los sobres de identidad. Solo sirve para eso: no ve
datos, no modera y no tiene más poder en la plataforma. Para abrir un sobre ante una denuncia grave
hace falta que lo aprueben al menos 5 custodios de grupos distintos. Ver
[registro-y-validacion.md](registro-y-validacion.md), apartado 10.

---

## 6. Solicitudes con apoyos

**Qué la necesita:**
- abrir un **debate**;
- convocar una **reunión**;
- dentro de un debate, **abrir una opción nueva** o **un debate nuevo a partir de un argumento** (apartado 11).

Lo demás se crea sin apoyos.

**Cómo funciona:**
1. Desde la zona de debates o de reuniones, la persona rellena el formulario normal y añade una
   **descripción**, una **justificación** y una **fecha de caducidad**.
2. Cada persona del grupo de destino (también las de sus subgrupos) la ve en su **inicio** («Solicitudes
   pendientes») y en el menú **«Solicitudes»**, con un contador. Puede **aceptarla** (apoyo) o
   **rechazarla**, y retirar su respuesta mientras la solicitud está pendiente.
3. Si es una reunión y la persona la acepta, se le pregunta a continuación si asistirá.
4. Cuando se alcanzan los apoyos necesarios, el debate o la reunión se crea solo y se avisa.
5. Si llega la fecha de caducidad sin apoyos suficientes, caduca. Quien la pidió puede cancelarla antes.

**Apoyos necesarios** (los ajustan el superadmin y el admin_org): **2** en el propio grupo, **5** en el
grupo padre y **10** en el abuelo. Dentro de un debate, 2 por defecto. Quien solicita no cuenta como
apoyo. Los rechazos no vetan.

**Qué se ve:** los apoyos, con el alias de quien apoya; los rechazos, **solo como número**, para evitar
presiones y roces.

**Pestaña «Solicitudes» del grupo:** dos listas, **pendientes** (con «2 de 5» y los botones) y
**pasadas** (aceptadas, canceladas y caducadas).

**Tablas:** `Solicitud` (grupo, tipo, datos del formulario en JSON, descripción, justificación,
solicitante, apoyos_necesarios, caduca_el, estado, objeto_creado como ancla, contadores) y `Apoyo`
(solicitud, usuario, acepta o rechaza; único por persona y solicitud).

---

## 7. Identidad y validación

Resumen; el detalle y las explicaciones están en [registro-y-validacion.md](registro-y-validacion.md).

- Bóveda y plataforma en **dos bases de datos sin ninguna columna que las una**. En la bóveda se usan
  huellas HMAC, solo fechas (nunca horas) e identificadores aleatorios. Las listas muestran
  «Persona 3f2a9c1e».
- Alta con **pase de firma ciega** (RFC 9474), un pase por persona. **Nadie ve qué pase usó cada usuario.**
- Cinco métodos para validar la identidad: dominio de correo, documentos firmados, documentos y dominio,
  alta por el superadmin y validación colectiva.
- **Validar la identidad** (en la bóveda) no es lo mismo que **admitir en un grupo** (en la plataforma).
  Admiten el superadmin, el admin_org y el admin_grupo (con 1 voto), viendo solo el alias. **Nadie
  pertenece a una organización sin pertenecer a un grupo de ella.**
- Validación del **lugar** de cada usuario por 3 avales. El lugar solo lo ven la propia persona, el
  superadmin y quienes avalan.
- **Sobre de identidad:** en la versión 1 de la bóveda, una sola llave (la del superadmin), con registro y
  aviso de cada apertura. En la versión 2, custodia repartida (apartado 5.7).
- **Rondas de revalidación** bajo demanda, con motivo público.
- **Mientras no esté programado el alta real**, el superadmin crea los usuarios a mano (como en la
  versión 1).

### 7.3 Etiquetas (13 de noviembre de 2026)

- **Qué son:** palabras sueltas o grupos de dos o tres palabras para encontrar información útil
  («huelga», «local nuevo»), con **palabras relacionadas** (sinónimos): buscar cualquiera de ellas
  encuentra lo etiquetado. Se comparan sin mayúsculas ni tildes.
- **Forma fija (13 de noviembre de 2026, petición de la persona usuaria):** toda etiqueta, y sus palabras
  relacionadas, se guarda con la **primera letra en mayúscula, el resto en minúsculas y sin tildes**
  («REUNIÓN general» → «Reunion general»). La **ñ se conserva** («Año», no «Ano»), porque es otra letra.
  El selector las pasa a esa forma al añadirlas (se ven ya como se guardarán), el modelo al guardar
  (también desde la trastienda) y la búsqueda compara sin tildes ni mayúsculas, así que buscar «Difusión»
  encuentra «Difusion». Función `forma_de_frase` en `base/tablas.py` (y `formaDeFrase` en `interfaz.js`).
  Una migración pasó a esta forma las que ya había. *Descartado:* guardarlas tal como se escriben (salían
  «huelga», «Huelga» y «HUELGA» mezcladas en las listas).
- **Quién las crea (1A):** cualquiera, al usarlas. El selector propone las que ya existen mientras se
  escribe (también por sus relacionadas), para no duplicar. El admin de la organización
  (`etiquetas.ordenar`) y el superadmin pueden **fusionar** repetidas (las otras pasan a ser relacionadas
  de la que se queda), renombrar y poner relacionadas. De momento, en la trastienda («Clasificación»).
- **De cada organización (2A):** las de una organización no se sugieren ni se usan en otra (una etiqueta
  ya cuenta algo). El superadmin crea **etiquetas comunes** (sin organización), que sirven en todas. Si
  existe una común igual, se usa la común. *Descartado:* una sola base común para todas (como decía el
  diseño), por privacidad.
- **Tablas:** `Etiqueta` (organización o común, nombre, relacionadas, con sus formas normalizadas) y
  `EtiquetaDe` (etiqueta + ancla de lo etiquetado). Servicios: `sugerir`, `obtener_o_crear`, `etiquetar`,
  `etiquetas_de`, `buscar` (también por relacionadas) y `fusionar`.
- **Selector:** genérico en `base` (`SelectorDePalabras` y `CampoDePalabras`): pastillas con ×,
  sugerencias pedidas al servidor mientras se escribe, Intro o coma para añadir, borrar para quitar la
  última. `etiquetas.formularios.CampoDeEtiquetas` lo usa con las sugerencias de la organización y las
  reglas de las etiquetas.

### 7.2 La bóveda, fase 1 (13 de noviembre de 2026)

- **Base aparte:** las tablas de `boveda` van solo a la base «boveda» y las demás solo a la de la
  plataforma (`config/enrutador.py`). El enrutador **prohíbe cualquier relación** entre tablas de las dos
  bases. Las tablas de la bóveda no están en la trastienda (su historial guardaría horas exactas en la
  plataforma).
- **Tablas:** `Persona` (identificador al azar, nombre real, correo oficial mientras está pendiente,
  huella del correo, número de la organización, estado, método y días), `PaseEmitido` (persona, ronda y
  día; «provisional» si se marcó en el alta por el superadmin) y `DominioPermitido` (número de la
  organización y dominio).
- **Huellas:** HMAC-SHA256 con la clave `BOVEDA_CLAVE_HMAC`, en una variable de entorno, fuera de las
  bases (2A). Sin mayúsculas ni espacios alrededor.
- **Alta provisional (1A):** el superadmin da de alta a la persona (nombre, correo y organización) y
  queda pendiente; en su ficha puede corregir los datos y **validarla** (método «superadmin»). Al
  validarla: se borra el correo (queda su huella), y su pase se marca como emitido (ronda 0,
  provisional). El alias se crea aparte, sin enlace.
- **Nombre y correo (1A, 13 de noviembre de 2026):** el nombre real se ve y se edita en la ficha (nunca en
  las listas: «Persona 3f2a9c1e»). El correo, solo mientras está pendiente; si hay que cambiarlo después,
  se escribe uno nuevo y la persona vuelve a quedar pendiente, con nueva huella (su pase sigue emitido).
  *Descartado:* guardar el correo siempre (una bóveda robada daría nombres y correos juntos).
- **Dominios permitidos por organización (3A):** se guardan en la bóveda (con el número de la
  organización: entre las dos bases no hay claves ajenas). Si una organización tiene dominios, el correo
  debe ser de uno de ellos (ya en el alta provisional). Por usabilidad se ven también en la ficha de la
  organización, con una nota de que se guardan en la bóveda. *(En las pantallas de organizaciones de la
  aplicación, cuando existan, igual.)*
- **Origen de cada alias (2):** «alta directa» (a mano o importado) o «con pase» (registro real). Nunca se
  dice qué persona hay detrás.
- **Pantallas (4):** sección **Usuarios** del superadmin: «Bóveda (personas reales)» (arriba: Personas ·
  Dominios permitidos) y «Alias (usuarios de la app)» (arriba: Lista). En la ficha de cada alias se ven
  todos sus grupos y se puede activar o desactivar la cuenta y **hacerle superadmin**. Nadie puede quitarse
  el superadmin a sí mismo ni desactivarse.
- **Permisos:** `boveda.ver` y `administracion.usuarios`, sin roles por defecto: solo el superadmin.

### 7.1 El módulo `usuarios` (12 de noviembre de 2026)

- **Modelo propio sobre `AbstractBaseUser`** con lo justo: `alias` (con el que se entra),
  `correo_alternativo` (opcional), `es_superadmin`, `activo`, `activado_el` (**solo el día**, nunca la
  hora) y las preferencias `tema`, `letra` y `densidad`.
  - *Motivo:* ningún campo invita a guardar datos reales, y se respeta la regla de solo fechas.
  - *Descartado:* `AbstractUser` (trae nombre, apellidos, correo y la hora exacta del alta).
  - Superadmin es una marca del usuario (apartado 5.1). Solo él entra en la trastienda.
- **Alias:** de 3 a 30 caracteres (letras, números, espacio, `.`, `_` y `-`). **No se distinguen
  mayúsculas ni tildes:** si existe «María», no se puede crear «maria». Se guarda el alias normalizado
  en una columna única (`alias_normalizado`) y se entra escribiéndolo de cualquiera de las dos formas.
  - *Descartado:* distinguir solo mayúsculas (dejaría suplantar con «Maria» a «María»).
- **Nada se ve sin sesión**, salvo la pantalla de entrada (`usuarios/middleware.py`, basada en
  `LoginRequiredMiddleware`). Lo público (fase 8) se marcará con `@login_not_required`.
- **Sesiones en la caché con respaldo en la base** (`cached_db`): leer la sesión no cuesta consultas.
  Cada pantalla con sesión cuesta 1 consulta de base: cargar el usuario.
- **Preferencias en la cuenta**, con el navegador como respaldo sin sesión. El servidor las pone en
  `<html>` al pintar, sin destello. El plegado del menú se queda solo en el navegador, porque depende de
  la pantalla.
  - *Descartado:* solo en el navegador (no viajan entre el móvil y el ordenador).
- **Esta pieza incluye:** entrar (alias y contraseña), salir, «Mi cuenta → Preferencias» y «Mi cuenta →
  Contraseña» (cualquiera puede cambiar la suya). Contraseñas cifradas con **Argon2**.
- **Códigos de recuperación:** se dejan para la fase 8, con la bóveda real, de la que dependen. Hasta
  entonces, quien olvide su contraseña se la pide al superadmin.
- **Datos de ejemplo:** el módulo `ejemplos` aporta ya la orden `python manage.py ejemplos crear|borrar`,
  que llama a los `datos_de_ejemplo` de cada contrato en el orden de las capas y solo funciona en
  desarrollo. Los usuarios de ejemplo son **animales y árboles**; el superadmin es **superadmin** (antes «Águila»;
  cambiado el 13 de noviembre de 2026 para que no haya dudas). Borrar los datos de ejemplo no lo toca. Todos
  tienen la contraseña `M3n0sL3ctiv4s` (a petición de la persona usuaria).

---

## 8. Organizaciones, grupos, lugares y talentos

### 8.1 Organizaciones y grupos

- Las **organizaciones son independientes** entre sí. La jerarquía existe solo entre grupos.
- Toda organización tiene **al menos un grupo**.
- **Relaciones entre grupos** de tipo libre, que se ven en un grafo. Solo «contiene» afecta a los
  permisos (tabla de cierre).
- Cada usuario tiene una **asamblea base** (su grupo más local).
- Borrar un grupo: lo pide un admin y lo aprueba el superadmin.
- **Proyectos conjuntos entre organizaciones** (12 de noviembre de 2026, a petición de la persona
  usuaria). En general, la comunicación es solo entre personas que comparten grupo. Pero a veces grupos
  de organizaciones distintas necesitan un proyecto común: un grupo crea el proyecto e **invita a un
  grupo de otra organización**. Una vez aceptada la invitación, las personas del proyecto pueden
  **comunicarse entre ellas** dentro del proyecto. Es una excepción a la independencia de las
  organizaciones y debe quedar limitada al proyecto (no abre nada más de cada organización).
  - **Decidido (12 de noviembre de 2026): invitación de grupo a grupo, colgada de lo invitado.** El grupo
    que crea el proyecto invita a un grupo de otra organización (`InvitacionDeGrupo`, con un ancla al
    proyecto). Al aceptarla, ese grupo entra en la audiencia del proyecto y el chat del proyecto llega a
    quienes lo ven. Nadie cambia de organización ni de grupo.
    - *Descartado:* un «grupo puente» con miembros de las dos organizaciones (rompe que cada grupo es de
      una sola organización y deja una vía permanente entre ellas).
  - **La acepta o rechaza el admin_grupo del grupo invitado** (o el superadmin), y se avisa a todo el
    grupo (cuando exista `comunicaciones`). *Descartado:* una solicitud con apoyos (llega en la fase 2).
  - Solo se invita a grupos de **otra** organización; dentro de la misma basta con la audiencia. Invita
    cualquier miembro del grupo que invita (lo afinará `permisos`), y cualquiera de ellos puede retirarla.
  - *(por diseñar: qué audiencia tiene el proyecto y cómo se comunican, con `audiencias`, `proyectos` y
    `comunicaciones`)*
- **Asamblea base: una por persona en toda la plataforma** (12 de noviembre de 2026). Es donde se valida
  en la bóveda; con dos, una persona podría validarse dos veces. *(revisable: la persona usuaria no lo ve
  del todo claro; pasar a una por organización solo cambia una restricción de la tabla.)*

**Cómo está hecho `grupos` (12 de noviembre de 2026).**
- `Organizacion`; `Grupo` (con `padre`, de la misma organización y sin círculos; no cambia de
  organización); `Contencion`, la **tabla de cierre** (un par por cada «antecesor contiene a
  descendiente», también el grupo consigo mismo), que mantiene el propio `Grupo.save()` al crear o mover
  un grupo; `Pertenencia` (rol `usuario` o `admin_grupo`, desde qué día, asamblea base);
  `AdminDeOrganizacion` (debe estar en algún grupo de la organización; deja de serlo al salir del
  último); `RelacionEntreGrupos` (libre, para el grafo; no afecta a permisos); `InvitacionDeGrupo`.
- Los cambios se hacen con `grupos/servicios.py` (`crear_organizacion`, que crea también su primer
  grupo; `crear_grupo`, `admitir`, `sacar`, `cambiar_rol`, `cambiar_asamblea_base`,
  `nombrar_admin_de_organizacion`, `invitar`, `responder_invitacion`, `retirar_invitacion`), que avisan
  con eventos_sw (`grupos.pertenencias_cambiadas`, `grupos.estructura_cambiada`,
  `grupos.invitacion_*`) para que `permisos` y `audiencias` rehagan sus cálculos.
- `grupos_de(usuario)`: los grupos de los que es miembro, también los que contienen a los suyos, con una
  sola consulta.
- **Niveles sin límite.** Un grupo puede contener subgrupos a cualquier profundidad. Lo normal serán tres
  (grupo general → grupo de zona → grupo de centro), pero puede haber más; la pertenencia se hereda hacia
  todos los que están por encima. *(Si hiciera falta nombrar los niveles, se añadiría después un tipo de
  grupo; de momento no.)*
- **Datos de ejemplo:** organizaciones con nombres de ríos ibéricos («ORG Tajo», «ORG Ebro», «ORG Duero»,
  «ORG Guadalquivir»). El grupo general de cada una es el propio río («GRU Tajo») y dentro van sus
  afluentes y los afluentes de estos, hasta cinco niveles («GRU Ebro › GRU Segre › GRU Cinca › GRU Ésera
  › GRU Isábena»), a petición de la persona usuaria. Cada usuario de ejemplo tiene su asamblea base;
  algunos están en dos organizaciones.
- **Camino y orden de árbol.** Cada grupo se muestra con su camino completo («ORG Tajo › GRU Tajo › GRU
  Jarama › GRU Henares»), calculado con la tabla de cierre dentro de la misma consulta
  (`Grupo.objects.con_camino()`). Para listar en orden de árbol (cada grupo tras su padre, hermanos por
  orden alfabético sin tildes) se usa una clave aparte (`en_orden_de_arbol()`), porque PostgreSQL ordena
  el texto según el idioma y no tiene en cuenta los signos como «›».

**La trastienda, reordenada (12 de noviembre de 2026, a petición de la persona usuaria).** Aunque es solo
para emergencias, debe entenderse la jerarquía:
- Secciones en este orden (`config/trastienda.py`): **Usuarios** (usuarios y pertenencias),
  **Organizaciones y grupos** (organizaciones, grupos, relaciones e invitaciones), **Admins** (de
  organización y de grupo, juntos) y **Funcionamiento interno**. Lo que no esté en la lista sale en
  «Otros».
- Se quita la tabla «Grupos» de Django (Autenticación y autorización): son grupos de permisos del panel,
  no tienen nada que ver con los de las asambleas y confundían.
- Cada pantalla lleva un texto de ayuda (qué muestra y qué se puede gestionar), con `base/trastienda.py`.
- Ficha de usuario: sus pertenencias directas y la lista de todos sus grupos, también los heredados, y de
  qué es admin. Ficha de grupo: su camino, todos sus subgrupos, sus miembros directos y los que le llegan
  de sus subgrupos. Los desplegables de grupos muestran el camino completo, en orden de árbol.
- **Admins de grupo** es otra forma de ver las pertenencias con rol de admin (modelo «proxy»
  `AdminDeGrupo`). Nombrar a alguien que ya está en el grupo le cambia el rol, sin duplicar nada.
- **Botones de las fichas** (13 de noviembre de 2026, a petición de la persona usuaria): «Guardar» (guarda
  y vuelve a la lista), «Guardar y continuar editando» (guarda y se queda), «Cancelar» (no guarda y vuelve
  a la lista, con sus filtros) y «Eliminar». Se quita «Guardar y añadir otro» de Django, que confundía.
  Las listas de casillas (los permisos de un rol) ocupan todo el ancho, una opción por línea, agrupadas
  por módulo y con el código aparte (`base/static/trastienda/trastienda.css`).

**Sección «Desarrollo y mantenimiento» (13 de noviembre de 2026, a petición de la persona usuaria).** Es la
«Ayuda y referencias» del apartado 5.1, con otro nombre. Módulo `mantenimiento` (capa funcional, porque
usa `permisos`), con el permiso `mantenimiento.ver`, que de entrada solo tiene el superadmin.
- **Documentación:** los documentos de `docs/` convertidos en páginas con Python-Markdown 3.11.2
  (BSD-3), con un índice a la izquierda, tablas y código con estilo propio (clase `documento` en
  `entrada.css`) y los enlaces entre documentos llevados a sus páginas. Se leen del disco, así que siempre
  están al día; la conversión se guarda en memoria mientras el fichero no cambie.
  - *Descartado:* el complemento de tipografía de Tailwind (otra dependencia para unas pocas reglas).
- **Trastienda:** una página que explica qué es y un botón que la abre (sin htmx, porque es otra
  aplicación).
- **Organización en tres niveles** (13 de noviembre de 2026): subsecciones «Ayuda y documentación»
  (arriba, una pestaña por documento), «Pruebas» (arriba, «Importar grupos» e «Importar usuarios») y
  «Trastienda».

**Importación masiva de grupos y usuarios (13 de noviembre de 2026, a petición de la persona usuaria).**
En «Desarrollo y mantenimiento → Pruebas». Solo para el superadmin.
- **Plantillas en formato LibreOffice (.ods)**, que se descargan con una hoja «Datos» (cabecera en
  negrita, filas de ejemplo y desplegables para el rol y los sí/no) y una hoja «Instrucciones». Se puede
  subir .ods o .csv. Se escriben y se leen con código propio (`base/hojas.py`, librería estándar).
  *Descartado:* .xlsx de Microsoft (la persona usuaria usa LibreOffice) y librerías externas (odfpy,
  pyexcel), que harían falta solo para esto.
- **En dos pasos (2A):** subir → **vista previa** con lo que se crea, lo que ya existe, avisos y errores
  por fila → **confirmar**, todo o nada. Con algún error no se puede confirmar. Entre los dos pasos, el
  plan se guarda en la sesión, sin contraseñas en claro (ya cifradas).
- **Grupos:** columnas Organización, Grupo, Grupo padre y Localización. El orden de las filas da igual;
  un padre vacío es un grupo principal; la organización que no existe se crea; un grupo que ya existe no
  se toca (si el fichero le pone otro padre, se avisa); se detectan padres inexistentes y círculos. La
  localización va al «ámbito geográfico» (cuando lleguen los lugares, se enlazará).
- **Usuarios:** columnas Alias, Contraseña, Organización, Grupo, Rol, Asamblea base, Admin de la
  organización y Correo alternativo. Una fila por grupo (varias filas por alias). Rol vacío = usuario
  normal. La contraseña basta en una fila y se comprueba con las reglas de contraseñas; si el alias ya
  existe, no se cambia (cada persona la cambia en «Mi cuenta»). **Asamblea base opcional:** si no se
  marca ninguna, la primera fila del alias, salvo que ya tenga una. El grupo debe existir.
- **Interruptor «Permitir el alta masiva de usuarios»** (`AjustesDeMantenimiento`), apagado al
  empezar: crea alias sin pasar por la bóveda, así que es para el periodo de pruebas.
- **«Pruebas → Datos de ejemplo»** (13 de noviembre de 2026): botones para crear y borrar los datos de
  ejemplo de todos los módulos (lo mismo que `python manage.py ejemplos`). Borrar no toca al superadmin.
  Solo con DEBUG encendido. Borrar pide confirmación.
- **Varios superadmins:** cualquier usuario puede ser superadmin (casilla «Superadmin» de su ficha, de
  momento en la trastienda), para repartir el trabajo.
- **El menú oculta las secciones sin permiso.** `EntradaDeMenu.permiso` ya existía; ahora `base` pregunta
  a una función que le presta `permisos` al arrancar (`registrar_comprobador_de_permisos`), porque `base`
  no puede importar `permisos`. Se mira si la persona tiene el permiso en alguna parte
  (`puede_en_alguna_parte`). Desde el 13 de noviembre de 2026, también las subsecciones (por ejemplo,
  «Árbol» de «Organizaciones y grupos»): `base/contexto.py` apunta las que no se pueden ver en
  `interfaz.ocultas` y la plantilla del menú no las pinta.

**Sección «Organizaciones y grupos» (13 de noviembre de 2026, decisiones 1A, 2A y 3A de la persona
usuaria).** Vistas en `grupos/views.py`; qué ve cada cual, en `grupos/acceso.py`.
- **Una sola sección para todo el mundo (1A).** Cada persona ve sus grupos y lo que administra, y los
  botones dependen de sus permisos. *Descartado:* una sección del superadmin y otra «Mi organización»
  para los admins (código repetido), y una sola pantalla con pestañas sin subsecciones (no se verían de
  un vistazo las invitaciones pendientes).
- **Subsecciones:** «Mis grupos» (todas las personas: sus grupos en árbol por organización, con los
  heredados en gris, su asamblea base y su rol; es importante para saber dónde está cada cual, porque
  una persona puede estar en varios grupos de la misma organización), «Árbol» (solo quien administra
  algo, permiso nuevo `grupos.ver_arbol`: el superadmin ve todo, el admin de la organización la suya y el
  admin de un grupo su rama; con ámbito, número de personas y admins, y la lista de organizaciones),
  «Relaciones» (submenú propio) e «Invitaciones (N)» (submenú propio).
- **Fichas** de grupo y de organización, que cuelgan de la sección (`EntradaDeMenu.otras_rutas`).
  - Grupo: camino con enlaces, datos, quién lo cuida (admins del grupo y de la organización, con el
    tiempo que llevan), subgrupos con su número de personas, miembros (también los de los subgrupos,
    en tabla filtrable) y, para quien lo administra, editar, crear subgrupos, admitir por alias, sacar y
    cambiar el rol. Hacer admin a alguien (o tocar a un admin) pide `grupos.nombrar_admin_grupo`. Mover
    un grupo de padre, solo el admin de la organización (`grupos.editar_organizacion`). La ven sus
    miembros (también los de sus subgrupos) y quienes lo administran.
  - Organización: datos, el interruptor de la lista de miembros, grupos principales y admins (los
    nombra o los quita el superadmin). La ven su admin y el superadmin.
- **Quién ve la lista de miembros (2A).** Permiso nuevo `grupos.ver_miembros` (de entrada, el rol
  `usuario`, que lo controla el superadmin) **y** el interruptor de cada organización
  `Organizacion.miembros_ven_miembros` (lo maneja su admin para todos sus grupos). El admin de la
  organización solo puede cerrar: si el superadmin ha quitado el permiso al rol, marcar el interruptor no
  lo devuelve. Los admins la ven siempre. *(Los cometidos del grupo se mostrarán en la ficha cuando haya
  módulos con cometidos y su visibilidad pase por las audiencias.)*
- **«Invitaciones (N)» (3A):** cuenta las pendientes que la persona **puede responder** (las llegadas a
  grupos donde tiene `grupos.responder_invitacion`; el superadmin, todas). Con 0 se escribe «(0)».
  Dentro se ven las recibidas y las hechas por sus grupos; se aceptan, rechazan o retiran. Se crean desde
  lo que se comparte (un proyecto), no desde aquí.
  - **Contador en el menú:** `EntradaDeMenu.contador` es la ruta de una función (usuario → número). El
    resultado se guarda en la caché con versión (`grupos/contadores.py`), que sube al guardar o borrar
    cualquier invitación (señales en `grupos/senales.py`): casi siempre 0 consultas. Como al navegar el
    menú no se vuelve a pintar, `base/zona.html` manda los números aparte con `hx-swap-oob` y htmx los
    pone en su sitio.
- **Relaciones:** solo entre grupos de la misma organización (las organizaciones son independientes). Las
  ve quien ve alguno de los dos grupos; las crea o borra quien puede editar uno de los dos. El grafo
  (isla de Cytoscape) queda para más adelante.
- **Fuera de esta pieza:** mapa (con `lugares`), peticiones de borrado de grupos (con `solicitudes`),
  recuento de talentos y grafo de relaciones.

### 8.2 Lugares

- El superadmin sube listas desde Excel en dos pasos (vista previa → confirmar). Mapa con chinchetas
  agrupadas.
- Cada usuario elige el suyo, o propone uno nuevo con sus datos; el superadmin lo acepta en la lista.
- El superadmin puede avisar a quienes aún no han elegido lugar.
- Un grupo que elige un lugar es una **asamblea de centro**. Pertenecer a ella dice a sus miembros dónde
  trabaja cada persona, así que **al entrar se avisa claramente** de ello. El recuento de miembros solo
  se muestra si son 5 o más.
- Los recuentos por lugar solo se muestran a partir de 5 personas.

### 8.3 Talentos (parte de `usuarios`)

- Son datos personales del usuario: recursos (furgoneta) y habilidades (trabajos verticales). Se eligen
  de un catálogo común con sugerencias y palabras relacionadas. El superadmin fusiona duplicados.
- **El usuario decide con qué grupos y con qué proyectos comparte cada talento.**
- Los demás solo ven **cuántas personas** ofrecen cada talento, nunca quiénes. Una petición de talento
  llega a quienes lo comparten con ese grupo o proyecto; solo quien responde revela su alias.

---

## 9. Tipologías y plantillas

- El superadmin crea un **árbol de tipologías** para proyectos y otro para eventos. Por ejemplo:
  - Proyecto → Comunicación, Tecnología, Preparación de acción, Genérico…
  - Evento → Reunión, Acción, Recaudatorio, Genérico…
- Cada tipología tiene una **plantilla**: campos personalizados (texto, texto largo, número, fecha, sí/no,
  lista), cometidos que se pueden usar (con plazas y si son obligatorios) y, en los proyectos, tareas modelo
  con fecha relativa.
- Al crear algo, la tipología se elige en una lista en árbol. Se ve en todas las listas, junto a las fechas.
- Los valores de los campos personalizados se guardan en JSON dentro del propio objeto.

### 9.1 Tipologías, fase 1 (13 de noviembre de 2026)

- **Dónde se editan:** en una sección nueva del menú, **«Configuración → Tipologías»**, con dos vistas arriba
  («De eventos» y «De proyectos»): el árbol a la izquierda y, a la derecha, el tipo elegido con sus campos.
  La entrada se ve con el permiso `tipologias.gestionar` (admin de la organización) o siendo superadmin.
- **Comunes y de cada organización:** las comunes las crea y cambia solo el superadmin. El admin de cada
  organización puede añadir **subtipos propios** (de un tipo común o de otro suyo), que solo se ven en su
  organización. Una organización nunca ve los tipos de otra, y los nombres solo se comparan con los comunes
  y los suyos (dos organizaciones pueden tener un subtipo con el mismo nombre sin saberlo).
- **Herencia:** un subtipo pide los campos de su tipo y los de más arriba, y después los suyos. Por eso la
  clave de un campo no puede repetirse en la misma rama del árbol.
- **Campos:** texto corto, texto largo, número, fecha, sí o no y lista de opciones; con explicación y si
  es obligatorio. Se **ordenan arrastrándolos** por el asa (SortableJS, MIT, componente `listaOrdenable` de
  `interfaz.js`). `tipologias.servicios.formulario_de()` hace el formulario que usarán proyectos y eventos, y
  `a_json()` deja los valores listos para guardarlos en JSON.
- **Pendiente:** los cometidos y las tareas modelo de la plantilla llegarán con `proyectos` y `eventos`;
  borrar un tipo tendrá que comprobar entonces que nada lo usa.

---

## 10. Eventos y calendario

### 10.1 Datos comunes de un evento

- grupo que convoca y usuario que convoca;
- tipología;
- audiencia (apartado 3.4);
- modalidad (presencial o en línea) y lugar o URL;
- fecha, hora y duración;
- comunicación: cartel y textos para cada red social, con botones de compartir;
- coste: gratis, con donaciones o con entrada.

Todos aparecen en el calendario.

### 10.2 Eventos periódicos

- Una **serie** («todos los lunes a las 18:00») genera **cada vez como un evento propio**, con su propia
  entidad: su asistencia, su ODD y su acta.
- Las veces se crean con antelación, por ejemplo 3 meses vista (configurable), y se van añadiendo solas.
- Cambiar la serie cambia las veces futuras que no se hayan tocado a mano.

### 10.3 Tipologías de evento iniciales

| Tipología | Qué añade |
|---|---|
| **Reunión** | Cometidos de facilitación y toma de acta (hasta 2 personas a la vez). «¿Vas a ir?» (Sí, No, Aún no lo sé). **ODD** y **acta** escritos en el editor (apartado 13). Asistencia («Estoy aquí»). «Convocar la siguiente». Ciclo: borrador → convocada → en curso → celebrada → acta aprobada. **Necesita una solicitud con apoyos.** |
| **Acción** | Qué llevar, riesgos, enlace a documentación para prepararse. Cometidos (Promoción y Comunicación, obligatorios; Logística, Cuidados, «Oveja») con inscripción individual y plazas; mínimo de personas; aviso «lista / qué falta». |
| **Recaudatorio** | Coste de la entrada o cómo se recauda; a quién va el dinero; grupos y usuarios responsables del dinero. |
| **Genérico** | Solo los datos comunes. |

**Preparar una acción:** se crea un **proyecto** de tipología «Preparación de acción», con sus tareas
modelo. Cuando está listo, se crea el **evento** de la acción, copiando lo que haga falta con el botón
«copiar» de cada campo. Se pueden enlazar con un ancla («salida del proyecto»).

### 10.4 Calendario

- Junta todo lo que tiene fecha (cada módulo lo aporta en su contrato), con un color por tipo y filtros.
  Vistas mes, semana, día y lista (en el móvil empieza en lista). Se arrastra lo propio.
- **Recordatorios:** cualquier usuario puede crear en el calendario una anotación libre, sin módulo detrás, y
  elegir si la ve su grupo. El admin del grupo puede hacerla visible a los grupos padre y abuelo.
- Calendario público y suscripción `.ics` con una clave secreta que se puede cambiar.

---

## 11. Debates

- Una **pregunta** con **dos o más opciones**, cada una en una **columna**, todas en paralelo. Puede
  colgar de cualquier cosa (ancla) o ser un debate suelto del grupo. Para abrirlo hace falta una
  **solicitud con apoyos**.
- **Facilitación:** quien abre el debate. El admin puede designar a más personas.
- **Lo que puede hacer cada persona:**
  - En una opción o en un argumento: ⭐ muy importante (con una justificación breve), 👍 apoyo,
    👎 en contra, ⛔ oposición total (con una justificación breve).
  - Solo en argumentos: 🔁 repetitivo y 🚫 no tiene que ver.
  - En el debate entero: 🤝 «todas me valen, no me opongo a ninguna».
  - Escribir un argumento nuevo, a favor o en contra, o responder a otro argumento.
  - **Pedir una opción nueva** o **un debate nuevo a partir de un argumento** (propio o ajeno). Se abre
    cuando lo apoyan N personas (2 por defecto; lo configuran el superadmin y los admin).
  - Si la opción nueva es **de consenso**, se reinicia el número de intervenciones. Quien la pide la
    propone como de consenso, y se confirma sola si recibe apoyos de N personas de opciones distintas.
- **No hay «matiz»**: algo parecido se escribe como argumento.
- **Qué lleva nombre:** los argumentos llevan siempre su alias. Los votos se muestran **solo como
  recuentos**, y las justificaciones de ⭐ y ⛔ aparecen **sin nombre**, para que nadie se sienta
  intimidado.
- **Recuentos sobre cada opción:** argumentos distintos a favor, votos de cada tipo (un voto por persona y
  opción, no por argumento) y argumento más votado.
- **Clasificación de las opciones**, que se muestran juntas:
  - solo votos a favor;
  - votos a favor menos votos en contra.
- **Límites blandos y duros** (palabras por intervención, intervenciones por opción y en total,
  argumentos por opción, opciones nuevas por persona):
  - Al llegar al **límite blando**, se permite una intervención más, **muy marcada visualmente**.
  - Al llegar al **límite duro**, ya no se puede escribir.
  - Los límites van en cascada: superadmin → admin_org → admin_grupo → cada debate. Cada nivel solo
    puede ser más estricto que el anterior. Hay una pantalla de configuración en cada nivel. También se
    configura si la fecha de fin es obligatoria.
- **Etiquetas** en los debates y en los argumentos, con su propio grupo de etiquetas. Forman la **base de
  conocimiento**: argumentos que se pueden buscar por etiqueta o por palabra y reutilizar en otros
  debates.
- **Ampliar** un debate a otros grupos o al público es cambiar su audiencia. El público solo lee y no ve
  alias.
- **Más adelante:** chat (en `comunicaciones`), vista gráfica para la facilitación y resumen automático.

**Tablas:** `Debate`, `Opcion`, `Argumento` (padre opcional), `Voto` (único por persona y elemento),
`LimitesDeDebate` (en cada nivel), y los contadores guardados en la opción.

---

## 12. Consultas

- Quien la crea:
  - **diseña un formulario** (respuesta única, múltiple o abierta, con documentación adjunta);
  - **elige quién vota** (una audiencia);
  - fija **las fechas de apertura y cierre**;
  - decide **cuándo se ven los resultados**: al cerrar (por defecto), en una fecha de publicación
    posterior al cierre o en tiempo real. Si elige tiempo real, se le avisa de que ver cómo va la
    votación influye en quien aún no ha votado;
  - decide **quién ve los resultados**, con los niveles de visibilidad de siempre (apartado 3.4);
  - decide **si se puede cambiar el voto** antes del cierre. Por defecto, no. Si no se puede cambiar,
    se avisa claramente a cada persona antes de votar.
- **Una persona, un voto. Solo uno.** Nadie puede votar dos veces; cambiar el voto (si se permite)
  sustituye el anterior.
- **Voto secreto** (seudónimo con clave aparte): nadie ve desde la plataforma qué ha votado cada persona.
- Resultados en gráficos. El desglose por grupos solo se muestra con 10 votantes o más.
- El resultado se copia como **decisión** al registro.

---

## 13. Documentos: orden del día (ODD) y actas

- **Editor colaborativo:** Markdown escrito a la vez por varias personas en **tiempo real** (Yjs, con un
  pequeño servidor aparte), con **vista previa en HTML al momento**. El PDF se genera con **Typst**
  (Apache-2.0).
- **El ODD se escribe en el mismo editor.** El acta **parte del ODD** y se completa durante la reunión.
- El acta termina siempre con dos apartados fijos: **«Acuerdos alcanzados»** y **«Temas a discutir en la
  próxima reunión»**. Cada acuerdo se marca como bloque de decisión (consenso o votación, con su recuento)
  y se copia solo al registro de decisiones. Cada tema puede convertirse en una solicitud de debate.
- **Plantillas de documentos** que crea el superadmin, según dónde se usen (reuniones, debates,
  proyectos).
- **Escriben** quienes tienen el cometido de toma de acta (hasta dos a la vez). Las demás personas
  asistentes **comentan o proponen cambios** hasta que se aprueba en la reunión siguiente.
- **Autoría que nadie puede borrar**, ni el superadmin:
  - En la primera página, un **registro automático de cambios**: fecha, hora y usuario de cada
    modificación.
  - Detrás de cada párrafo, en color claro y entre paréntesis, **los usuarios que han contribuido a él**.
    El último de la lista es el último que lo ha modificado.
  - No se guardan las versiones anteriores del texto, solo quién ha participado en cada párrafo.
  - Así nadie puede cambiar un acta en silencio por tener más permisos.

---

## 14. Proyectos, tareas y limpieza

### 14.1 Proyecto

- **Descripción:**
  - objetivo general (para qué sirve dentro de una estrategia mayor);
  - objetivos específicos (qué se quiere generar);
  - tipología (apartado 9);
  - alcance (qué entra y qué queda fuera);
  - riesgos y plan de contingencia.
- **Fechas:** inicio y límite de fin.
- **Estados:** sin empezar, empezado, casi acabado, acabado y funcionando (con revisiones periódicas que
  crean tareas), finalizado.
- **Desglose:** proyecto padre, subproyectos (recursivo), tareas, fases y cronograma.
- **Dependencias entre proyectos:** de cuáles depende y a cuáles condiciona, en una vista gráfica.
- **Salidas:** eventos enlazados con anclas.
- **Recursos:**
  - grupo que lo coordina y otros grupos implicados o invitados;
  - cometidos de coordinación, documentación y comunicación;
  - recursos materiales, presupuesto y **necesidades no cubiertas**, cruzadas con los talentos que se
    comparten con el proyecto.

  Los recursos se guardan como **filas genéricas** (tipo de recurso configurable, descripción, cantidad,
  unidad, cubierto o no). Así se pueden añadir tipos nuevos sin cambiar las tablas. Los totales del
  proyecto son la suma de sus tareas y subproyectos, guardada y actualizada por un eventos_sw.
- **Documentación:** cada bloque con su propia visibilidad (apartado 3.4), privada por defecto.
- **Chat** propio (en `comunicaciones`, anclado). **Etiquetas.**
- **Proyecto personal:** con la casilla «privado e individual» solo lo ve quien lo crea y no se publica.
- **Vista:** su lugar en el árbol de proyectos y subproyectos, con sus tareas. Todo se puede pulsar, al
  menos para ver la parte que cada cual tiene permitida.

### 14.2 Tarea

- Atómica: **1 responsable** obligatorio y colaboradores opcionales.
- Puede estar en un **proyecto**, ser una **tarea suelta de un grupo** o una **tarea personal** (solo la ve
  su dueño).
- Descripción, fecha límite y recursos que necesita.
- Estados: pendiente, en curso, bloqueada, hecha (las columnas del kanban). Se bloquea y desbloquea sola
  según sus dependencias; no se permiten dependencias en círculo.

### 14.3 Limpieza (módulo `limpieza`)

- El superadmin configura, **por cada tipo de elemento** (proyecto, tarea, evento, debate, consulta,
  documento, chat…):
  - a los cuántos días de terminar se **archiva** (sale de las listas), avisando al grupo;
  - a los cuántos días después se **borra**, avisando de nuevo al grupo.
- Hay dos configuraciones: una para los elementos **sueltos** y otra para los **asociados a un proyecto**,
  que siguen el plazo del proyecto.
- Antes de borrar, el aviso permite ver los documentos asociados y decidir qué conservar.
- Las **decisiones** se quedan siempre en el registro, con el texto y sin el enlace.
- El superadmin puede además **podar a mano** para liberar espacio.
- **Protección de la memoria colectiva:** las actas aprobadas y las decisiones solo se borran con un
  **aviso previo al grupo** y un **plazo para descargarlas**. Cada borrado queda en un **registro visible**.

---

## 15. Información pública

- Módulo `publico`. **Nada es público por defecto.**
- El superadmin edita la **portada** de la plataforma, y cada organización tiene la suya.
- Debajo, unos menús que se llenan solos con lo que se ha hecho público en proyectos, eventos, debates,
  actas y consultas. Forman un **banco de recursos** producidos por los grupos (carteles, textos,
  documentos, resultados) y ofrecidos al público.
- Nunca se muestran alias.
- El superadmin y todos los admin tienen una **lista de lo publicado** en su ámbito, para ocultarlo
  rápido si hace falta.
- **Repositorio público** (13 de noviembre de 2026, idea de la persona usuaria): la parte pública tendrá
  un menú propio de **repositorio de materiales** (textos, carteles, PDF, fotos…; al principio, seguramente
  solo textos y enlaces a los demás materiales). Se ve como una **lista o tabla filtrable** (por palabras y
  por tipo en cada columna, con la tabla filtrable común), **ordenada de más reciente a más antiguo**.
  *(por diseñar al llegar a `publico`, fase 8)*

---

## 16. Registro de decisiones

- Tabla común con las decisiones de reuniones, debates y consultas. Cada una enlaza a su origen (ancla).
  Se llena sola con eventos_sw.
- Cada persona ve las decisiones de los espacios en los que podía participar.
- Filtros al momento por fecha, origen y grupo. Se cargan como mínimo las 20 últimas.
- Si una decisión se vuelve a tomar, la antigua **se marca como «sustituida por…»**, con un enlace a la
  nueva. **Nunca se borra**: deja de salir en la lista por defecto, pero sigue en su origen.

---

## 17. Comunicaciones

- Menú **«Comunicaciones»** de cada usuario, con bandejas por origen: superadmin, admins, proyectos,
  eventos, debates, solicitudes y sistema.
- **Notificaciones** de los módulos (escuchan eventos_sw) y de otros usuarios. Cada tipo de aviso se activa
  o desactiva y se elige su canal (web, correo y, más adelante, Telegram).
- **Mensajes** del superadmin y de los admin, a una persona o a un conjunto filtrado. El usuario puede
  responder o **iniciar una conversación** con sus admins o con el superadmin.
- **Chat** que se cuelga de un proyecto, un debate, un evento o un grupo. Tiempo real con Channels y Redis.
- **Telegram:** bocetado, para una versión posterior.

---

## 18. Forma de trabajar

- Todo en castellano. Las respuestas empiezan con [A-ID].
- **Método socrático:** antes de cada pantalla o módulo, opciones con pros y contras (una recomendada),
  y se pregunta. No se programa sin acuerdo.
- **Documentación solo en Markdown dentro del repositorio** (`docs/`). Las decisiones van en este
  documento; lo que se explica para aprender, en `docs/tutorial.md`.
- **Normas de código:** comentario antes de cada orden y función, en lenguaje llano y en contexto; cada
  modelo y campo con `verbose_name` y `help_text`; en bash y docker, cada parámetro en su línea, con
  guion y más sangría; claro antes que ingenioso; nada de código GPL.
- **Cada pantalla nueva llega con su prueba de número de consultas** y se mide con datos de ejemplo.
- **Commit al terminar cada pieza acordada**, con el mensaje en castellano.
- Pruebas de pantalla con un navegador sin interfaz (Playwright, Apache-2.0).
  **Instalado el 12 de noviembre de 2026** (`playwright==1.64.1`, con su Chromium), tras un fallo de la
  tabla filtrable que las pruebas sin navegador no podían ver. Las pruebas de pantalla viven en
  `base/tests/test_navegador.py` (`StaticLiveServerTestCase`) y se saltan si no hay Chromium. Cada pieza
  de interfaz con JavaScript propio llega con su prueba en el navegador.

---

## 19. Orden de construcción

| Fase | Contenido |
|---|---|
| 0 | Esqueleto: contenedor, Django y ajustes de rendimiento, `base` (contrato de módulo, plantilla de interfaz con dos menús, tema, ayuda «?», menú que no salta, tabla filtrable, botón copiar), `eventos_sw`, prueba de número de consultas |
| 1 | `usuarios` (sin talentos), `grupos`, `permisos`, `audiencias`, tablas de la `boveda` (alta provisional por el superadmin), `etiquetas`, `tipologias`, pantallas del superadmin de usuarios, organizaciones y tipologías, datos de ejemplo |
| 2 | `comunicaciones` (notificaciones y mensajes), `solicitudes`, `moderacion`, `lugares`, talentos |
| 3 | `eventos` (reunión, acción, series) y `calendario` (con recordatorios) |
| 4 | `proyectos` (con tareas sueltas y personales, recursos y dependencias) y `limpieza` |
| 5 | `documentos` (editor de ODD y actas) y `decisiones` |
| 6 | `debates` |
| 7 | `consultas` |
| 8 | `publico`, chat, Telegram; bóveda real (firma ciega, sobre, métodos de validación, rondas) |

---

## 20. Pendiente de decidir

- Admisión en grupos: cuántos votos hacen falta además del del admin_grupo, quién vota y en qué plazo.
- Proyectos conjuntos entre organizaciones (apartado 8.1): qué audiencia tiene el proyecto, qué ve cada
  organización del otro grupo y cómo se comunican.
- **Búsqueda extensa para los admins** (13 de noviembre de 2026, petición de la persona usuaria): el
  superadmin y el admin de cada organización deben poder buscar en **todo el material generado por sus
  grupos y subgrupos** (proyectos, actas, debates, documentos…), por palabras y etiquetas, para encontrar
  material perdido y retomarlo. Idea: cada módulo declara en su contrato una «fuente de búsqueda» (como las
  fuentes del calendario) y un buscador común las recorre, respetando las audiencias (lo personal no
  entra). *(por diseñar cuando haya módulos con material)*
- Trabajador de colas: Celery o RQ.
- Qué mensajes de Telegram entran a un chat o a un debate.
- Detección de comportamientos sospechosos (señales sin mirar identidades).
