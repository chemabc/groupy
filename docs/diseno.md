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
| Funcional | `mantenimiento` | Sección «Desarrollo y mantenimiento» del superadmin: pruebas (importaciones y datos de ejemplo), entrada a la trastienda y, más adelante, la salud del sistema |
| Funcional | `ayuda` | Sección «Ayuda»: «How to?», documentación de la plataforma y guía de desarrollo (los documentos de `docs/` convertidos en páginas), también en el panel de ayuda de la derecha |

**Regla de dependencias:** Base no depende de nada. Identidad depende de Base. Organización depende de
Base y del modelo de usuario (`get_user_model()`). Funcional depende de Base y Organización, y **nunca de
otro módulo funcional**: se relacionan con anclas y eventos_sw.

**Ejemplo:** una consulta termina. `consultas` emite `consultas.cerrada`. `decisiones` lo escucha y copia
el resultado al registro, y `comunicaciones` avisa a quienes votaron. Ninguno importa al otro.

### 3.3 Contrato de módulo

Cada módulo declara **en una sola clase** (en su `apps.py`) todo lo que aporta: permisos y cometidos,
anclas, huecos en fichas, eventos con fecha para el calendario, eventos_sw que emite y que escucha, grupos
de etiquetas, tipos de elemento que se pueden limpiar, datos de ejemplo, entradas de menú y textos de
ayuda «?». El registro se lee **una vez al arrancar**. Nada de buscar ficheros por su nombre. La única
excepción es **dónde va cada entrada del menú**: lo decide un solo fichero, `config/menu.py` (apartado 4,
«Disposición del menú»).

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
  (`audiencias.configurar`) o el superadmin, en **«Configuración → Visibilidad»** (13 de noviembre de
  2026, opción A de la persona usuaria): una tarjeta por organización con una frase que resume lo que se
  puede elegir («Se puede elegir: privado; su grupo: hasta el grupo padre; grupos concretos. No se
  permite lo público.») y el formulario para cambiarlo. Lo ya publicado no cambia.
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
- **Ayuda «?»** en la cabecera de cada sección. Los textos los declara cada módulo en su contrato. Es una
  **miniayuda en ventana emergente**: qué es la sección, para qué se usa y, si lo trae, un ejemplo
  (`Ayuda.ejemplo`, 14 de noviembre de 2026). No tiene nada que ver con el panel de ayuda del «?» rojo.
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

**Subsecciones de otro módulo (13 de noviembre de 2026; sustituido el 14 de noviembre por la «Disposición
del menú», abajo: ya no existen `dentro_de` ni `orden`).** Una entrada con `dentro_de` se cuelga dentro
de la sección de otro módulo (así `audiencias` y `etiquetas` ponen «Visibilidad» y «Etiquetas» dentro de
«Configuración», que es de `tipologias`), ordenada por `orden`. La sección «Configuración» ya no pide
permiso: una sección se oculta si todas sus subsecciones están ocultas. *(Limitación: el enlace de la
sección lleva a «Tipologías»; quien solo pudiera ver otra subsección recibiría un 403 al pulsarla. Hoy los
tres permisos los tiene el mismo rol, admin de la organización.)*

**Disposición del menú (14 de noviembre de 2026, decisión 2B de la persona usuaria).** El orden de las
entradas del menú y dentro de qué sección va cada una se decide en **un solo fichero**, `config/menu.py`
(`DISPOSICION`), escrito con los códigos de las entradas: `"usuarios.cuenta"` es una entrada sin
subsecciones y `("ayuda.ayuda", ("ayuda.como_se_hace", …))`, una con sus subsecciones, a cualquier
profundidad. Los módulos siguen declarando en su contrato qué entradas aportan (nombre, dirección, icono,
color, permiso, vistas); las subsecciones que declaran solo agrupan su contrato.
- *Motivo:* la persona usuaria quiere cambiar y agrupar el menú a menudo; así es mover una línea y se ve
  todo el menú de un vistazo.
- El registro (`base/registro.py`) rehace el árbol con la disposición al arrancar. Avisa (con
  `manage.py check`) si una entrada declarada no está colocada (y la pone al final para que no
  desaparezca), si se nombra una que nadie declara, si una sale dos veces o si un elemento está mal escrito.
- Quién ve cada entrada sigue en su contrato (`permiso`, `tambien_si`); una sección cuyas subsecciones
  están todas ocultas no se muestra.
- Se quitan `EntradaDeMenu.orden` y `EntradaDeMenu.dentro_de` (había dos formas de decir lo mismo).
- El final del menú es, por este orden: «Ayuda», «Configuración de mi cuenta» (antes «Mi cuenta») y
  «Desarrollo y mantenimiento» (solo el superadmin). Para quien no es superadmin, «Ayuda» es la penúltima
  y «Configuración de mi cuenta», la última: «Ayuda» siempre va antes que la cuenta. *(Desde el mismo día,
  con el menú en tres bloques, «Ayuda» y la cuenta cierran el bloque de lo propio y «Desarrollo y
  mantenimiento», el de «Plataforma».)*
- *Descartado:* seguir con un número `orden` en cada contrato (el orden queda repartido por veinte
  ficheros y hay que buscar números libres).
- *Mejora futura (2C):* editar la disposición desde la interfaz, guardada en la base de datos. Como la
  disposición ya es solo datos (una tupla de códigos), bastaría un modelo que guarde ese mismo árbol y que
  el registro lo use antes que `config/menu.py`, con las mismas comprobaciones; la pantalla sería un árbol
  que se ordena arrastrando (como los campos de las tipologías). Haría falta volver a colocar el menú al
  guardar en todos los procesos (por ejemplo, con una versión en la caché). Ahora no hace falta.

**Sección «Ayuda» y panel de ayuda (14 de noviembre de 2026, a petición de la persona usuaria).**
- **Módulo `ayuda`** (capa funcional), que se queda con los documentos de `docs/` (antes en
  `mantenimiento`). Su sección «Ayuda» tiene tres subsecciones, cada una con sus documentos como pestañas
  arriba:
  - **How to?** (`docs/como-se-hace.md`): guías cortas, paso a paso, para las tareas de cada día. La ve
    todo el mundo. Se escribe a mano y se amplía en cada pieza.
  - **Documentación de la plataforma**: Tutorial, Arquitectura, Arranque y tests, Registro y validación.
  - **Guía de desarrollo**: Comprobaciones pendientes, Diseño y decisiones.
  - Estas dos últimas: en desarrollo, todo el mundo; en producción, quien tiene `ayuda.ver_documentacion`
    (de entrada, solo el superadmin). Lo decide `GUIAS_DE_DESARROLLO_PARA_TODOS`, como antes.
  - Qué documento va en qué subsección es una línea de `ayuda/documentos.py` (`DOCUMENTOS`, con su
    «apartado»). Quién puede ver un documento lo decide su subsección del menú, con la misma regla que la
    muestra u oculta (`puede_ver_entrada`).
  - *Descartado para «How to?»:* juntar solas las ayudas «?» de todas las secciones (no habría que
    mantenerlo, pero explica secciones, no tareas).
- **Botón «?» rojo** arriba a la derecha, junto al del tema. Despliega las subsecciones de la ayuda (y las
  pestañas de las que tienen varias). Sale de la entrada del menú que lleva `panel_de_ayuda=True` (solo
  puede haber una), así que si se cambia la ayuda en `config/menu.py`, el botón la sigue.
- **Panel de ayuda a la derecha.** Al elegir algo, se abre en un panel que estrecha la zona principal.
  - **No se vuelve a pintar al navegar:** está fuera de `#zona`, igual que el menú izquierdo, y la
    navegación con htmx solo cambia `#zona`.
  - Lo que se abre en él se pide con htmx al propio panel (`HX-Target: panel-de-ayuda-contenido`) y
    `base/contexto.py` elige entonces la plantilla `base/panel.html` (título, pestañas, «Abrir en grande» y
    el contenido, sin cabecera de sección ni menús). Las páginas no tienen que hacer nada. Cuesta lo mismo
    que la página en la zona principal.
  - Dentro del panel, las anclas del índice bajan dentro del panel; las páginas de la ayuda se abren en
    el panel; las demás, y «Abrir en grande», van a la zona principal.
  - **Línea de separación arrastrable** (con el ratón, con las flechas del teclado; doble clic, ancho de
    partida: un tercio largo de la pantalla, entre 320 y 720 píxeles). La zona principal no baja de 32rem
    (512 px) con el panel abierto: si no cabe, sale una barra de desplazamiento abajo. En el móvil, el
    panel ocupa toda la pantalla.
  - Se recuerda en el navegador si está abierto, qué página tenía y su ancho. El script de la cabecera lo
    aplica antes de pintar (`data-panel-de-ayuda` en `<html>`, variante `panel-abierto:` de Tailwind, y la
    variable `--ancho-del-panel`), así que no salta al recargar.
  - **Botones − y +** en la cabecera del panel: cambian el tamaño de la letra **solo del panel** (del 70 %
    al 160 %, por pasos), y se recuerda en el navegador. Se aplica con `zoom` de CSS a la página del
    panel, que agranda todo a la vez (también tablas y diagramas) y reparte las líneas en el ancho que
    hay. *Descartado:* cambiar el tamaño de la letra base (las clases de Tailwind van en `rem`, que mira
    la letra de `<html>`, y cambiaría toda la pantalla). Para que nada se salga de lado, la columna del
    documento no puede crecer (`grid-cols-[minmax(0,1fr)]`) y el código dentro del texto se parte
    (`overflow-wrap: anywhere`).
  - El **«?» gris de cada sección no va al panel**: sigue siendo su ventana emergente (corrección de la
    persona usuaria, 14 de noviembre de 2026; durante un rato se abrió en el panel y no era lo querido).
  - *Descartado:* un panel de ancho fijo (la persona usuaria prefería poder arrastrarlo, y no era
    complejo) y un `<iframe>` (cargaría otra vez toda la página, con sus menús).
- **Índice plegable** en los documentos: un botón «Índice» lo pliega y lo despliega, y se recuerda en el
  navegador (aparte en el panel, donde sale plegado de entrada). Se coloca a la izquierda o encima según
  el **ancho de su caja** y no el de la pantalla (consultas de contenedor de Tailwind, `@container`), así
  que en el panel estrecho va encima.
- **Sin HTML escrito a mano en los documentos:** la conversión de Markdown escapa cualquier etiqueta que
  no esté en un bloque de código. *Motivo:* el tutorial mencionaba «`<script>`» sin comillas de código y se colaba en la página
  como etiqueta de verdad (salió en las pruebas del panel). Ningún documento usaba HTML a propósito.

**Menú en tres bloques (14 de noviembre de 2026, decisiones 1A, 2a, 3A y 4A de la persona usuaria).** Lo
propio va separado de lo que se hace por otras personas.
- *Motivo:* antes se mezclaban; por ejemplo, en «Comunicaciones» convivían tus notificaciones con el buzón
  que atiendes como admin, y en «Solicitudes», las que apoyas con las que esperan tu sí.
- **Tres bloques** (`base/disposicion.py`, `Bloque`), siempre visibles y en este orden:
  - **Lo propio**, sin título: Inicio (Panel · Mis datos), Calendario y eventos, Comunicaciones
    (Notificaciones, Conversaciones, Solicitudes), Tareas y proyectos, Participación, Organizaciones y
    grupos (Mis grupos, Mapa de lugares), Ayuda y Configuración de mi cuenta (Usabilidad, Mis datos, Avisos
    que recibo, Contraseña, Archivo).
  - **Administrar** (admin de grupo y de organización; franja ámbar): Grupos que administro, Buzón de la
    administración, Por aprobar, Eventos y talentos, Moderación y Mi organización. Cada pantalla enseña
    solo lo que administra quien mira (2a: una sola sección para los dos tipos de admin, no una por rol).
  - **Plataforma** (solo superadmin; franja roja): Usuarios, Catálogos comunes, Limpieza y Desarrollo y
    mantenimiento (con «Componentes», la demostración de la plantilla que antes era «Inicio»).
  - Las pantallas de «Administrar» y «Plataforma» llevan arriba una **banda** de su color que lo recuerda.
  - Un bloque sin nada que ver no sale. Un superadmin que además está en grupos ve los tres.
  - *Descartado (1B):* un interruptor «Personal / Administración» que cambie el menú entero (esconde
    cosas y hay que recordar en qué modo se está).
- **Secciones con pestañas** (`Pestanas` en `config/menu.py`): las subsecciones de una entrada salen
  arriba como pestañas, no en el menú de la izquierda. Así una sección junta pantallas de módulos distintos
  (por ejemplo, «Mis grupos»: Árboles · Grafo · Relaciones · Talentos de mis grupos). Si la pestaña elegida
  tiene varias vistas, salen en una segunda fila, más pequeña. El menú de la izquierda marca la sección;
  el título es el suyo; su número es la suma de los de sus pestañas.
- **«Configuración de mi cuenta» con submenús a la izquierda** (no pestañas), para poder añadir más.
- **Herramientas que aún no existen** (módulo `proximamente`): cada una tiene su entrada, con su sitio en
  el menú, y al pulsarla dice que está vacía y qué hará. Son: conversaciones con grupos y con personas,
  grafo de grupos, datos de la cuenta, debates, consultas, órdenes del día y actas, decisiones, miembros,
  eventos de los grupos que administro, moderación y web pública. Cuando se construye una, se cambia su
  código en `config/menu.py`. (Ya hechas: «Inicio → Panel» y «Mis datos», y los datos de la cuenta; ver
  «Inicio» más abajo.)
- **Separaciones que han hecho falta:**
  - Las conversaciones: las propias, en «Comunicaciones»; las que se atienden, en «Administrar → Buzón de
    la administración» (con su número aparte).
  - Las solicitudes: «Para apoyar» (como miembro), en lo propio; «Por aprobar» (el sí de la
    administración), en «Administrar», cada una con su número.
  - «Pedir talentos» sale de la pantalla de peticiones y va a «Administrar».
  - «Mi organización → Datos»: pantalla nueva con las organizaciones que se administran y el enlace a su
    ficha.
- **Las invitaciones no son solicitudes:** son de un grupo a un grupo de otra organización, para algo
  concreto, y las responde su administración. Van en «Administrar». Entrar en un grupo sí es una solicitud.
- **Corregido de paso:** al entrar en una tarea, el menú marcaba la sección y no «Tareas»; ahora la ficha
  de la tarea pertenece a «Tareas» y la del proyecto a «Proyectos».
- *Pendiente:* las tipologías y las etiquetas comunes las cambia el superadmin desde «Administrar → Mi
  organización» (es la misma pantalla que la de cada organización); si se quiere, se puede separar en
  «Plataforma → Catálogos comunes».

**Inicio: Panel y Mis datos (14 de noviembre de 2026, [A-40], decisiones 1 y 2 de la persona usuaria;
lo pedido en docs/todo.md, «Reorganización de menús», 1).** La portada de cada cuenta.
- **«Panel» es un dashboard:** resume lo que ya está en otras secciones, sin datos nuevos, y todo lleva a
  su sitio.
  - Fila 1: «Comunicaciones» (recibidas: notificaciones sin ver y respuestas de la administración sin
    leer; enviadas: las conversaciones que empezaste y siguen sin resolver) y «Solicitudes» (recibidas:
    las que puedes apoyar y aún no has respondido; enviadas: las tuyas pendientes).
  - Fila 2: «Mis proyectos abiertos»: los que no están terminados ni archivados y en los que participas
    (los creaste, tienes un cometido o eres responsable o colaboras en una de sus tareas), primero los que
    tienen fecha límite.
  - Cada apartado enseña lo más reciente (5; 8 proyectos) y «Ver todas (N)» si hay más.
  - Lo que se hace como admin (buzón, «Por aprobar») no sale: está en «Administrar».
  - «Enviadas» de comunicaciones son las **sin resolver** y no «las que esperan respuesta»: no se guarda
    quién escribió el último mensaje, solo si cada parte tiene algo sin leer.
- **«Mis datos»: Inicio enseña y «Configuración de mi cuenta → Mis datos» edita** (decisión 1). Filas:
  datos públicos (alias, desde cuándo); talentos; datos privados (correo alternativo, cómo se creó la
  cuenta, preferencias) y mi lugar; y el **árbol de mis grupos** con el rol en cada uno (decisión 2: el
  mismo componente de «Árboles de grupos», apartado 8.1). Cada recuadro con su botón «Editar»; el de los
  grupos, «Pedir entrar en un grupo».
  - *Descartado (1B):* una sola pantalla editable en Inicio (habría dos sitios para lo mismo).
- **«Configuración de mi cuenta → Mis datos → Datos»** (antes vacía): cada dato con quién lo ve y cómo se
  cambia; aquí se cambia el correo alternativo. El alias lo cambia la administración.
- **Cómo está hecho:** pieza nueva del contrato, `TarjetaDeInicio` (título, icono, color y la función que
  hace el resumen: devuelve un `ResumenDeTarjeta` con `ApartadoDeTarjeta` y `FilaDeResumen`, o una
  plantilla propia, o None si no toca). Cada módulo pone su función en su `inicio.py`. **Dónde va cada
  tarjeta lo decide `config/inicio.py`**, como el menú en `config/menu.py`; `manage.py check` avisa si
  sobra, falta o se repite una (`base.E007`). `base/inicio.py` las junta sin importar los módulos.
  - *Motivo:* `base` es la capa de abajo y no puede importar `comunicaciones`, `solicitudes` ni
    `proyectos`; así, cuando existan debates o consultas, añaden su tarjeta sin tocar `base`.
  - Los totales de lo recibido son los mismos números del menú (ya en la caché), así que no cuestan
    consultas. El panel cuesta 10 consultas y «Mis datos», 6, haya lo que haya.
  - *Descartado:* tarjetas que solo enseñen los números del menú (no dicen qué hay pendiente ni separan
    lo enviado de lo recibido).

**Lo que cuelga de otra cosa (15 de noviembre de 2026, para documentos, debates y consultas).**
- **`Colgante`**, pieza nueva del contrato: un módulo dice qué suyo puede colgar de qué anclas
  («eventos.evento», «proyectos.proyecto»…) y la función que lo lista. La etiqueta `{% colgantes %}` de
  `base` pinta en la ficha de ese elemento el recuadro **«Cuelga de aquí»**, con lo que ya cuelga y el
  enlace para crear uno nuevo (`?ancla=tipo:número`). Así la ficha de una reunión enseña sus órdenes del
  día, actas, debates y consultas sin importar esos módulos. Hoy está en las fichas de eventos y proyectos.
  - Es lo que el contrato llamaba «huecos» (declarados pero sin usar): se deja `Hueco` para cuando una
    ficha necesite varios sitios distintos.
- **`base/anclas.py`:** pasa «tipo:número» a (tipo, número) y encuentra el elemento por el modelo que
  declara su módulo; lo que cuelga toma de ahí su grupo y su audiencia.
- **`base/markdown.py`:** Markdown seguro para lo que escriben las personas (sin HTML y sin enlaces
  `javascript:`, `data:` ni `vbscript:`, tampoco disimulados con entidades).
- **`grupos.acceso.grupos_donde_puede`:** los grupos donde alguien tiene un permiso, para los desplegables
  «Grupo» al crear (estaba repetida en cuatro vistas; las viejas se pasarán a ella cuando se toquen).

**Selector de personas (14 de noviembre de 2026, decisiones 1A, 2, 3A, 4A con buscador y 5 de la persona
usuaria).** Para elegir personas (de entrada, la responsable y quienes colaboran en una tarea) ya no se
escribe el alias a ciegas: un componente común abre una ventana con quienes ven aquello, de lo más cercano
a lo más lejano.
- *Motivo:* antes había que saberse el alias, y el campo aceptaba **cualquier alias de la plataforma**, también de
  otra organización (rompía la regla dura entre organizaciones y dejaba averiguar si un alias existía).
- **Cercanía respecto al grupo de referencia** (1A): el que coordina el proyecto, o el de la tarea suelta.
  Bloques: «Aquí» (el propio grupo), «En sus subgrupos», «Un nivel por encima: GRU Jarama» (el resto del
  padre y sus subgrupos), «Dos niveles por encima…», «Más lejos» y «Otras personas que lo ven». Son los
  mismos niveles que la visibilidad («grupo:0», «grupo:1»…). Cada persona sale una vez, en su bloque más
  cercano, bajo su grupo. Lo cercano sale desplegado y con más color; lo lejano, plegado y más suave. Junto
  al alias, «admin» y «tú».
  - *Descartado (1B):* medir desde los grupos de quien elige (ambiguo con varios grupos y podía enseñar a
    quien no ve el proyecto).
- **Solo salen las personas que lo ven** (2), y solo se aceptan esas al guardar. En un proyecto privado,
  solo quienes ya lo ven. En una tarea suelta aún «privada», las del propio grupo y sus subgrupos (todavía no
  tiene personas). Las cuentas desactivadas no salen. El error al guardar es el mismo exista o no el alias
  («No está entre quienes ven esto: X»), para no dar pistas de quién hay fuera.
- **Respeta la lista de miembros cerrada** (3A): la lista solo la ve quien puede ver los miembros del grupo
  de referencia (quien lo administra y, si la organización no la ha cerrado, sus miembros: la regla de
  `grupos/acceso.py`). Si no, la ventana solo deja escribir el alias exacto, que se comprueba igual.
  - *Descartado (3B):* enseñar siempre la lista (se saltaba la decisión de la organización).
- **Ventana con buscador** (4A): el buscador filtra mientras se escribe, sin peticiones, por palabras del
  alias, del grupo o de la marca, sin tildes ni mayúsculas, y despliega los bloques donde hay coincidencias.
  Responsable: una persona (al elegirla se cierra); colaboran: varias (casillas y «Listo»). Las elegidas
  quedan como pastillas con ×.
  - *Descartado (4B):* solo un buscador con sugerencias (no da la vista de quién está cerca y quién lejos).
- **Componente común** (5): `SelectorDePersonas` y `CampoDePersonas` en `base/formularios.py`, la isla
  `selectorDePersonas` en `interfaz.js` y el cálculo en `audiencias/cercania.py` (`cercania`,
  `ids_que_ven`, `ve_la_lista`). El módulo que lo usa da la dirección de la lista (JSON) y la función con
  los ids que se pueden elegir. La lista se pide al abrir la ventana (no cuesta nada si no se abre) y otra
  vez si cambia un campo del que depende (la visibilidad de una tarea suelta nueva). Cuesta 5 consultas en
  `audiencias` y 6 la dirección de `proyectos`, haya las personas que haya. Servirá también para los
  cometidos de los eventos, los avisos a personas, etc.

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

**Cómo está hecho `solicitudes` (13 de noviembre de 2026, decisiones 1A, 2A y 3A de la persona
usuaria).**
- **Cada módulo declara sus tipos (1A)** en su contrato: `TipoDeSolicitud(código, nombre, resolver,
  apoyos, días, aprobacion, basta_el_superadmin, solo_miembros, comprobar, generica)`. `solicitudes` lleva
  apoyos, plazo y estado; al aceptarse llama a `resolver(solicitud)` del módulo, que crea lo pedido. Los
  debates y las reuniones declararán los suyos.
- **Primer tipo: «Entrar en un grupo» (2A, de `grupos`).** Resuelve la admisión que estaba pendiente:
  hace falta el sí de la administración del grupo (permiso `grupos.admitir`: su admin o el de la
  organización) **y** 2 apoyos de sus miembros, en 15 días. Además, **el sí del superadmin basta** por sí
  solo, para los primeros usuarios (a petición de la persona usuaria). Si quien entra no tiene asamblea
  base, ese grupo pasa a serlo. Se pide desde «Solicitudes → Mis solicitudes → Pedir algo», con los grupos
  de sus organizaciones (o de todas, si aún no está en ninguno).
- **Apoyos y plazos ajustables:** `AjusteDeSolicitud`, en «Configuración → Solicitudes»: el superadmin los
  de toda la plataforma y el admin de cada organización (`solicitudes.ajustar`) los de la suya. Vale el de
  la organización, si no el de la plataforma, si no el del contrato. Solo cambia las solicitudes nuevas.
- **Sección «Solicitudes» (3A):** «Pendientes (N)», «Pasadas» y «Mis solicitudes». N cuenta las que
  esperan algo de esa persona (responder, o dar el sí de la administración). El superadmin ve todas, con
  su estado, sus apoyos («2 de 2», con los alias) y si tienen el sí de la administración.
- **Caducar:** las pantallas caducan las vencidas al abrirse, y la orden `caducar_solicitudes` lo hace
  para ejecutarla una vez al día.
- **Avisos:** «necesita el sí de tu administración» (a los admins del grupo y de la organización),
  «se ha aceptado tu solicitud» y «ha caducado tu solicitud».

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
  de la que se queda), renombrar y poner relacionadas, en **«Configuración → Etiquetas»** (13 de
  noviembre de 2026, opción A de la persona usuaria): arriba se elige de quién (una organización o, el
  superadmin, las comunes) y se busca (también en las relacionadas); la tabla dice cuántas cosas lleva
  cada etiqueta; se crean, se cambian, se borran y se fusionan marcando varias y eligiendo cuál se queda.
  Las casillas de la tabla pertenecen al formulario de fusionar por su atributo `form`, para que cada
  fila pueda tener también sus propios formularios (los formularios no se pueden meter unos en otros).
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
  - **Borrar quita también lo creado al probar** (14 de noviembre de 2026). Antes, cada módulo borraba solo
    lo que había creado él; lo que se hacía siguiendo las comprobaciones (una petición de talentos, un
    evento, un proyecto, un recordatorio, un subtipo propio…) protegía a lo de los módulos de abajo y
    `ejemplos borrar` fallaba (`ProtectedError`). Ahora el borrado de cada módulo quita además lo suyo
    que esté en las **organizaciones de ejemplo** (`grupos.ejemplos.organizaciones_de_ejemplo`) o sea de
    las **personas de ejemplo** (`usuarios.ejemplos.usuarios_de_ejemplo`). `eventos` y `calendario`, que no
    crean ejemplos, declaran solo el borrado (`DatosDeEjemplo(crear="", borrar=…)`). Lo de otras
    organizaciones no se toca. Lo vigila `ejemplos/tests/test_ejemplos.py`, que simula lo que se hace al
    probar y comprueba que se borra y se vuelve a crear.
  - *Descartado:* borrar las protecciones (`PROTECT` → `CASCADE`): protegen datos reales en producción.

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

**Sección «Desarrollo y mantenimiento» (13 de noviembre de 2026, a petición de la persona usuaria; el 14
de noviembre la documentación y las guías pasaron a la sección «Ayuda», módulo `ayuda`, ver apartado 4, y
aquí quedan «Pruebas» y «Trastienda», solo para el superadmin).** Es la
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
- **Guías de desarrollo** (13 de noviembre de 2026, a petición de la persona usuaria): una cuarta
  subsección, la primera, con dos pestañas, ambas en Markdown dentro de `docs/`:
  - «Comprobaciones pendientes» (`docs/comprobaciones.md`): lo construido, pieza a pieza, con qué mirar
    en cada pantalla, y antes un apartado «Antes de empezar» en el que cada paso dice primero cómo saber
    si ya está hecho y, si no, qué ejecutar. Las listas `- [ ]` se pintan con casillas que se pueden
    marcar y que recuerda cada navegador (localStorage), con un recuento arriba.
  - «Arquitectura» (`docs/arquitectura.md`): diagramas de todo el programa (Django, librerías, servicios,
    capas y módulos, cada caja con su etiqueta: núcleo, contrib, librería, servicio, módulo, componente,
    isla…) y después uno por módulo y por componente con sus relaciones (importa, contrato, eventos_sw).
  - **Diagramas:** bloques `mermaid` del Markdown que dibuja la isla «documento» con Mermaid 11.17.2 (MIT)
    y svg-pan-zoom 3.6.2 (BSD-2-Clause), servidos por nosotros y cargados solo si hay diagramas; cada diagrama se dibuja al acercarse a la vista
    (dibujar los 30 y pico de golpe tardaba decenas de segundos). Botones
    para acercar, alejar, ajustar y pantalla completa, arrastrar y doble clic. *Descartado:* Mermaid 12 (la
    versión mayor más reciente) y dibujar los diagramas a mano en SVG (no se mantendrían al día).
  - **Quién las ve:** en desarrollo, cualquier persona con sesión; en producción, solo quien tiene
    `mantenimiento.ver` (el superadmin). Lo decide `GUIAS_DE_DESARROLLO_PARA_TODOS` (de entrada, igual que
    `DEBUG`; variable de entorno `DJANGO_GUIAS_PARA_TODOS`). Para ello `EntradaDeMenu` tiene un campo nuevo,
    `tambien_si`: una función que deja ver la entrada aunque falte el permiso. Las demás subsecciones de
    «Desarrollo y mantenimiento» siguen pidiendo `mantenimiento.ver`.
  - Se mantienen al día con cada pieza (ver CLAUDE.md, «Guías de desarrollo»).

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

**Árboles de grupos (14 de noviembre de 2026, [A-40]; lo pedido en docs/todo.md, «Grupos y proyectos»).**
Un solo componente dibuja los grupos en árbol en todas las pantallas, para que se lean siempre igual.
- *Motivo:* la persona usuaria quiere saber de un vistazo dónde está, con los mismos colores en todas
  partes; y el mismo árbol servirá para «Inicio → Mis datos» (decidido en [A-40]: primero el árbol y después
  Inicio, para no hacerlo dos veces).
- **Qué sale:** los grupos en los que está la persona, los que los contienen (miembro por herencia, en
  gris) y los que administra, con sus subgrupos. Nada más: ni los grupos hermanos ni los de otras ramas,
  que no ve. El superadmin ve solo los suyos (todos los grupos están en «Administrar → Árbol»).
- **Colores:** la organización en una etiqueta violeta; la asamblea base con fondo amarillo (y la etiqueta
  «asamblea base»); el grupo cuya ficha se mira, con un recuadro rojo. Junto a cada grupo, el rol si no es
  el normal, y «administras (y lo de debajo)» solo en el grupo más alto de lo que se administra (ponerlo
  en todos lo llenaba de etiquetas). Cada nombre lleva a la ficha del grupo; el de la organización, a la
  suya, si se administra.
- **Un árbol por organización**, en una rejilla de hasta 3 columnas (2 en pantallas medianas, 1 en el
  móvil). Debajo, la leyenda de los colores.
- **Dónde está:** «Organizaciones y grupos → Mis grupos → Árboles» (sustituye a la lista con sangría, con lo
  mismo que enseñaba) y arriba de la ficha de cada grupo (solo el árbol de su organización, con el
  recuadro rojo). El camino de la ficha («ORG Tajo › GRU Tajo › …») se mantiene.
- **Cómo está hecho:** `grupos/arboles.py` (`arboles_de`, que cuesta de 2 a 5 consultas sean cuantos
  sean los grupos) y las plantillas `grupos/arboles.html` y `grupos/nodo_de_arbol.html` (se incluye a sí
  misma para cada subgrupo). Los colores son clases propias en `base/estilos/entrada.css` (`arbol`,
  `arbol-organizacion`, `arbol-base`, `arbol-actual`). La ficha de grupo pasa de 10 a 13 consultas.
  - *Descartado:* una isla de JavaScript (un árbol que se pliega no hace falta con pocos grupos, y sin
    JavaScript sale ya pintado) y el grafo, que es otra pestaña («Mis grupos → Grafo», aún por hacer).

**Grafo de grupos (14 de noviembre de 2026, versión sencilla pedida por la persona usuaria tras [A-47]).**
«Organizaciones y grupos → Mis grupos → Grafo».
- **Qué sale:** los mismos grupos que los árboles (los tuyos, los que los contienen y los que
  administras), cada organización en su caja violeta; flechas llenas de cada grupo a sus subgrupos y de
  puntos para las relaciones libres («colabora», «apoya»…). Si una relación llega a un grupo que no sale en
  tu árbol, ese grupo sale punteado (es lo mismo que enseña «Relaciones»). Mismos colores que los árboles:
  asamblea base amarilla, heredados en gris, lo que administras con borde ámbar.
- **Cada grupo se pulsa** y lleva a su ficha. Se acerca, se aleja, se arrastra y se ve a pantalla completa.
- **Cómo está hecho:** sin librerías nuevas. `grupos/grafo.py` escribe el grafo en texto de Mermaid (la
  librería de los diagramas de la ayuda) y lo dibuja la misma isla, «documento», a la que se le ha
  añadido `data-enlaces` para que los nodos se puedan pulsar. Cuesta 5 consultas.
  - *Descartado:* una librería de grafos interactivos (Cytoscape, vis-network…): más peso para lo mismo.
    Si hace falta mover nodos a mano o filtrar, se reconsidera.

### 8.2 Lugares

- El superadmin sube listas desde Excel en dos pasos (vista previa → confirmar). Mapa con chinchetas
  agrupadas.
- Cada usuario elige el suyo, o propone uno nuevo con sus datos; el superadmin lo acepta en la lista.
- El superadmin puede avisar a quienes aún no han elegido lugar.
- Un grupo que elige un lugar es una **asamblea de centro**. Pertenecer a ella dice a sus miembros dónde
  trabaja cada persona, así que **al entrar se avisa claramente** de ello. El recuento de miembros solo
  se muestra si son 5 o más.
- Los recuentos por lugar solo se muestran a partir de 5 personas.

**Cómo está hecho `lugares` (13 de noviembre de 2026, decisiones 1A y 2A de la persona usuaria).**
- **Lista común a toda la plataforma (1A).** Cada lugar tiene datos obligatorios (nombre, dirección y
  URL de localización, de la que salen solas las coordenadas si es de OpenStreetMap o Google Maps) y
  opcionales (latitud y longitud a mano, teléfonos, correos y notas, un texto amplio), los mismos en todos
  los lugares. Se puede retirar uno de la lista sin quitárselo a quien ya lo tenía.
- **Altas:** el superadmin los crea a mano o los importa desde una hoja (.ods o .csv, con plantilla), en
  dos pasos (vista previa → confirmar; uno con el mismo nombre y dirección no se toca). Cualquier persona
  **propone un lugar nuevo**; si el superadmin lo acepta, entra en la lista y, si aún no tenía lugar,
  pasa a ser el suyo.
- **Cambios:** desde «Mi lugar», un botón para **proponer un cambio** en los datos de su lugar. El
  superadmin ve qué cambia (antes y después), lo acepta (se actualiza para todos) o lo rechaza con una
  explicación. Se avisa a quien lo propuso.
- **Privacidad:** el lugar de cada persona solo lo ven ella y el superadmin. Los demás ven cuántas personas
  **de sus organizaciones** hay en cada lugar, solo a partir de 5, nunca quiénes.
- **Configurable por organización (2A):** «Configuración → Lugares» (superadmin y admin de la
  organización): si sus miembros ven el mapa y la lista, si ven los recuentos y si el mapa se publica en
  su web pública (se guarda ya; se usará con el módulo `publico`).
- **Mapa:** isla «mapa» de `base/static/base/interfaz.js` con Leaflet 1.9.4 (BSD-2) y
  Leaflet.markercluster 1.5.3 (MIT), servidos por el propio servidor y cargados solo en la página que los
  usa. Teselas de OpenStreetMap con `referrerPolicy`. Chinchetas agrupadas; al pulsar, nombre (enlace a la
  ficha), dirección y número de personas.
- **Recordatorio:** el superadmin avisa con un botón a quienes aún no han elegido lugar.
- *(Pendiente: la «asamblea de centro», un grupo con lugar, con el aviso claro al entrar; y los avales del
  lugar, con la bóveda real.)*

### 8.3 Talentos (parte de `usuarios`)

- Son datos personales del usuario: recursos (furgoneta) y habilidades (trabajos verticales). Se eligen
  de un catálogo común con sugerencias y palabras relacionadas. El superadmin fusiona duplicados.
- **El usuario decide con qué grupos y con qué proyectos comparte cada talento.**
- Los demás solo ven **cuántas personas** ofrecen cada talento, nunca quiénes. Una petición de talento
  llega a quienes lo comparten con ese grupo o proyecto; solo quien responde revela su alias.

**Cómo está hecho `talentos` (13 de noviembre de 2026, decisión 3B de la persona usuaria).**
- **Módulo propio en la capa de organización**, no dentro de `usuarios`: necesita los grupos, y `usuarios`
  está en la capa de identidad.
- **Catálogo común** (`Talento`: nombre, tipo —recurso o habilidad— y palabras relacionadas), con la misma
  forma fija que las etiquetas. Al escribir uno se proponen los del catálogo (lista de sugerencias del
  navegador) y, si se escribe uno igual o una relacionada, se usa el que ya existe. El superadmin
  renombra, cambia el tipo y las relacionadas y fusiona repetidos en «Talentos → Catálogo».
- **Mis talentos:** cada persona añade los suyos (con un detalle opcional) y marca con qué grupos (de los
  suyos) comparte cada uno. Sin compartirlo, nadie sabe que lo tiene.
- **Recuentos:** «Talentos de mis grupos» dice cuántas personas comparten cada talento con un grupo o con
  sus subgrupos; nunca quiénes.
- **Peticiones (3B):** una administración (permiso `talentos.pedir`: admin del grupo y de la
  organización) pide a un grupo qué talentos hacen falta y cuántos de cada uno. Llega como aviso a quienes
  los comparten con ese grupo o sus subgrupos, y la ven todos los miembros del grupo con «x de y»
  ofrecidos. Cada persona decide: **«Lo ofrezco»** (con un mensaje opcional; su alias solo lo ven quien
  pidió y la administración, y se le avisa) o **«Tengo dudas»**, que abre una conversación con la
  administración del grupo (pantalla de `comunicaciones`, con el asunto puesto). Quien pidió la cierra o la
  vuelve a abrir. Número en el menú: «Peticiones (N)», las que piden algo que compartes y no has respondido.
- *(Más adelante: pedir talentos desde un proyecto, con su ancla, cuando exista `proyectos`; y el chat.)*

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
- **Pendiente:** los cometidos de la plantilla llegarán con `eventos` (plazas y obligatorios); borrar un
  tipo tendrá que comprobar entonces que nada lo usa. Las tareas modelo ya están (apartado 14.1.3).

---


**Árbol de tipologías con el aspecto de los demás árboles (14 de noviembre de 2026, [A-44]).** La persona
usuaria pidió el mismo protocolo visual para todas las jerarquías. En «Tipologías», el árbol de la
izquierda cuelga cada tipo de su padre con rayas (clase `arbol`); arriba, la familia («Tipos de
proyectos») en la etiqueta violeta; en amarillo, los tipos que quien mira puede cambiar (los de su
organización; el superadmin, todos), y en rojo el elegido. El resto de la pantalla no cambia. Lo pinta
`tipologias/nodo_de_tipologia.html` (se incluye a sí misma); la vista cuelga las ramas sin consultas
(`_en_nodos`).

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
- **Cómo está hecho (13 de noviembre de 2026):**
  - `Serie` comparte con `Evento` los datos comunes (una tabla abstracta, `DatosDeEvento`); su `inicio`
    es el de la primera vez. Frecuencias: cada semana, cada dos semanas, cada mes el mismo día (los meses
    sin ese día se saltan) y cada mes el mismo día de la semana («el segundo martes», «el último
    viernes»). Opcionalmente, hasta un día. La hora es la de aquí (no cambia con el horario de verano).
  - Se crea al convocar, eligiendo «¿Se repite?». Cada vez es un `Evento` con `serie`, `en_la_serie` (la
    fecha que le tocaba) y `tocado`. Al crearla se avisa solo de la primera vez (no de cada una).
  - Antelación 90 días (campo `antelacion`). La **tarea diaria** `eventos.generar_series` añade las
    siguientes y termina las que llegan a su último día.
  - Editar o cancelar una vez la marca como «cambiada a mano». Cambiar la serie copia los datos en las
    próximas no tocadas; si cambia cuándo se repite, las que ya no encajan se borran (o se cancelan, con
    aviso, si alguien había respondido) y se crean las nuevas. «Terminar la serie» cancela las próximas
    no tocadas.
  - Una **serie de reuniones** pide una sola solicitud con apoyos (tipo `eventos.serie_de_reuniones`,
    2/5/10 como una reunión suelta); hasta tenerla no crea veces.
  - Pantallas: «Eventos → Mis eventos → Series» (las que convoqué y las de los grupos que administro) y
    la ficha de cada serie (regla, próximas veces, cambiar, terminar). Cada vez enlaza a su serie.
  - **Tareas diarias** (nuevo apartado del contrato, `TareaDiaria`): las ejecuta el trabajador la primera
    vuelta de cada día (marca en Redis con `cache.add`, para que no se ejecuten dos veces aunque haya dos
    trabajadores); también `python manage.py tareas_diarias`. La primera de otro módulo:
    `solicitudes.caducar`. Descartado por ahora cron o Celery beat (diseño, apartado 20).

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

### 10.5 Cómo está hecho `eventos` (13 de noviembre de 2026, decisiones 1A, 2A y 3A de la persona usuaria)

- **Orden de la fase 3 (1A):** eventos → calendario → series periódicas.
- **Convocar:** se elige el grupo (donde se tenga `eventos.convocar`, de entrada cualquier miembro) y el
  tipo (las tipologías de evento comunes y de su organización); después, los datos comunes, **quién lo
  ve** (el selector de visibilidad de `audiencias/selector.py`, estrenado aquí, con las opciones que
  permite la organización: privado, mi grupo, hasta el padre…, toda la organización, público) y los campos
  propios de su tipología. Presencial pide lugar de la lista o dirección; en línea, el enlace.
- **Reuniones con apoyos:** una tipología de la rama «Reunión» común es una reunión. Al convocarla queda
  **pendiente** (solo la ve quien la convoca) y se pide una solicitud «Convocar una reunión» al grupo al que
  llegará: 2 apoyos en el propio grupo, 5 en el padre, 10 en el abuelo o más arriba
  (`TipoDeSolicitud.apoyos_por_altura`), en 7 días; el sí del superadmin basta. Al aceptarse, se convoca
  sola con la visibilidad elegida. La visibilidad de una reunión no se cambia después.
- **Cartel (2A):** imagen (JPG, PNG o WebP, comprobada con Pillow) de hasta 5 MB, en la carpeta
  `ficheros/` del servidor (`MEDIA_ROOT`), que **no tiene dirección pública**: la entrega la vista
  `eventos:cartel` solo a quien ve el evento.
- **«¿Vas a ir?» (3A):** Sí, No, Aún no lo sé. Todos los que ven el evento ven cuántos van; los alias, solo
  quien convoca y quien tiene un cometido en el evento (y el superadmin).
- **Cometidos** (declarados en el contrato): facilitación, toma de acta, promoción y comunicación,
  logística, cuidados y oveja. Cada persona se apunta o se quita; quien gestiona el evento puede quitar a
  otras. En un evento privado, apuntarse da acceso. *(Las plazas por cometido y los obligatorios de una
  acción, más adelante.)*
- **Compartir:** texto para las redes (con botón «copiar») y enlaces para Telegram, WhatsApp, Mastodon y
  Bluesky.
- **Avisos:** «nuevos eventos que puedo ver» (a quienes lo ven; si es público, al grupo que convoca y sus
  subgrupos) y «se cancela un evento al que iba».
- Editar y cancelar: quien convoca, la administración del grupo (`grupos.editar_grupo`) o el superadmin.
- **Eventos de los grupos que administro y repaso de las listas** (15 de noviembre de 2026, [A-54],
  respuestas de la persona usuaria; era lo que quedaba de [A-37]):
  - «Administrar → Eventos y talentos → Eventos de mis grupos»: **tabla filtrable con pestañas** Próximos ·
    Esperan apoyos (con «1/2» apoyos) · Pasados · Cancelados, con los eventos de los grupos que administro
    **y de sus subgrupos** (todos, el superadmin). *Descartado:* cajas por grupo (largas y sin filtros).
  - La administración **ve, edita y cancela** los eventos de esos grupos, también los de los subgrupos y los
    que esperan apoyos. Ve cuántos van, **no quiénes** (sigue siendo de quien convoca y de los cometidos,
    3A). *Descartado de momento:* ver los alias.
  - Decidido sin preguntar (reversible): la administración ve los eventos de sus grupos aunque la
    visibilidad elegida no le llegue, porque tiene que poder editarlos y cancelarlos.
  - **Todas las listas de eventos** pasan a la tabla filtrable común (fecha y hora, evento, tipo, grupo,
    estado, cuántos van): «Eventos de mis grupos» (Próximos · Pasados) y «Mis eventos» (**Próximos ·
    Pasados · Series**, con la columna «Mi papel»: Convoco, Voy, Quizá).

### 10.4 Calendario

- Junta todo lo que tiene fecha (cada módulo lo aporta en su contrato), con un color por tipo y filtros.
  Vistas mes, semana, día y lista (en el móvil empieza en lista). Se arrastra lo propio.
- **Recordatorios:** cualquier usuario puede crear en el calendario una anotación libre, sin módulo detrás, y
  elegir si la ve su grupo. El admin del grupo puede hacerla visible a los grupos padre y abuelo.
- Calendario público y suscripción `.ics` con una clave secreta que se puede cambiar.

### 10.6 Cómo está hecho `calendario` (13 de noviembre de 2026, a partir de lo acordado en 10.4)

- **Contrato:** `FuenteDeCalendario` lleva ahora `color` (de CSS) y `mover` (función para arrastrar), y su
  función devuelve `FechaDeCalendario` (título, inicio, fin, día entero, enlace, tipo para los filtros,
  color, lugar y si esa persona puede arrastrarla). En lo de día entero, `fin` es el último día (no el
  siguiente, como hacen FullCalendar e iCalendar). Fuentes: «Eventos» (un color por tipo principal:
  Reunión violeta, Acción roja, Recaudatorio verde, Genérico azul; los cancelados en gris y los
  pendientes de apoyos, solo para quien convoca) y «Recordatorios».
- **Isla:** FullCalendar 6.1.22 (MIT), servido desde el propio servidor y cargado solo en el calendario.
  Mes, semana, día y lista (en el móvil empieza en lista del mes). Casillas de filtro por tipo, que se
  recuerdan en ese navegador. Se arrastra lo que se gestiona (los eventos propios o del grupo que se
  administra; los recordatorios propios). No se pasa algo con hora a día entero ni al revés. Pulsar un
  hueco abre «Apuntar un recordatorio» con ese día. Descartada la 7.x: salió en julio de 2026 y aún
  cambia cada pocas semanas.
- **Recordatorios:** en un grupo propio; «Solo yo» es contenido personal (ni el superadmin lo ve), «Mi
  grupo» llega también a sus subgrupos. Con el permiso `calendario.ampliar_recordatorios` (admin_grupo y
  admin_org), hasta el padre o el abuelo, si la organización lo permite. Los cambia o borra quien lo
  apuntó o la administración del grupo.
- **Suscripción .ics:** «Calendario → Suscripción» muestra la dirección con la clave secreta (se guarda
  tal cual para poder mostrarla siempre; descartado guardarla cifrada, que obligaría a enseñarla una
  sola vez) y un botón para cambiarla. El .ics trae los últimos 2 meses y el próximo año, se pide sin
  sesión y lleva título, tipo, lugar y enlace de cada fecha.
- **Menú:** sección «Calendario» (▦) con «Ver el calendario», «Recordatorios» y «Suscripción».
- *(Más adelante: el calendario público, con el módulo `publico`.)*

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


### 11.1 Cómo está hecho `debates`, versión sencilla (15 de noviembre de 2026, encargo tras [A-47])

Hecho sin preguntar, con lo que ya decía este apartado; las dudas que cambiarían algo esencial van al
apartado 20.
- **Abrir:** «Proponer un debate» (pregunta, contexto, opciones de partida, fecha de cierre opcional y
  quién participa) crea el debate «esperando apoyos» (solo lo ve quien lo propone) y una solicitud
  `debates.abrir` (2 apoyos, 15 días; basta el sí del superadmin). Al aceptarse se abre con su audiencia.
  Si cuelga de algo (una reunión, un proyecto, un acta, otro debate), toma su grupo y su audiencia.
- **Facilitación:** cometido `debates.facilitacion`, para quien lo propone; quien facilita (o la
  administración del grupo) la da a otras personas por alias, lo **amplía** (solo a más gente, nunca a
  menos) y lo **cierra** con una conclusión y, si quiere, la opción elegida.
- **Opciones nuevas: con 👍 dentro del debate, no con una solicitud.** Nacen «propuestas» y se abren
  cuando las apoyan N personas (2 de partida; sin contar a quien la propone).
  - *Motivo:* las solicitudes solo dejan una pendiente por persona y grupo, y frenarían el debate.
- **Votos:** un voto por persona y elemento (opción, argumento o el debate entero para 🤝); repetirlo lo
  quita y otro lo cambia; ⭐ y ⛔ piden justificación breve, que sale **sin nombre**. Solo se ven recuentos.
- **Recuentos y clasificación** calculados al pintar (no guardados en la opción): argumentos a favor,
  votos de cada tipo, argumento más apoyado y las dos clasificaciones (solo a favor; a favor menos en
  contra). Cuesta 9 consultas haya lo que haya.
- **Límites** (`LimitesDeDebate`), en cascada; vale siempre el más estricto (15 de noviembre de 2026,
  [A-51]):
  - de la plataforma (superadmin);
  - de cada organización (admin de organización);
  - de cada grupo (admin del grupo; valen también en sus subgrupos);
  - de cada debate (quien lo facilita, en «Límites de este debate» de su ficha).

  Los tres primeros se ponen en «Administrar → Mi organización → Debates» (`debates.limitar`). El
  cálculo común está en `base/limites.py` (`mas_estricto`). Palabras por intervención (blando: se marca; duro: no se publica), intervenciones por persona
  en el debate (al llegar al blando, una más y marcada; al duro, ya no), opciones nuevas por persona, apoyos
  para abrir una opción y si la fecha de fin es obligatoria. De partida: 250/400 palabras, 15/20
  intervenciones, 2 opciones, 2 apoyos.
- **Opción de consenso** (15 de noviembre de 2026, respuesta a la duda 4 del apartado 20): cualquiera la
  propone marcándola «de consenso»; se confirma sola cuando la apoyan (👍) N personas **que habían apoyado
  (⭐ o 👍) opciones distintas** del debate, cada una con una opción diferente (se empareja cada persona con
  una opción sin repetir: dos que venían de la misma opción cuentan como una). Al confirmarse, **las
  intervenciones vuelven a contar desde cero para todo el mundo y en todo el debate**
  (`Debate.intervenciones_desde`).
- **Al cerrar**, `debates.cerrado` lleva la conclusión al registro de decisiones.
- **Aún no:** límites por grupo y por debate, argumentos por opción, etiquetas y base de conocimiento,
  debate nuevo a partir de un argumento
  (hoy, «+ Debate» en el recuadro «Cuelga de aquí» del debate), lectura pública sin alias, chat, vista
  gráfica y resumen.

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


### 12.1 Cómo está hecho `consultas`, versión sencilla (15 de noviembre de 2026, encargo tras [A-47])

- **Quién crea** (15 de noviembre de 2026, respuesta a la duda 3 del apartado 20): la administración del
  grupo y de la organización (`consultas.crear`) la crea directamente; **cualquier miembro**
  (`consultas.proponer`) la propone: nace «propuesta» (solo la ve quien la propone), le pone las preguntas
  y pulsa «Pedir apoyos al grupo» (solicitud `consultas.abrir`, 2 apoyos, 15 días, basta el sí del
  superadmin, con las preguntas escritas en la solicitud). Desde ese momento las preguntas ya no cambian.
  Al aceptarse queda «aceptada» como las demás; si su apertura ya había pasado, se abre en ese momento y el
  cierre (y la publicación) se corren para que dure lo mismo.
  - *Descartado:* que cualquiera la cree sin apoyos (el grupo recibiría votaciones sin filtro).
- **Crear:** título,
  explicación, fechas, cuándo se ven los resultados (al cerrar, en una fecha posterior o en tiempo real, con
  el aviso), quién vota y quién ve los resultados (con el selector de siempre) y si se puede cambiar el voto.
  Las **preguntas** se ponen en su ficha y se pueden cambiar hasta que se abre.
- **Votar:** una persona, un voto. Sin cambio de voto, se avisa antes y un segundo voto se rechaza.
- **Secreto o público** (15 de noviembre de 2026, [A-51]): cada consulta elige (`Consulta.secreta`), y de
  partida es **secreta**. La ficha lo dice siempre, arriba, y la solicitud de apoyos también.
  - **Pública:** la papeleta lleva quién la vota y los resultados enseñan los alias de cada respuesta.
  - **Secreta de verdad:** la papeleta no se guarda al votar. Va a una **urna en Redis**
    (`consultas/urna.py`) y se guarda en la base en **tandas de 5 o más, desordenadas**, con un **número al
    azar** (UUID). Así no se puede emparejar con la fila de quién ha votado por su orden ni por la operación
    en la que se creó. Al cerrar se vacía lo que quede. Los resultados cuentan también lo que espera en la
    urna.
  - Redis guarda cada cambio en disco (`--appendonly yes`, con su volumen), para no perder papeletas al
    reiniciar.
  - *Descartado:* guardar la papeleta al votar con un número al azar. Seguiría creándose en la misma
    operación que la participación, y eso las empareja.
- **Voto secreto:** `Participacion` dice quién ha votado (sin hora) y `Papeleta` qué se ha votado (sin
  nombre ni hora; solo la asamblea base, para el desglose). Si se puede cambiar el voto, la papeleta lleva
  una clave HMAC del par consulta-persona con un secreto del servidor: con la base de datos sola no se sabe
  de quién es, pero con el secreto sí. **Provisional** hasta la bóveda real (fase 8; ver apartado 20).
- **Resultados** en barras (CSS, sin librería); las abiertas, como lista; desglose por grupos con 10 votos
  o más.
- **Cierre:** al pasar su fecha, se da por cerrada al abrir su ficha o con la tarea diaria
  `consultas.cerrar`; `consultas.cerrada` lleva al registro de decisiones el título y la respuesta más
  votada de cada pregunta.
- **Extras:** su cierre sale en el calendario (`consultas.cierres`) y la tarjeta «Consultas por votar» en
  «Inicio → Panel».
- **Aún no:** adjuntar ficheros como documentación (hoy, enlaces en Markdown), gráficos de verdad y avisos
  al abrirse.

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


### 13.1 Cómo está hecho `documentos`, versión sencilla (15 de noviembre de 2026, encargo tras [A-47])

- **Tipos:** orden del día, acta y documento libre. Se crean sueltos (en un grupo, con el selector de
  visibilidad) o **colgados** de una reunión o un proyecto (toman su grupo y su audiencia), desde el
  recuadro «Cuelga de aquí» de su ficha.
- **Escribir:** Markdown con **vista previa al momento** (htmx manda el texto medio segundo después de la
  última tecla), **sin tiempo real**. Si otra persona ha guardado mientras tanto, no se pisa: se avisa
  (número de versión).
  - *Al principio se dejó fuera* el editor colaborativo en tiempo real. Ya está hecho su esqueleto
    (13.2); este formulario queda para cuando no hay editor o no conecta.
- **Quién escribe:** quien tiene el cometido `documentos.redaccion` (quien lo crea, y quien le dé; hasta
  dos personas) o la toma de acta de la reunión de la que cuelga (`eventos.toma_de_acta`, por su código).
  Las demás personas que lo ven **comentan** hasta que se aprueba.
- **Autoría por párrafo:** al guardar se comparan los párrafos de antes y de después (`difflib`): los que
  no cambian conservan sus alias; los cambiados ponen al final a quien cambia; los nuevos, solo a quien
  escribe. Un título solo va con el párrafo que le sigue. Sale detrás de cada párrafo, en claro.
- **Registro de cambios** plegado arriba (quién, cuándo, cuántos párrafos), sin borrar nunca.
- **Acta desde el orden del día:** copia los puntos y añade «Asistentes», «Acuerdos alcanzados» y «Temas a
  discutir en la próxima reunión». Cada línea de acuerdos puede empezar por `[consenso]` o `[votación
  12-3-1]`. Al **aprobarla**, ya no se cambia y cada acuerdo sale con `documentos.acuerdo_tomado` hacia el
  registro de decisiones. Cada tema lleva «Proponer debate».
- **Aún no:** PDF con Typst, plantillas del superadmin (hoy, un texto de partida en el código), adjuntos.


### 13.2 Editor colaborativo en tiempo real: pieza aparte (15 de noviembre de 2026, respuestas 1 y 6 del apartado 20)

**Decidido por la persona usuaria:** colaboración en tiempo real de verdad. El editor es **una pieza aparte**,
que se irá mejorando y que **podrán usar otros proyectos**; el PDF de las actas, con **Typst, dentro del
editor**. La idea es acabar construyendo fuera un editor potente que esta herramienta use.

**Esqueleto hecho** (carpeta `editor/`, Node, todo MIT; detalle en `editor/LEEME.md`):
- **Servidor:** Hocuspocus sobre Yjs. Une lo que escriben varias personas a la vez sin pisarse y reparte
  los cambios por WebSocket. Guarda su copia de cada sala en ficheros.
- **Cliente:** CodeMirror con los cursores y los nombres de las demás personas en color. Se construye en
  un solo script (132 KB comprimido) que sirve el propio editor en `/cliente.js`.
  - *Sin colores de Markdown:* doblarían el peso, y la vista previa ya enseña cómo queda.

**Encaje con la plataforma:**
- **Contrato:** cada módulo que tenga textos editables declara un `TextoEditable` (tipo de ancla y tres
  funciones: permiso, texto inicial, guardar). `documentos` declara el suyo.
- **`base/editor.py` hace de puente:**
  - da los pases;
  - comprueba las firmas;
  - cierra salas;
  - y `base/vistas_del_editor.py` recibe las llamadas del editor y las pasa al módulo, sin importarlo.
- **La plataforma tiene siempre el texto bueno.** El editor avisa de lo escrito unos segundos después de
  cada cambio, con quién ha escrito.
  - Las autorías por párrafo y el registro de cambios siguen funcionando igual.
  - Si en ese rato han escrito dos personas, el párrafo cambiado lleva a las dos.
- **Sin editor** (`EDITOR_URL` vacío), todo funciona como antes, con el formulario. Si el editor no conecta,
  «Escribir sin directo» abre el formulario.

**Acceso y permisos:**
- **La plataforma decide; el editor solo comprueba.** Al abrir «Escribir», la plataforma pregunta al
  módulo qué puede hacer esa persona:
  - **escribir:** quien tiene la redacción, si es borrador;
  - **comentar:** quien lo ve, si es borrador;
  - **leer:** quien lo ve, si ya está aprobado;
  - **nada:** quien no lo ve.
- **El pase:** con eso, la plataforma le da un pase. Es un JWT HS256 que dura 5 minutos, con su alias, la
  sala y el permiso, firmado con el secreto que comparten la plataforma y el editor.
  - El editor no ve la base de datos ni conoce a las personas.
  - Quien no escribe entra de solo lectura: el servidor descarta lo que intente cambiar.
  - Quien no escribe ve «Seguir en directo» en la ficha.
- **Al reconectar**, el navegador pide un pase nuevo (`/editor/pase/`). Si ya no tiene permiso, no entra.
- **Al aprobar un acta o quitar la redacción**, la plataforma pide al editor que cierre la sala; quien
  vuelve, entra con su permiso de ahora. Si
  el editor guardara después, la plataforma responde 409 y el editor cierra la sala.
- **Entre servidores**, cada petición va firmada (HMAC del cuerpo y de la hora, con 5 minutos de margen).
- **Riesgos y lo que falta:** en «Seguridad y privacidad», apartado 9.

**Descartado:**
- **Que el editor tenga sus propios usuarios o lea la base de datos de la plataforma:** lo ataría a esta
  aplicación.
- **Etherpad o un editor completo ya hecho:** es más pesado, tiene su propio modelo de usuarios y no da la
  autoría por párrafo que ya existe.
- **Pases asimétricos (Ed25519) desde el principio:** HS256 basta mientras editor y plataforma son de la
  misma gente. Pasar a Ed25519 queda anotado para cuando lo usen otros.

**Ampliado el 15 de noviembre de 2026 ([A-51], respuestas de la persona usuaria):**
- **Repositorio propio:** el editor tiene su propio historial de git, dentro de `editor/` (la plataforma lo
  ignora). Aún no está publicado en ningún servidor.
- **Markdown, y Typst si se quiere:** cada documento elige al crearse en qué se escribe (`Documento.formato`):
  - **Markdown**, lo de partida y recomendado;
  - **Typst**, para maquetar a mano.

  El PDF sale con Typst en los dos casos (el Markdown se convierte dentro del editor).
- **Barra de formato** arriba del texto: negrita, cursiva, título, listas, cita, enlace, código, tabla y
  separador, con las marcas del formato del documento.
- **Vista Typst** al lado del texto, con un botón para encenderla:
  - **encendida**, se compila poco después de cada cambio;
  - **apagada**, no se ve y no se gasta nada;
  - **«Previsualizar»** compila una vez y **«PDF»** lo descarga.
  - **Cómo se compila:** en el servidor del editor (compilador de typst.ts para Node, Apache-2.0), en un hilo
    aparte, con 8 segundos como mucho, en una carpeta vacía y sin paquetes de internet.
  - *Descartado:* compilar en el navegador. Son unos 20 MB más para cada persona y el móvil sufre.
- **Comentarios anclados al texto:** se selecciona un trozo y «💬 Comentar»; queda resaltado y, al pulsarlo,
  sale un **bocadillo** debajo con el hilo, «Responder» y «✓ Resuelto».
  - Se guardan en el editor, en una sala aparte (`#comentarios`), con posiciones relativas de Yjs: siguen
    en su sitio aunque se escriba alrededor.
  - Pueden comentar quienes escriben y quienes comentan; quien solo lee, no.
  - *Elegido por sencillo y estable:* el bocadillo es un recuadro propio colocado bajo el trozo, sin
    tooltips de CodeMirror (se perdería lo que se está escribiendo al llegar una respuesta).
- **Comentarios y versiones registrados** (15 de noviembre de 2026, [A-52]):
  - **Comentarios:** el editor manda a la aplicación todos los comentarios de la sala cada vez que cambian,
    con el trozo que comentan (`POST /editor/comentarios/`, firmado). `documentos` los guarda
    (`ComentarioEnElTexto`) sin borrar ninguno y los enseña en la ficha.
  - **Versiones:** cada documento guarda versiones de su texto (`VersionDeDocumento`): una por cada rato
    de escritura (tras 10 minutos sin cambios empieza otra), otra al crearlo, otra al aprobarlo y otra al
    volver a una anterior. Cada versión se ve, se compara con lo de ahora (líneas en rojo y verde) y,
    quien tiene la redacción, puede volver a ella. Volver no borra nada: queda como una versión nueva.
- **Muchas personas a la vez:** ya no hay un máximo fijo de dos. Hay **límites en cascada**
  (`LimitesDeDocumento`) de cuántas personas escriben (tienen la redacción) y cuántas comentan a la vez;
  vale el más estricto:
  - la plataforma (superadmin);
  - cada organización (su admin);
  - cada grupo (su admin);
  - cada documento («Opciones» en su ficha, la administración de su grupo).

  Los tres primeros se ponen en «Administrar → Mi organización → Documentos». De partida, 10 escribiendo
  y comentarios sin límite. El pase lleva los máximos; quien llega de más entra a leer, con un aviso.

### 13.3 Biblioteca del editor: plantillas, fragmentos, cabeceras y pies, e imágenes (15 de noviembre de 2026, [A-52] y [A-53])

Pedido por la persona usuaria en [A-52]; respuestas a las cuatro preguntas en [A-53].

- **Vive en el editor** (no en la plataforma), porque el editor es para varias herramientas. Lo de una
  aplicación nunca lo ve otra.
- **Cuatro árboles** de carpetas y subcarpetas:
  - **Plantillas**: *todo* lo que puede llevar un documento de partida (respuesta 4: «anything can go in the
    template»): su aspecto en Typst (página, letra, títulos; la variable `titulo`) y, si se quiere, un
    texto de partida. Cada documento elige la suya en el desplegable «Plantilla»; si el texto está vacío, se
    pone el de partida.
  - **Fragmentos** (la «enciclopedia»): texto, código o las dos cosas. Se meten con un clic desde el cajón
    «📚 Fragmentos e imágenes».
  - **Cabeceras y pies** (membretes): **se eligen aparte**, como una plantilla (respuesta 3), en el
    desplegable «Cabecera y pie».
  - **Imágenes**: PNG, JPEG o GIF, de 2 MB como mucho, en carpetas como `ORG Tajo / plantillas` o
    `ORG Tajo / grupos`. Se ponen en el texto (`![nombre](imagen:<número>)`), en las plantillas y en los
    membretes.
- **Quién crea y cambia** (respuestas 1 y 2):
  - lo común, el superadmin; lo de cada organización, su admin;
  - **cualquier persona crea sus propias plantillas y fragmentos** y los **comparte con un grupo o con
    personas sueltas**;
  - las imágenes y las carpetas de primer nivel, la administración.
- **Cómo lo sabe el editor:** el pase lleva un número de la persona que no dice quién es
  (`base.editor.id_para_editor`, HMAC) y sus **ámbitos**: toda la plataforma (`comun`), sus organizaciones
  (`o<n>`) y sus grupos, también los que contienen a los suyos (`g<n>`). Lleva «cambiar» en los que
  administra. Los da `grupos` (contrato: `ambitos_del_editor`). Para compartir con personas, el navegador
  busca en la plataforma (`grupos:personas_para_editor`), que solo devuelve a quien se puede ver.
- **Desde esta plataforma, solo actas:** las carpetas de primer nivel de plantillas y fragmentos que ve la
  plataforma se limitan a «Actas» (`"carpetas": ["Actas"]` en la configuración del editor). Las cabeceras y
  pies y las imágenes no se limitan así: son de cada organización.
- **Cifrado** (respuesta 1: «los snippets se almacenan encriptados»): se cifra **toda** la biblioteca, no
  solo los fragmentos, con AES-256-GCM y la clave `EDITOR_CLAVE`. Ver «Seguridad y privacidad», 9.7.
- **Dónde se ve:** «Participación → Plantillas de documentos» (pestañas Plantillas, Cabeceras y pies,
  Imágenes) y «Participación → Enciclopedia de fragmentos». La pantalla la pinta el propio editor
  (`EditorColaborativo.montarBiblioteca`), con la isla «bibliotecaDelEditor».
- *Descartado:*
  - guardar la biblioteca en la plataforma: el editor no podría servirla a otras herramientas;
  - cifrar solo los fragmentos: es el mismo código y protege también los nombres de las carpetas;
  - escribir plantillas a la vez (en tiempo real): de momento, cada cual en su ficha, con «Guardar» y
    «Previsualizar».

**Por hacer** (en `editor/LEEME.md`):
- PDF con Typst: la dirección ya existe y responde «aún no»;
- comentarios anclados al texto;
- autoría letra a letra;
- expulsar a una persona sin cerrar la sala;
- varias instancias con Redis.

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

### 14.1.1 Cómo está hecho `proyectos`, primera pieza (13 de noviembre de 2026, decisiones 1A, 2A, 3A y 4A)

- **Subproyectos en todos (petición de la persona usuaria):** cualquier proyecto, también uno personal,
  puede tener subproyectos, y estos los suyos, sin límite. Cada proyecto guarda su `padre` y su `raiz`
  (el principal de su árbol), para cargar el árbol entero con una consulta. Un subproyecto es del grupo
  de su padre (y personal si el padre lo es) y tiene su propia visibilidad (de entrada, la del padre).
  Desde un subproyecto visible bajo uno que no se ve, el camino dice «(un proyecto que no puedes ver)».
- **Primero proyectos y tareas (1A):** tipología con sus campos, objetivo general, objetivos específicos,
  alcance, riesgos, inicio, fecha límite y estado. Recursos, dependencias, documentación por bloques,
  chat y etiquetas, en la siguiente pieza.
- **Quién gestiona:** quien lo creó o lo coordina (cometido `proyectos.coordinacion`), o creó o coordina
  un antecesor; la administración del grupo; el superadmin (salvo lo personal). La coordinación solo la
  da quien gestiona; documentación y comunicación, cada cual se apunta si ve el proyecto. Crear proyectos
  y tareas sueltas: permiso `proyectos.crear` (usuario, admin_grupo, admin_org).
- **Tareas:** en un proyecto (la ve quien ve el proyecto; responsable y colaboradoras deben verlo, y en
  uno privado pasan a verlo), sueltas en un grupo (con su visibilidad) o personales. Aviso «Me encargan
  una tarea». Pueden cambiarlas su responsable, quien colabora, quien la creó y quien gestiona el
  proyecto.
- **Kanban (2A):** isla con SortableJS: columnas pendiente, en curso, bloqueada y hecha. El de un proyecto
  incluye las tareas de todos sus subproyectos; también «Mis tareas → Kanban». Solo se arrastra lo que se
  puede cambiar. (El bloqueo automático por dependencias, en el apartado 14.1.2.)
- **Personales (3A):** proyectos (con subproyectos) y tareas «privados e individuales», con audiencia
  personal: ni el superadmin los ve. Pantalla «Proyectos → Personales».
- **Calendario:** fuentes «Proyectos» (fechas límite) y «Tareas» (las no hechas), de día entero, que se
  arrastran para cambiar la fecha.
- **`limpieza` (4A):** después de proyectos, como tarea diaria.

### 14.1.2 Dependencias y recursos (13 de noviembre de 2026, decisiones 1A y 2A de la persona usuaria)

- **Dependencias entre tareas, con bloqueo automático (1A).** Una tarea de un proyecto puede «esperar a»
  otras tareas de su mismo árbol (el proyecto principal y todos sus subproyectos). Mientras alguna no
  está hecha, pasa sola a «Bloqueada» (`bloqueo_automatico`); cuando lo están todas, vuelve sola a
  «Pendiente» y se avisa a su responsable («Una tarea mía ya no espera a nada»). Si una tarea esperada
  vuelve atrás, la que esperaba se bloquea de nuevo; si se borra, la que esperaba se pone al día. Una
  tarea que espera no se puede sacar de «Bloqueada» a mano (el kanban muestra por qué y la devuelve a
  su sitio). Lo bloqueado a mano no se desbloquea solo. No se permiten círculos ni esperar a tareas de
  otro árbol; las sueltas y las personales no tienen dependencias. Se eligen en el formulario de la
  tarea (casillas con las tareas del árbol) y la ficha muestra «Espera a» y «La esperan». Si al mover
  una tarea cambian otras, el kanban se recarga. *Descartado (1B):* marcar dependencias sin bloquear
  solas.
- **Recursos, una lista sencilla (2A).** Cada proyecto tiene sus recursos (`Recurso`: qué, cuánto, de
  dónde sale y si ya se tiene). Quien gestiona el proyecto los apunta, los marca como conseguidos y los
  quita. Si además puede pedir talentos al grupo (`talentos.pedir`), «Pedir al grupo» crea una petición
  de talentos con el título del proyecto, el recurso (que entra en el catálogo como «recurso») y la
  cantidad si es un número, anclada al proyecto; el recurso enlaza a su petición. *Descartado (2B):* un
  texto libre. *(Aún no: tipos de recurso configurables, totales que suman tareas y subproyectos, y
  dependencias entre proyectos con su vista gráfica.)*

### 14.1.3 Etiquetas y tareas modelo (13 de noviembre de 2026, decisión 1A de la persona usuaria)

- **Se cierra `proyectos` con lo pequeño (1A).** La documentación por bloques irá con `documentos` (fase
  5) y el chat, con el tiempo real. *Descartado (1B):* hacer ahora la documentación dentro de `proyectos`
  y encajarla después.
- **Etiquetas:** los proyectos de grupo llevan etiquetas de su organización (o comunes), con el selector
  común (`CampoDeEtiquetas`) al crear y al editar. Salen en la ficha y en la lista de «De mis grupos»;
  al pulsar una, la lista muestra solo los que la llevan (`?etiqueta=`). Los personales no llevan
  etiquetas (no tienen organización y crearían etiquetas comunes).
- **Tareas modelo (apartado 9):** `TareaModelo` en `tipologias` (título, descripción, plazo en días y «espera
  a la anterior»), solo en los tipos de proyecto. Se heredan como los campos y se añaden o quitan en
  «Configuración → Tipologías → De proyectos». Al crear un proyecto de ese tipo, la casilla «Crear las N
  tareas modelo» (marcada de entrada) las crea con quien lo crea como responsable, la fecha límite a esos
  días y, si esperan a la anterior, como dependencia (bloqueadas hasta que esté hecha). De ejemplo,
  «Preparación de acción»: pedir permiso, preparar el material y difundir.

### 14.1.4 Árboles de proyectos (14 de noviembre de 2026, [A-43] y [A-44]: decisiones 1B, 2A y 3 de la persona usuaria)

Los proyectos se ven como los grupos: un árbol por proyecto principal, con el mismo protocolo visual
(apartado 8.1, «Árboles de grupos»). Lo pidió la persona usuaria en docs/todo.md («Siempre que haya una
jerarquía… han de aparecer en árbol»; «Árbol de proyectos: cada árbol en una celda de tabla de 3 columnas»).
- **Rejilla:** un árbol por celda, hasta 3 columnas (2 en pantallas medianas, 1 en el móvil), en «De mis
  grupos» y en «Personales» (3). Arriba de cada celda, el grupo que coordina el proyecto principal en una
  etiqueta verde («Personal» si lo es), con su organización al lado.
- **Las tareas, dentro del árbol y plegadas (1B):** junto a cada proyecto, «(hechas/totales)» y una
  flecha ▸ que las despliega. Es un `<details>` de HTML: se abre sin JavaScript.
  - *Descartado (1A):* solo proyectos, con el número de tareas.
- **Colores (2A):** con fondo amarillo, los proyectos en los que participas (los creaste, tienes un
  cometido o tienes una tarea en ellos); con recuadro rojo, el que miras (en su ficha sale arriba su árbol
  entero); en gris, los finalizados. *Descartado (2B):* amarillo solo para los que coordinas o creaste.
- **En la ficha** se mantiene el camino («Proyectos › Huerto › Riego») y el árbol va encima. Las listas de
  subproyectos y de tareas que había debajo se quitan porque repetían el árbol (decisión de la persona
  usuaria tras [A-45]); «+ Tarea» pasa junto a «Kanban». La ficha cuesta 10 consultas.
- **Cómo está hecho:** `proyectos/arboles.py` (`arboles_de_proyectos`, 2 consultas sean cuantos sean los
  proyectos y las tareas; `en_los_que_participa`, que usa también la tarjeta de Inicio) y las plantillas
  `proyectos/arboles.html`, `nodo_de_proyecto.html` (se incluye a sí misma) y `_titulo_en_arbol.html`.
  Reutiliza las clases de los árboles de grupos (`arbol`, `arbol-base`, `arbol-actual`) y añade
  `arbol-coordina` y `arbol-tareas`. La lista pasa de 3 a 5 consultas; la ficha, de 9 a 11.
- **Otras jerarquías** (la persona usuaria pidió que se le indicaran): las tipologías siguen el mismo
  protocolo (decidido en [A-44]); las etiquetas relacionadas no son un árbol sino una red; las respuestas
  de los debates y los puntos de un orden del día lo seguirán cuando existan.

### 14.2 Tarea

- Atómica: **1 responsable** obligatorio y colaboradores opcionales.
- Puede estar en un **proyecto**, ser una **tarea suelta de un grupo** o una **tarea personal** (solo la ve
  su dueño).
- Descripción, fecha límite y recursos que necesita.
- Estados: pendiente, en curso, bloqueada, hecha (las columnas del kanban). Se bloquea y desbloquea sola
  según sus dependencias; no se permiten dependencias en círculo.

**Ficha de una tarea (14 de noviembre de 2026, [A-44], punto 4 de la persona usuaria).**
- **Camino:** «Tareas › Huerto › Riego › la tarea», con los proyectos de los que viene en violeta
  (`miga-de-proyecto`), para que se distingan del resto del camino. En una tarea suelta, su grupo (en
  verde, como en los árboles de proyectos); en una personal, «Personales».
- **Lo ya escrito se cambia encima:** el título, el estado, la fecha límite y la descripción. Se pulsa el
  dato (o ✎), se convierte en su cuadro con el valor de ahora, Intro o «Guardar» lo guarda sin recargar la
  página (htmx manda solo ese dato a `proyectos:tarea_campo`, que devuelve el trozo ya cambiado o con el
  error) y Escape o «Cancelar» lo deja como estaba. Es `proyectos/_campo_de_tarea.html`, con Alpine solo
  para abrir y cerrar.
- **Lo que no está escrito, en el desplegable** («Completar o cambiar todo», antes «Cambiar»), que
  enseña todos los valores de ahora para cambiarlos sobre ellos. Las personas y las dependencias, que
  necesitan el selector o las casillas, se cambian también ahí: su ✎ abre el desplegable.
- Guardar un dato hace las mismas comprobaciones que el formulario (dependencias, quién ve el proyecto,
  avisos a la nueva responsable): llama al mismo servicio, `editar_tarea`. La ficha pasa de 8 a 10
  consultas por el camino.
  - *Descartado:* guardar al salir del cuadro (sin pulsar nada): un clic fuera por error cambiaría la
    tarea.

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

**Cómo está hecha (13 de noviembre de 2026, decisiones 1A, 2A y 3A de la persona usuaria).**
- **Cada módulo dice qué es «terminado» (1A).** `Limpiable(codigo, modelo, nombre, terminados, ficha,
  archivar_a, borrar_a)`: `terminados(antes)` devuelve la consulta de lo que está sin archivar y terminó
  antes de ese momento. El modelo lleva `titulo`, `audiencia` y `archivado` (lo comprueba `manage.py
  check`). Archivar es poner la fecha en `archivado`: el módulo lo saca de sus listas, pero la ficha
  sigue abriéndose por su enlace (con un aviso «Archivado el…») y todo se ve en **«Archivo →
  Archivados»**, filtrable por tipo y por «Se borra pronto». *Descartado (1B):* ocultar sin pestaña.
- **Qué cuenta como terminado:** proyectos principales finalizados (los subproyectos y sus tareas siguen
  al principal: se archivan y se borran con él), tareas hechas sueltas y personales, eventos convocados o
  cancelados ya pasados (no los pendientes de apoyos, que caducan con su solicitud) y recordatorios
  pasados. Proyecto y Tarea guardan `terminado` (cuándo se finalizó o se hizo); si se reabren, pierden
  esa fecha y la de archivo, y la limpieza los quita del archivo. Los eventos y recordatorios archivados
  **siguen en el calendario** (es historia, no una lista).
- **Plazos de partida (2A):** archivar a los 30 días de terminar y borrar a los 365 de archivar. El
  superadmin los cambia o para un tipo en **«Configuración → Limpieza»** (`Plazo`; sin fila, los de
  partida del contrato). Como de momento solo hay proyectos con lo suyo dentro, «lo asociado a un proyecto»
  no tiene plazos propios: sigue al proyecto.
- **Antes de borrar (3A):** 15 días antes se avisa a quienes lo ven (notificación «Se va a borrar algo
  archivado que veo», una por persona con cuántos elementos), que pueden pulsar **«Conservar»**: sigue
  archivado, pero no se borra solo. Nunca se borra nada sin ese aviso con 15 días de margen, aunque se
  acorten los plazos. Al archivar también se avisa. *Descartado (3B):* avisar sin poder conservar.
- **Quién:** «Conservar», quien lo ve (proteger es inofensivo); «Dejar de conservar» y **«Borrar ya»**
  (podar a mano), solo el superadmin. Lo personal solo lo ve su dueña, también en el archivo.
- **Registro de borrados** (`Borrado`: tipo, título, quién lo veía, cuándo se archivó y se borró, y si fue
  por el plazo o a mano). Se ve en «Archivo → Borrados» con la audiencia que tenía. Nunca se borra.
- **Sin archivo:** las notificaciones vistas se borran a los 90 días de verlas y las no vistas a los 365
  de llegar (`Limpiable` con `borrar`: lo borra su módulo, que pone al día el número sin ver).
- **Cuándo:** tarea diaria `limpieza.limpiar` del trabajador, en lotes de 2000 por tipo y vuelta.
- *(Pendiente: las actas y las decisiones llegarán en la fase 5; las decisiones no declaran `Limpiable`,
  y las actas aprobadas tendrán su plazo de descarga al diseñarlas. Las series terminadas de eventos aún
  no se limpian.)*

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


### 16.1 Cómo está hecho `decisiones` (15 de noviembre de 2026, encargo tras [A-47])

- Una tabla, `Decision`: texto, cómo se tomó (consenso, votación, debate, consulta), detalle (recuento),
  grupo, audiencia (la de su origen: la ve quien podía participar), origen (ancla y enlace), fecha y
  «sustituida por».
- **Se llena sola** escuchando `documentos.acuerdo_tomado`, `debates.cerrado` y `consultas.cerrada`, que
  traen todos los datos (así no importa esos módulos). Si llega dos veces, no se repite.
- **Pantallas:** «Vigentes» y «Todas», con la tabla filtrable al momento (por cómo y por grupo, y
  búsqueda); la ficha, con su origen. La administración del grupo (`decisiones.sustituir`) la marca como
  sustituida por otra más nueva del mismo grupo.
- La sección del menú «Participación» (debates, consultas, órdenes del día y actas, decisiones) la declara
  este módulo y abre los debates.

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

**Cómo están hechas las notificaciones (13 de noviembre de 2026, decisiones 1A, 2A, 3A y 4A de la
persona usuaria).** Primera pieza de `comunicaciones`: solo notificaciones en la web. Los mensajes y
conversaciones son la pieza siguiente; el correo, el chat y Telegram, después.
- **Cada módulo declara sus avisos (1A).** En su contrato, `avisos = (TipoDeAviso(código, nombre,
  origen, eventos_sw, preparar),)`. La función `preparar` recibe los datos del eventos_sw y devuelve
  `AvisoPreparado(usuarios, texto, enlace)`: a quién y qué (sin contar nada que esas personas no puedan
  ver). `comunicaciones` declara `reparte_avisos` y el registro le añade sola una escucha asíncrona por
  cada aviso, con el código del aviso como dato fijo (`Escucha.extra`). Así `comunicaciones` no sabe
  nada de los demás módulos. *Descartado:* que `comunicaciones` escuchara y redactara cada aviso
  (acabaría conociendo todos los módulos).
- **Orígenes (bandejas):** organización y grupos, superadmin, admins, proyectos, eventos, debates,
  solicitudes y sistema (`ORIGENES_DE_AVISO`). Se añade «Organización y grupos» a la lista del diseño
  para los avisos de `grupos`.
- **Trabajador (2A):** servicio `trabajador` en docker que ejecuta `procesar_bandeja --espera 2`. Sin
  Celery ni RQ todavía; cuando se elijan, solo cambiará quién llama a la bandeja.
- **Número sin ver (3A):** «Comunicaciones → Notificaciones (N)», con `EntradaDeMenu.contador`, guardado
  en la caché por persona y borrado al repartir, marcar o borrar. Se pone al día al navegar
  (`hx-swap-oob`). El tiempo real (Channels) llegará con el chat.
- **Bandeja:** pestañas por origen con las sin ver de cada una; cada notificación se abre (queda vista y
  lleva a su enlace, solo dentro de la aplicación), se marca como vista o se borra con su **papelera**.
  Arriba, «Marcar todas como vistas» y **«Limpiar las vistas»** (borra todas las ya vistas; las no vistas
  se quedan), a petición de la persona usuaria.
- **Conservación (4A):** las vistas se borrarán a los 90 días y las no vistas a los 365, con el módulo
  `limpieza` (fase 4), y el superadmin podrá cambiar los plazos. Mientras, cada persona limpia las suyas.
- **Preferencias:** «Comunicaciones → Preferencias de aviso», una casilla por tipo de aviso, agrupados por
  origen. Solo se guarda lo desactivado (`PreferenciaDeAviso`); sin fila, activado. De momento, un canal
  (la web).
- **Primeros avisos, de `grupos`:** te han admitido en un grupo, ha cambiado tu rol, te han nombrado admin
  de una organización, otra organización ha invitado a un grupo que administras (a sus admins y a los de
  su organización) y han aceptado o rechazado una invitación de tu grupo (a quien invitó y a los admins).
  Para ello `grupos` emite tres eventos_sw nuevos: `grupos.admitido`, `grupos.rol_cambiado` y
  `grupos.admin_de_organizacion_nombrado`.

**Avisos y conversaciones con la administración (13 de noviembre de 2026, a petición de la persona
usuaria).** Sustituye a los «mensajes» del principio de este apartado. Los mensajes entre personas
llegarán con el chat (más adelante).
- **Se escribe a la administración, nunca al alias de un admin.** Hay tres: la de un grupo, la de una
  organización y la de la plataforma (el superadmin) (`comunicaciones/administraciones.py`).
- **Avisos de la administración:** el superadmin y los admins (permiso `comunicaciones.avisar`, de
  entrada admin del grupo y admin de la organización) avisan, en nombre de una de sus administraciones, a
  grupos (con sus subgrupos) o a personas, siempre dentro de lo que esa administración alcanza. Cada aviso
  lleva un **nivel con su color** y llega como notificación (no se puede desactivar). Con la casilla «Se
  puede responder», el aviso trae un enlace para abrir una conversación con esa administración.
- **Niveles de aviso** editables (`NivelDeAviso`: nombre, descripción, color y orden) en «Configuración →
  Niveles de aviso», solo el superadmin (`comunicaciones.niveles`). Iniciales: Información (azul),
  Atención (ámbar) y Problema (rojo). Uno usado no se borra.
- **Conversaciones con la administración:** siempre está «Escribir a la administración» (la de cualquiera
  de sus grupos o de los que los contienen, la de su organización o el superadmin). Cada conversación es
  de una persona con una administración (3A) y la atienden todos sus admins, como un buzón compartido
  (2A). La pueden leer los admins de ese grupo, los de su organización y el superadmin (3A de la segunda
  ronda: son temas administrativos; las conversaciones entre personas, no). Quien responde firma
  **«Admin de GRU Henares (Lince)»**. Tienen asunto y **estado** (abierta, en proceso, solucionada), que
  cambian los admins. Se ven con borde violeta y salen primero las que tienen algo sin leer. Número en el
  menú: «Con la administración (N)».
- **Casi en tiempo real (1A):** con una conversación abierta, htmx vuelve a pedir los mensajes cada 10
  segundos. *Descartado por ahora:* Channels y websockets (llegarán con el chat de grupos y proyectos, que
  podrá reutilizar `Conversacion` y `Mensaje`).
- *(Más adelante: temas o categorías de las conversaciones, y el chat.)*

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

**Dudas de las fases 5, 6 y 7, contestadas el 15 de noviembre de 2026** ([A-50]):
1. **Tiempo real:** sí, en una pieza aparte reutilizable (13.2).
2. **Voto secreto con cambio de voto:** se deja así hasta la bóveda. Riesgos en «Seguridad y privacidad».
3. **Consultas:** cualquier miembro, con apoyos (12.1).
4. **Opción de consenso:** apoyos de gente que había apoyado opciones distintas; las intervenciones vuelven a
   contar para todo el mundo (11.1).
5. **Límites de los debates:** pendiente. La persona usuaria no entendió la pregunta; se le explica en [A-50].
6. **PDF:** con Typst, dentro del editor (13.2).

**Respuestas del 15 de noviembre de 2026 ([A-51]):**
- **Límites de los debates:** también por grupo (su admin) y por debate (quien facilita). Vale el más
  estricto (11.1).
- **Formato del texto:** Markdown, con la opción de Typst, barra de formato y vista Typst que se enciende y
  se apaga (13.2).
- **Comentarios:** anclados al trozo, con bocadillo (13.2).
- **Repositorio:** aparte (13.2). Falta decidir dónde se publica.
- **Voto secreto:** opción de cada consulta, secreta de partida y de verdad; cada votación lo dice (12.1).

**Plantillas, fragmentos e imágenes del editor**, contestado el 15 de noviembre de 2026 ([A-53]); hecho en
13.3:
1. **Dónde:** todo vive en el editor, y los fragmentos se guardan cifrados (se cifra toda la biblioteca).
2. **Quién:** la administración (común: superadmin; organización: su admin), y además cualquier persona
   crea sus propias plantillas y fragmentos y los comparte con un grupo o con personas.
3. **Cabecera y pie:** se eligen, como una plantilla.
4. **Plantilla:** aspecto y texto de partida; puede llevar cualquier cosa.

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
