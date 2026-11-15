# Tutorial del proyecto (versión 2)

Lo que se va explicando para aprender, en el orden en que aparece. Cada entrada dice qué es, para qué
sirve aquí y dónde se usa.

## 1. El esqueleto (12 de noviembre de 2026)

- **Contenedor de desarrollo** (`.devcontainer/`): VS Code abre el proyecto dentro de un contenedor
  Docker que ya trae Python, PostgreSQL y Redis. Así todo el mundo trabaja con lo mismo.
- **`config/settings.py`**: los ajustes que Django lee al arrancar. Tres decisiones de rendimiento
  desde el primer día:
  - **JIT apagado** (`-c jit=off`). El JIT es un compilador de PostgreSQL pensado para consultas
    analíticas enormes. En consultas pequeñas, como las de una página web, tarda más en compilar que
    en ejecutar. En la versión 1 se llevaba 370 de los 440 ms de una consulta.
  - **Conexiones persistentes** (`conn_max_age=60`). Abrir una conexión con la base cuesta tiempo, así
    que se reutiliza durante 60 segundos.
  - **Caché en Redis**. Lo que se calcula por persona (permisos, audiencias) se guarda en memoria para
    no repetirlo en cada petición.
- **¿Por qué no se ejecuta todavía `migrate`?** Django guarda en la primera migración qué tabla es la
  de usuarios. Si se crean las tablas antes de decirle que el usuario es el `Usuario` de la app `usuarios`, después es muy
  difícil cambiarlo.

## 2. El contrato de módulo (12 de noviembre de 2026)

- **Qué es una «app» de Django.** Una carpeta con su `apps.py`, sus modelos, sus vistas… Aquí cada app es
  un **módulo** de la aplicación (`base`, `eventos`, `debates`…). Django la conoce porque está en
  `INSTALLED_APPS`, en `config/settings.py`.
- **`apps.py` y `AppConfig`.** En `apps.py` hay una clase que describe la app. Django crea una copia
  de esa clase al arrancar y, cuando ya están todas cargadas, llama a su método `ready()`.
- **El contrato** (`base/contrato.py`). Nuestra clase `ModuloConfig` hereda de `AppConfig` y le añade
  apartados: permisos, eventos_sw que emite y que escucha, menú, ayuda… Cada módulo rellena los suyos.
  Así, para saber qué aporta un módulo, basta con leer una sola clase.
- **Fichas inmutables** (`@dataclass(frozen=True)`). Cada cosa declarada es una clase pequeña de solo
  datos, que no se puede cambiar después de crearla. Así nadie modifica el contrato por accidente
  mientras la aplicación funciona.
- **El registro** (`base/registro.py`). En `BaseConfig.ready()` se recorren todas las apps una vez y se
  reúne lo declarado en diccionarios: `registro.permisos`, `registro.escuchas`, `registro.menu`… El
  resto del código pregunta ahí.
- **Las comprobaciones de Django** (`base/comprobaciones.py`). Una función marcada con
  `@checks.register` se ejecuta al arrancar y con `python manage.py check`. Si devuelve errores, Django
  los muestra y no arranca. Así una errata en el contrato se ve enseguida, no el día en que falla una
  pantalla.
- **Nombrar sin importar.** Un módulo dice «escucho `consultas.cerrada` con la función
  `decisiones.receptores.copiar`» con textos. Nadie importa el módulo de otro: por eso los módulos
  funcionales pueden ser independientes.
- **Vigilar las capas leyendo el código** (`base/dependencias.py`). El módulo `ast` de Python convierte
  un fichero en un árbol que se puede recorrer sin ejecutarlo. La prueba busca cada `import` y comprueba
  que respeta la regla de capas.
- **`SimpleTestCase`.** Es una prueba que no usa la base de datos. Por eso estas pruebas tardan
  milésimas y funcionan aunque todavía no se haya ejecutado `migrate`.

## 3. Los avisos internos: eventos_sw (12 de noviembre de 2026)

- **Para qué.** Un módulo anuncia que algo ha pasado y otros reaccionan sin conocerse. `consultas` no
  sabe que `decisiones` existe. Solo dice `emitir("consultas.cerrada", consulta_id=7)`, y `decisiones`
  declara en su contrato que lo escucha.
- **Transacción** (`transaction.atomic()`). Es un bloque de cambios en la base de datos que se guardan
  todos o ninguno. Si algo falla dentro, PostgreSQL deshace todo el bloque. Por eso `emitir()` exige
  estar dentro de uno: el cambio y sus avisos van juntos.
- **Síncrono y asíncrono.**
  - Síncrono: el receptor se ejecuta en el acto, dentro de la misma transacción. Úsalo para lo que debe
    ocurrir sí o sí, como invalidar la caché.
  - Asíncrono: se apunta en una tabla y otro proceso lo hace después. Úsalo para lo lento o lo que
    depende de fuera, como enviar un correo.
- **Bandeja de salida** (patrón *outbox*). En lugar de enviar el correo dentro de la transacción (¿y si
  luego se deshace?), se guarda una fila «pendiente» dentro de la misma transacción. Si la transacción
  se deshace, la fila tampoco existe. Si se confirma, el trabajador la encontrará.
- **El trabajador** (`python manage.py procesar_bandeja`). Es una orden propia de `manage.py`: Django
  busca las órdenes en `<módulo>/management/commands/`. Se deja funcionando en otra terminal.
- **`SELECT … FOR UPDATE SKIP LOCKED`** (`select_for_update(skip_locked=True)`). Bloquea las filas que
  el proceso va a tratar, y otro proceso que llegue a la vez se las salta en lugar de esperar. Así
  pueden trabajar varios trabajadores sin hacer dos veces el mismo aviso.
- **Puntos de guardado.** Un `transaction.atomic()` dentro de otro crea un punto de guardado. Si falla
  un aviso, se deshace solo lo suyo, y los demás de la tanda siguen adelante.
- **Reintentos con espera creciente** (1, 2, 4, 8 minutos). Así, si un servicio externo está caído un
  rato, no se le machaca, y tras 5 fallos alguien tiene que mirarlo.
- **Migraciones.** `python manage.py makemigrations` escribe en `migrations/` las órdenes para crear la
  tabla a partir de `models.py`. Las pruebas las aplican en una base temporal que se borra al terminar.
  En la base real aún no se aplican (no se ejecuta `migrate` hasta que exista `usuarios`).
- **`assertNumQueries`.** Comprueba cuántas consultas hace un trozo de código. Aquí asegura que
  apuntar varios avisos cuesta una sola consulta (`bulk_create`).

## 4. Medir el coste de cada pantalla (12 de noviembre de 2026)

- **Por qué contar consultas.** Cada consulta a PostgreSQL es un viaje de ida y vuelta. Una pantalla
  rápida hace pocas consultas, y siempre las mismas, tenga 10 filas o 500.
- **El error típico: «N+1».** Se traen las filas con una consulta y, luego, por cada fila, se pide algo
  más (su grupo, su autor…), lo que suma una consulta por fila. Con 5 filas no se nota, pero con 500 la
  pantalla tarda segundos. En Django se evita con `select_related` y `prefetch_related`, que traen lo
  relacionado de una vez.
- **`comprobar_consultas(url, n, crear_mas_datos)`** (`base/pruebas.py`):
  1. Visita la pantalla una vez para calentarla.
  2. La visita otra vez y cuenta las consultas, que deben ser exactamente `n`.
  3. Añade filas y la vuelve a contar: si sale más de `n`, hay un N+1.

  Las pruebas de `base/tests/test_pruebas_de_pantalla.py` lo demuestran con una pantalla buena y otra mala.
- **`override_settings`.** Cambia un ajuste solo durante una prueba. Ahí se usa para que la aplicación
  use una lista de direcciones de mentira (`ROOT_URLCONF`).
- **La barra de depuración.** Con `runserver` en marcha, a la derecha de cada página sale una barra.
  En «SQL» se ven todas las consultas de esa página, con su tiempo, y las repetidas marcadas: es la
  forma rápida de encontrar un N+1 mientras se programa.
- **Ajustes distintos en las pruebas** (`PROBANDO` en `config/settings.py`):
  - La caché va en la memoria del propio proceso, para que cada ejecución empiece limpia.
  - Las contraseñas se cifran con MD5, que es rápido. Argon2 es lento a propósito, para frenar a quien
    intente adivinarlas, y en las pruebas solo haría perder tiempo.

## 5. La plantilla general: Tailwind, htmx y Alpine (12 de noviembre de 2026)

- **Tailwind.** En lugar de escribir CSS, se ponen clases pequeñas en el HTML: `p-4` (relleno), `flex`,
  `text-sm`, `dark:bg-slate-900` (fondo oscuro en modo oscuro)… `npm run construir` lee las plantillas y
  genera un CSS solo con las clases que se usan. Mientras programas, `npm run vigilar` lo regenera al
  guardar. Si una clase nueva no hace nada, casi siempre es que no se ha vuelto a construir.
- **npm y `package.json`.** npm es el instalador de librerías de JavaScript. `package.json` dice cuáles
  y en qué versión exacta, y `package-lock.json` fija también las de sus dependencias. Se instalan en
  `node_modules/`, que no se guarda en Git.
- **htmx.** Permite que un enlace o un botón pida HTML al servidor y lo coloque en un trozo de la página,
  sin recargarla. Con `hx-boost` en `<body>`, todos los enlaces lo hacen: piden la página, htmx toma la
  zona central de la respuesta y la cambia por la anterior. El menú izquierdo no se toca y por eso no salta.
- **Una dirección, dos respuestas.** Si la pide htmx, el servidor manda solo la zona; si la pide el
  navegador, la página entera. Lo decide `base/contexto.py` mirando las cabeceras de htmx. Las páginas
  escriben `{% extends interfaz.plantilla %}` y no se enteran.
- **Herencia de plantillas con `block.super`.** `pagina.html` hereda de `zona.html` y pone la zona entera
  (`{{ block.super }}`) en medio de la cabecera y los menús. Así la zona se escribe una sola vez.
- **Procesador de contexto** (`base/contexto.py`). Es una función que Django llama en cada página para
  añadir datos comunes a todas las plantillas. Aquí da el menú, la sección actual, la ayuda y el título,
  sin consultar la base de datos.
- **Alpine.js.** Añade comportamiento con atributos en el HTML:
  - `x-data` crea un componente con sus datos;
  - `x-show` muestra u oculta;
  - `@click` reacciona a un clic;
  - `:class` cambia clases según los datos;
  - `$store` es un almacén compartido por toda la página.

  Los componentes comunes están en `base/static/base/interfaz.js`.
- **`localStorage`.** Es un pequeño almacén de cada navegador, que se conserva al recargar y al cerrar.
  Ahí se guardan el tema, la letra, la densidad y el estado del menú.
- **Evitar el destello del tema.** Si el tema se aplicara cuando ya se ha pintado la página, se vería un
  instante en claro. Por eso un script corto, dentro de `<head>`, lo aplica antes de pintar.
- **Variables de CSS** (`--color-marca`, `--spacing`). Cambiar una variable cambia todo lo que la usa.
  Así funcionan la densidad compacta, el color de marca y el modo oscuro.
- **La cabecera `Vary`.** Le dice al navegador que la misma dirección puede dar respuestas distintas
  según ciertas cabeceras. Sin ella, podría guardar la zona suelta y enseñarla sin menú.

## 6. Un error de cookies entre las dos versiones (12 de noviembre de 2026)

- **El síntoma.** `relation "django_session" does not exist` al abrir la portada, aunque la portada no
  usa la sesión.
- **La causa.**
  - El navegador guarda las cookies por nombre de servidor (`localhost`), sin mirar el puerto. La
    cookie `sessionid` de la versión 1 llegaba también a la versión 2.
  - La barra de depuración enseña la sesión en su pestaña «Request». Al leerla, Django buscó esa
    sesión en la tabla `django_session`, que aún no existe porque no se ha ejecutado `migrate`.
- **Cómo se encontró.** Primero se probó con una cookie inventada y no fallaba. Django descarta sin
  consultar la base las claves de sesión de menos de 8 caracteres. Con una clave de 32 caracteres, como
  las de verdad, el fallo apareció y la traza señaló a la barra de depuración.
- **La solución.** Las cookies de la versión 2 tienen nombre propio (`SESSION_COOKIE_NAME` y
  `CSRF_COOKIE_NAME` en `config/settings.py`). Así cada versión solo lee las suyas.

## 7. La tabla filtrable y el botón «copiar» (12 de noviembre de 2026)

- **Dos formas de filtrar, un solo componente** (`base/tablas.py`).
  - Con pocas filas (hasta 500), lo más rápido es mandarlas todas y que el navegador las oculte o las
    muestre mientras se escribe: no hay viaje al servidor.
  - Con muchas, mandarlas todas haría la página pesada, así que el servidor filtra y manda solo las
    primeras 100.
  - La clase `Tabla` decide sola el modo: pide 501 filas y mira si llega la 501.
- **El tanteo de «límite + 1».** Para saber si hay más de 500 filas no hace falta contarlas (`COUNT`):
  basta con pedir 501. Si llegan 501, hay más; si no, ya se tienen todas. Es una sola consulta.
- **Las fuentes.** `FuenteDeConsulta` (un QuerySet de la base de datos) y `FuenteDeLista` (filas en
  memoria) tienen los mismos métodos: `filtrar`, `ordenar`, `contar` y `cortar`. La tabla no sabe de
  dónde salen las filas.
- **Buscar sin tildes.**
  - En Python, `unicodedata.normalize("NFD", …)` separa la letra de su tilde («á» pasa a ser «a» más
    «´»), y luego se quitan las tildes sueltas.
  - En JavaScript, `normalize("NFD")` y `/\p{Diacritic}/gu` hacen lo mismo.
  - En PostgreSQL, la extensión `unaccent`, que se usa en Django con `campo__unaccent__icontains`.
- **htmx con retardo:** `hx-trigger="input changed delay:300ms"` espera a que dejes de escribir
  300 ms antes de pedir nada, así que no se hace una petición por cada letra.
- **Herencia de atributos de htmx.** `hx-target`, `hx-swap` o `hx-include` puestos en un elemento los
  heredan los de dentro. Por eso basta con ponerlos una vez en el bloque de la tabla.
- **`hx-vals` y `hx-include`.**
  - `hx-include="#tabla-x"` manda con la petición todos los campos de ese bloque: búsqueda, desplegables
    y orden.
  - `hx-vals` añade o sustituye valores: por ejemplo, el orden nuevo al pulsar una columna, o desde qué
    fila cargar con «Mostrar más».
- **`history.replaceState`.** Cambia la dirección del navegador sin recargar ni añadir un paso al botón
  «atrás». Lo usa el filtro del navegador para dejar los filtros en la dirección.
- **El pintor de formularios** (`FORM_RENDERER`). Desde Django 5 se puede decir con qué plantilla se
  pinta cada campo de todos los formularios (`field_template_name`) y, desde Django 5.2, qué clase
  representa cada campo (`bound_field_class`). Así todos los campos llevan su botón «copiar» y su
  explicación sin tocar ningún formulario.
- **El portapapeles.** `navigator.clipboard.writeText()` solo funciona en páginas seguras (https o
  `localhost`). Si falla, se usa el método antiguo: un cuadro de texto oculto, se selecciona y
  `document.execCommand("copy")`.

## 8. Un fallo que solo se ve en el navegador: `$el` y `$root` en Alpine (12 de noviembre de 2026)

- **El síntoma.** En la tabla de 200 filas, escribir en el buscador no filtraba nada, ni con tilde ni
  sin ella. Las pruebas pasaban.
- **Por qué las pruebas no lo vieron.** Comprobaban el HTML que manda el servidor y el código Python.
  El filtro de esa tabla es JavaScript que se ejecuta en el navegador, y ninguna prueba lo ejecutaba.
- **La causa.** En Alpine, `this.$el` es el elemento donde ha ocurrido la acción, no la raíz del
  componente.
  - Al cargar la página, `filtrar()` se ejecutaba desde la raíz (el bloque de la tabla) y funcionaba.
  - Al escribir, se ejecutaba desde el formulario, así que buscaba las filas dentro del formulario, no
    encontraba ninguna y no filtraba nada.
  - La solución es `this.$root`, que es siempre la raíz del componente.
- **Las tildes ya se quitaban.** `normalizar()` hace lo mismo en Python y en JavaScript. Lo que fallaba
  era que el filtro no llegaba a ejecutarse.
- **Playwright.** Abre la aplicación en un Chromium sin interfaz, escribe, pulsa y lee el resultado.
  Ahora hay pruebas así en `base/tests/test_navegador.py`. Para comprobar que de verdad detectan el
  fallo, se rompió el filtro a propósito, la prueba falló y después se restauró.
- **`StaticLiveServerTestCase`.** Arranca un servidor de verdad en un puerto libre, con los ficheros
  estáticos, para que el navegador de la prueba pueda abrir las páginas.
- **No perder el foco al filtrar en el servidor.** Si la respuesta sustituyera la cabecera, el cuadro en
  el que estás escribiendo se cambiaría por otro y perderías el cursor. Por eso, al filtrar solo se
  sustituyen las filas. El recuento, que está fuera de ellas, se actualiza con `hx-swap-oob="true"`:
  htmx coloca ese trozo de la respuesta en el elemento con el mismo `id`, esté donde esté.

## 9. Las cuentas de usuario: alias, sesión obligatoria y preferencias (12 de noviembre de 2026)

- **Un modelo de usuario propio.** El usuario de Django (`AbstractUser`) trae nombre, apellidos, correo y
  la hora exacta del alta: justo lo que la plataforma no debe saber. Por eso `usuarios.Usuario` parte de
  `AbstractBaseUser`, que solo pone la contraseña y el último inicio de sesión, y añade lo justo: alias,
  correo alternativo, superadmin, activo, el **día** de activación y las preferencias.
  - `AUTH_USER_MODEL = "usuarios.Usuario"` debe fijarse **antes de la primera `migrate`**: las tablas de
    Django (la trastienda, las sesiones) apuntan al modelo de usuario desde su primera migración, y
    cambiarlo después es muy difícil. Por eso no se ejecutó `migrate` hasta ahora.
  - El «gestor» (`GestorDeUsuarios`) es la clase que crea usuarios (`create_user`, `create_superuser`)
    y la que Django usa para buscarlos al iniciar sesión (`get_by_natural_key`).
- **Alias que no se pueden confundir.** Cada usuario guarda también su alias normalizado (sin tildes, en
  minúsculas y sin espacios de más), con una restricción única en la base de datos. Así «María» y
  «maria» no pueden convivir, y se puede entrar escribiendo «aguila» en la cuenta de «Águila».
  - Se guarda en una columna en lugar de usar `unaccent` en un índice porque PostgreSQL no deja usar
    `unaccent` en índices (no la considera «inmutable»).
- **Nada se ve sin sesión.** `LoginRequiredMiddleware` (Django 5.1+) exige sesión en todas las vistas,
  salvo las marcadas con `@login_not_required`. La nuestra (`usuarios/middleware.py`) añade dos cosas:
  - si la petición es de htmx, responde con la cabecera `HX-Redirect` para que htmx cargue la entrada
    como página entera (si no, la metería dentro de la zona central);
  - mira la marca `@login_not_required` antes de cargar el usuario, y así ahorra una consulta en las
    pantallas que no lo necesitan.
- **Sesiones en la caché.** Con `SESSION_ENGINE = "...cached_db"` la sesión se lee de Redis y solo se
  escribe también en la base de datos. Cada pantalla cuesta así una sola consulta por la sesión: la que
  carga el usuario.
- **Preferencias en la cuenta, sin destello.** El servidor escribe las preferencias en `<html>`
  (`data-tema="dia"`) al pintar la página, y el script de la cabecera solo rellena lo que falte con lo
  guardado en el navegador. Al cambiar una, `interfaz.js` la manda con `fetch` a
  `/cuenta/preferencias/guardar/`, con la clave CSRF que va en `<meta name="csrf-token">`.
- **CSRF con htmx.** Los formularios que envía htmx necesitan la clave contra falsificaciones. Va en
  `hx-headers` del `<body>`, y htmx la añade a cada petición.
- **Las pruebas inician sesión.** `PruebaDePantalla` entra como un usuario de prueba con
  `force_login`, y `base/pruebas_navegador.py` entra por la pantalla de entrada, como una persona.
  `base` crea ese usuario con `get_user_model()`, sin importar `usuarios`, para respetar las capas.

## 10. Grupos dentro de grupos: la tabla de cierre (12 de noviembre de 2026)

- **El problema.** Quien está en «GRU Henares» es también miembro de «GRU Jarama», que lo contiene, y
  de lo que contenga a Jarama. Con solo el campo `padre`, saber todos los grupos de alguien obliga a
  subir por el árbol consulta a consulta, y el número de consultas crecería con la profundidad.
- **La solución: una tabla con todos los pares.** `Contencion` guarda una fila por cada pareja
  «antecesor contiene a descendiente», con la distancia, incluido cada grupo consigo mismo
  (distancia 0). Para Jarama ⊃ Henares ⊃ Badiel hay 6 filas: las 3 de cada grupo consigo mismo, más
  Jarama-Henares (1), Henares-Badiel (1) y Jarama-Badiel (2). Con eso, «todos los grupos de Lince» es
  una sola consulta (`grupos_de`).
- **Mantenerla al mover un subárbol.** `Grupo.save()` lo hace solo:
  1. borra los pares que unen el subárbol (el grupo y sus subgrupos) con sus antiguos antecesores;
  2. añade los pares de cada antecesor del nuevo padre con cada grupo del subárbol, con una sola
     escritura (`bulk_create`).

  Los pares de dentro del subárbol no cambian.
- **`from_db`.** Django llama a este método al leer un objeto de la base. Ahí se apunta el padre con el
  que estaba guardado, para saber al guardarlo si ha cambiado.
- **Restricciones con condición.** «Una asamblea base por persona» es una restricción única solo sobre
  las filas con `es_base=True` (`UniqueConstraint(..., condition=Q(es_base=True))`). La comprueba
  PostgreSQL, y también `full_clean()` antes de guardar, con un mensaje propio.
- **Servicios.** Las operaciones (`admitir`, `invitar`…) están en `grupos/servicios.py`: comprueban,
  guardan y avisan con eventos_sw en una sola transacción. Así una pantalla, la API o una orden hacen
  exactamente lo mismo.

## 11. La trastienda: ordenarla y explicarla (12 de noviembre de 2026)

- **Un `AdminSite` propio.** El panel de Django es una clase (`AdminSite`). La nuestra
  (`config/trastienda.py`) cambia el título, añade una portada explicada y reagrupa las tablas por lo
  que significan con `get_app_list`, en lugar de por módulo. Se activa con una configuración
  (`config/apps.py`) que sustituye a `django.contrib.admin` en `INSTALLED_APPS`.
- **Ayuda en cada pantalla.** `base/trastienda.py` tiene `ConAyuda`, un añadido para cualquier
  `ModelAdmin`. Pasa el texto `ayuda` a dos plantillas que heredan de las de Django
  (`admin/change_list.html` y `admin/change_form.html`) y lo pintan encima.
- **Campos calculados de solo lectura.** Un método con `@admin.display` dentro del `ModelAdmin`, puesto
  en `readonly_fields`, sale en la ficha como un campo más: así se ven «todos sus grupos» o «miembros por
  sus subgrupos» sin guardarlos en ninguna tabla.
- **Ampliar la ficha de otro módulo sin romper las capas.** `usuarios` no puede conocer los grupos, así
  que `grupos/admin.py` toma la ficha de usuario ya registrada, la amplía con las pertenencias y la
  vuelve a registrar.
- **Modelo «proxy».** `AdminDeGrupo` no crea tabla: es otra forma de ver `Pertenencia`, con un gestor
  que solo devuelve las de rol admin. Sirve para tener en la trastienda una lista propia de «admins de
  grupo».
- **Dos trampas del orden en el panel.**
  1. `ModelAdmin.get_queryset()` ya ordena con `get_ordering()`. Si ese orden usa un campo calculado
     (`orden`), hay que añadir el campo antes de ordenar, así que la consulta se construye a mano.
  2. Django usa el `get_ordering()` de la lista de grupos también para los desplegables de grupos de
     otras fichas. Por eso a esos desplegables se les da su propia consulta (`ElegirGrupoConCamino`).
- **Ordenar texto «letra a letra».** PostgreSQL ordena según el idioma («intercalación»): ignora signos
  y espacios en la primera pasada, y así «GRU Duero › GRU Adaja» quedaba antes que «GRU Duero». Con
  `Collate(..., "C")` se compara carácter a carácter. Para que las tildes no estorben, la clave va antes
  sin tildes y en minúsculas.

## 12. Permisos: calcular una vez, preguntar sin coste (12 de noviembre de 2026)

- **La idea.** Saber si alguien puede hacer algo mirando sus grupos, roles y excepciones en cada
  pregunta costaría varias consultas cada vez. Por eso `permisos_de(usuario)` lo calcula todo de una vez
  (unas 7 consultas) y lo guarda en la caché como un mapa: `{grupo: {permisos}}`. Después,
  `puede(usuario, "grupos.invitar", grupo=g)` solo mira el mapa.
- **Versiones en la caché.** La clave lleva un número de versión (`permisos:12:v3`). Para invalidar el
  cálculo de todo el mundo no hace falta buscar y borrar claves: se sube la versión y las claves viejas
  dejan de usarse (y caducan solas).
- **`transaction.on_commit`.** La caché se borra cuando la transacción ha terminado bien. Si se borrara
  antes, otra petición podría recalcular con los datos viejos y guardarlos de nuevo. En las pruebas
  (`TestCase`), la transacción nunca termina; se usa `captureOnCommitCallbacks(execute=True)`.
- **Señales de Django.** `post_save` y `post_delete` avisan cada vez que se guarda o se borra una fila,
  venga de donde venga (también de la trastienda). Ojo: `bulk_create` y `update` no las lanzan.
- **`post_migrate`.** Django lanza esta señal después de cada `migrate` y también cuando las pruebas con
  servidor de verdad vacían la base. `sincronizar_permisos()` la escucha para que los roles del sistema y
  sus permisos por defecto estén siempre.
- **Evitar círculos entre módulos.** `permisos` usa las tablas de `grupos`, y `grupos` pregunta a
  `permisos` antes de invitar. Para que no se importen el uno al otro al arrancar, `grupos` importa
  `permisos` dentro de la función que lo usa, y busca la tabla de roles por su nombre
  (`apps.get_model("permisos", "Rol")`).
- **La caché en las pruebas.** En las pruebas la caché vive en la memoria del proceso y pasa de una
  prueba a otra, aunque la base de datos vuelva atrás. Por eso las pruebas que usan permisos empiezan
  con `cache.clear()`.
- **htmx y los errores.** Por defecto, htmx no pinta las respuestas 4xx y 5xx. Con `responseHandling` (en
  `htmx-config`) se le dice que la 403 sí la pinte, porque trae la explicación.

## 13. Ver la documentación dentro de la aplicación (13 de noviembre de 2026)

- **Markdown a HTML.** Python-Markdown convierte el texto con `#`, `**`, tablas, etc. en HTML. Sus
  extensiones añaden tablas (`tables`), bloques de código (`fenced_code`) y el índice (`toc`), que además
  pone un «ancla» (`id`) en cada título para poder enlazarlo.
- **Memoria con caducidad propia.** `@lru_cache` guarda el resultado de una función según sus
  parámetros. Al pasarle también la fecha de modificación del fichero, si el fichero cambia la clave es
  otra y se vuelve a convertir: el documento siempre está al día sin convertirlo en cada visita.
- **`mark_safe`.** Django escapa todo lo que se pinta en una plantilla (convierte `<` en `&lt;`). El
  HTML de los documentos es nuestro y de confianza, así que se marca como seguro para que se pinte tal
  cual. Nunca se hace con texto que escriban las personas.
- **Prestar una función a una capa inferior.** `base` pinta el menú, pero no puede importar `permisos`.
  `permisos`, al arrancar, le entrega su función de comprobar (`registrar_comprobador_de_permisos`). Así
  `base` no depende de nadie y, si no hubiera módulo de permisos, simplemente ocultaría las secciones que
  piden permiso.
- **Un enlace que no debe usar htmx.** La trastienda es otra aplicación con su propia página. Si htmx la
  pidiera, la metería dentro de la zona central. `hx-boost="false"` en el enlace hace que el navegador la
  cargue entera.
- **Los botones del panel de Django** salen de la etiqueta `{% submit_row %}`. Se sustituyen
  redefiniendo el bloque `submit_buttons_bottom` de `admin/change_form.html` en nuestra plantilla de
  ficha.

## 14. Audiencias: un número que dice quién ve cada cosa (13 de noviembre de 2026)

- **La idea.** En lugar de guardar en cada proyecto o evento la lista de quién lo ve, cada cosa guarda
  un solo número (`audiencia_id`). Por cada persona se calcula una vez qué audiencias ve, y las listas se
  filtran con `audiencia_id__in=...`, que PostgreSQL resuelve muy rápido con un índice.
- **Compartir filas iguales.** «Lo ven GRU Jarama y sus subgrupos» puede ser la audiencia de cien cosas.
  Si cada una creara su propia fila, la lista de audiencias de cada persona crecería sin fin. La
  «huella» («grupos:7») resume la composición, y es única: elegir lo mismo devuelve la misma fila
  (`get_or_create`).
- **«Sus subgrupos» con la tabla de cierre.** Una persona ve la audiencia de un grupo G si está en G o en
  algún subgrupo de G. Eso es lo mismo que decir que G es uno de «sus grupos» de `grupos_de` (los suyos y
  los que los contienen), así que basta con una consulta.
- **Subconsultas dentro de una consulta.** `Q(id__in=GrupoDeAudiencia.objects.filter(...).values(...))`
  no hace una consulta aparte: Django la mete dentro de la principal como `IN (SELECT ...)`.
- **Una regla que se comprueba en un solo sitio.** La de las organizaciones vive en `audiencias`, no en
  cada módulo que crea audiencias. Así ningún módulo nuevo puede olvidarla.

## 15. Importar desde una hoja de cálculo (13 de noviembre de 2026)

- **Qué es un .ods por dentro.** Un zip con varios ficheros. El primero se llama `mimetype`, va sin
  comprimir y dice qué tipo de documento es; `META-INF/manifest.xml` es el índice; `content.xml` tiene
  las hojas, filas y celdas en XML. Para no repetir filas vacías, el formato escribe una sola con
  `number-rows-repeated="500"`, y lo mismo con las celdas. Al leer hay que tenerlo en cuenta.
- **Desplegables en la plantilla.** Son «validaciones» (`table:content-validation`) con una lista de
  opciones. Cada celda que la usa lleva su nombre. LibreOffice muestra la lista al pulsar la celda.
- **Revisar antes de crear.** Primero se comprueba todo y se prepara un «plan» (lo que se va a crear),
  sin tocar la base. La persona ve la vista previa y confirma. Solo entonces se aplica el plan, dentro de
  una transacción: si algo falla a mitad, no queda nada a medias.
- **El plan en la sesión.** Entre las dos peticiones (revisar y confirmar), el plan se guarda en la
  sesión de quien importa. Las contraseñas van ya cifradas (`make_password`), nunca en claro: la sesión
  se guarda en Redis y en la base de datos.
- **Consultas que no crecen con las filas.** Al revisar, se cargan de una vez todos los grupos, roles,
  alias y pertenencias que nombra el fichero (unas pocas consultas) y después se trabaja en memoria. Las
  pruebas comprueban que con 3 filas o con 30 se hacen las mismas consultas.
- **Subir ficheros con htmx.** Con `enctype="multipart/form-data"` en el formulario, htmx envía el
  fichero igual que el navegador. Para la descarga de la plantilla se usa `hx-boost="false"`, porque es
  un fichero, no una página.

## 16. Dos bases de datos que no se hablan (13 de noviembre de 2026)

- **El enrutador.** Django pregunta a `config/enrutador.py` en qué base lee, escribe y crea cada tabla:
  las del módulo `boveda` van a la base «boveda»; las demás, a la de la plataforma. Así, en el código
  basta con `Persona.objects.all()`: no hay que decir la base cada vez.
- **`allow_relation`.** El enrutador también decide si dos filas pueden relacionarse con una clave
  ajena. Entre la bóveda y la plataforma, nunca. Si alguien lo intentara, Django daría error.
- **Migrar las dos bases.** `migrate` solo trabaja en una base cada vez. Con `--database=boveda` se
  crean las tablas de la bóveda en su base; el enrutador hace que en ella solo se creen esas.
- **Transacciones por base.** Una transacción es de una base: `transaction.atomic(using="boveda")`
  protege los cambios en la bóveda.
- **Huella con HMAC.** Un resumen normal (SHA-256) de un correo se podría adivinar probando correos. Con
  HMAC, el resumen se mezcla con una clave secreta que no está en la base: sin la clave, la huella no
  sirve para nada. Con la clave, el mismo correo da siempre la misma huella, y así se sabe si ya está
  registrado sin guardarlo.
- **Pruebas con dos bases.** Una prueba que usa la bóveda lo declara con `databases = {"default",
  "boveda"}`; si no, Django no la deja tocar esa base. `comprobar_consultas` suma las consultas de las
  dos bases.

## 17. Un selector con sugerencias: Alpine pide, Django responde en JSON (13 de noviembre de 2026)

- **Por qué JSON y no htmx.** htmx sustituye trozos de HTML; aquí el componente (Alpine) necesita los
  datos para decidir qué mostrar (quitar las ya elegidas, marcar las comunes). La vista devuelve
  `JsonResponse({"sugerencias": [...]})` y el componente las pinta con `x-for`.
- **`fetch` y `async`/`await`.** `await fetch(direccion)` espera la respuesta sin congelar la página;
  `@input.debounce.250ms` hace que solo se pregunte cuando se deja de escribir un momento.
- **Campos ocultos generados.** Cada palabra elegida pinta un `<input type="hidden" name="etiquetas">`.
  Al enviar el formulario llegan varios valores con el mismo nombre, y el campo los lee con
  `request.POST.getlist("etiquetas")` (`value_from_datadict`).
- **Un componente genérico en la capa de abajo.** El selector (`base`) no sabe nada de etiquetas: solo
  recibe la dirección de las sugerencias. Así lo puede usar cualquier módulo para cualquier lista de
  palabras.
- **Nadie ve lo de otra organización.** La vista de sugerencias solo usa la organización que le piden si
  quien escribe está en ella; si no, solo devuelve las comunes. La regla está en el servidor, no en el
  navegador, porque la dirección la puede escribir cualquiera.

## 18. Una sección para todos: cada cual ve lo suyo (13 de noviembre de 2026)

- **Una pantalla, distintas personas.** «Organizaciones y grupos» es la misma para el superadmin, los
  admins y cualquier miembro. La vista calcula una vez el **alcance** de quien mira (`grupos/acceso.py`:
  sus grupos y los que administra) y con eso filtra las listas y decide qué botones salen. La plantilla
  solo pinta lo que le llega.
- **Comprobar dos veces.** Ocultar un botón no basta: cualquiera puede mandar el formulario a mano. Por
  eso, al recibirlo, la vista vuelve a comprobar el permiso con `exigir()`, que responde con la pantalla
  403 y explica qué falta.
- **Permiso y límite.** Para la lista de miembros mandan dos cosas a la vez: el permiso del rol (que
  decide el superadmin) y un interruptor de la organización (que decide su admin). Se combinan con «y»:
  el admin de la organización puede cerrar, pero no abrir lo que el superadmin ha cerrado.
- **Un número en el menú que no se queda viejo.** El menú no se vuelve a pintar al navegar (para que no
  salte), así que «Invitaciones (1)» se quedaría en 1 después de aceptar. La solución de htmx es
  `hx-swap-oob` («fuera de banda»): la respuesta lleva, además de la zona central, un
  `<span id="contador-…" hx-swap-oob="true">(0)</span>`, y htmx lo pone en lugar del que tiene el mismo
  id, esté donde esté.
- **Caché con versión.** Contar invitaciones en cada página costaría una consulta. Se guarda el
  resultado en Redis con un número de versión en la clave; al cambiar una invitación se sube la versión
  y todas las claves viejas dejan de usarse solas. Se sube al **terminar** la transacción
  (`transaction.on_commit`): si se hiciera antes, otra petición podría guardar el número viejo. En las
  pruebas, `TestCase` nunca termina la transacción, así que se usa `captureOnCommitCallbacks(execute=True)`.

## 19. Formularios que no se pueden anidar: el atributo `form` (13 de noviembre de 2026)

- **El problema.** En «Configuración → Etiquetas», cada fila tiene sus formularios (cambiar, borrar) y,
  a la vez, una casilla para «Fusionar las marcadas». HTML no deja meter un formulario dentro de otro, así
  que no se puede envolver la tabla entera en el formulario de fusionar.
- **La solución.** Un campo puede pertenecer a un formulario que está en otro sitio de la página:
  `<input type="checkbox" name="etiquetas" form="fusionar">` se envía con `<form id="fusionar">`, aunque esté
  dentro de la tabla. htmx (que envía los formularios con `hx-boost`) lo respeta, porque recoge los campos
  del formulario con `form.elements`, que incluye estos. Se ha comprobado en Chromium
  (`etiquetas/tests/test_navegador.py`).
- **Enviar al cambiar un desplegable.** `onchange="this.form.requestSubmit()"` envía el formulario como si
  se pulsara su botón; con `requestSubmit` (y no `submit`) se lanza el evento que escucha htmx, así que la
  página no se recarga entera.

## 20. Avisar sin acoplar: cada módulo dice qué avisa y otro lo reparte (13 de noviembre de 2026)

- **El problema.** Muchos módulos querrán avisar a la gente («te han admitido», «hay un debate nuevo»), pero
  un módulo funcional no puede importar otro. Si `comunicaciones` tuviera que saber redactar cada aviso,
  conocería todos los módulos.
- **La solución: un contrato.** Cada módulo declara sus `TipoDeAviso` (cuándo, con qué eventos_sw, y una
  función que dice a quién y qué). `comunicaciones` solo dice «yo reparto» (`reparte_avisos`). El
  registro, al arrancar, une las dos cosas: por cada aviso añade una escucha que llama al repartidor con
  el código del aviso. Es el mismo truco que el menú: los módulos declaran, el registro conecta.
- **Más tarde, no ya.** El aviso se reparte desde la bandeja de salida, en otro proceso (el
  trabajador). Así, si repartir falla, el cambio que lo provocó no se deshace, y la pantalla no espera.
  Por eso la función que prepara el aviso vuelve a leer de la base lo que necesita: unos segundos después,
  puede que ya no exista.
- **Probar algo asíncrono.** En las pruebas no hay trabajador: se llama a mano a `procesar_bandeja()`
  después del cambio, y se mira la bandeja de la persona.
- **Confirmar antes de borrar.** «Limpiar las vistas» usa `onclick="return confirm(...)"`: si se pulsa
  «Cancelar», el formulario no se envía. En Playwright, las ventanas de confirmación se rechazan solas;
  para aceptarla, la prueba dice antes `pagina.once("dialog", lambda d: d.accept())`.

## 21. Pedir cada poco lo nuevo, con htmx (13 de noviembre de 2026)

- **Sondeo («polling»).** `hx-get="…?fragmento=mensajes" hx-trigger="every 10s"` hace que htmx pida la
  lista de mensajes cada 10 segundos y la sustituya. Es «casi» tiempo real sin servidor de websockets.
- **`hx-target="this"`.** La página entera tiene como destino por defecto la zona central (`#zona`); sin
  esto, la lista se metería en el sitio equivocado. Solo se sustituye la lista: lo que se está escribiendo
  en el formulario de respuesta no se pierde (lo comprueba `comunicaciones/tests/test_navegador.py`).
- **Guardar solo lo que se cambia.** Un objeto leído de la base puede quedarse viejo mientras otra
  persona cambia la fila. Si se guarda entero (o varios campos), se pisa lo que cambió la otra. Por eso
  `escribir()` actualiza solo su campo con `Conversacion.objects.filter(pk=…).update(…)`. Lo destapó la
  prueba de número de consultas: una conversación ya leída volvía a salir como «sin leer».

## 22. Una isla de JavaScript que se carga sola (13 de noviembre de 2026)

- **Por qué no en todas las páginas.** Leaflet pesa bastante y solo lo usa el mapa. El componente «mapa»
  (Alpine) pide sus ficheros la primera vez que aparece un mapa, uno detrás de otro (`await`), porque el
  complemento de agrupar necesita que Leaflet ya esté cargado. Una promesa por fichero evita pedirlo dos
  veces.
- **Por qué no `<script src>` en la plantilla.** Al navegar con htmx, la zona central se sustituye y los
  scripts nuevos se cargan sin orden garantizado. Dejar que el componente los cargue funciona igual al
  entrar de golpe que al llegar navegando (lo comprueba `lugares/tests/test_navegador.py`).
- **Datos sin riesgo.** Los puntos van en la página con `json_script` (Django los escapa) y la ventanita
  de cada chincheta se construye con `textContent`, no escribiendo HTML: un nombre con «<script>» se ve
  como texto.
- **`destroy()`.** Alpine lo llama al quitar el componente (al navegar a otra página): ahí se libera el
  mapa para no dejar memoria ocupada.

## 23. El calendario: una fuente por módulo, JSON para la isla y un .ics escrito a mano (13 de noviembre de 2026)

- **Juntar sin importar.** El calendario no sabe nada de eventos: cada módulo declara en su contrato una
  `FuenteDeCalendario` con la ruta de una función que recibe (persona, desde, hasta) y devuelve una lista
  de `FechaDeCalendario` (título, inicio, fin, enlace, tipo, color, si se puede arrastrar). `calendario`
  recorre las fuentes del registro y llama a cada función con `import_string`. Así un módulo funcional
  aporta al calendario sin que ninguno importe al otro.
- **La isla pide los datos.** FullCalendar no recibe las fechas en la página: cada vez que cambia de mes,
  semana o día llama a la función `events` del componente, que pide `/calendario/datos/?start=…&end=…`.
  Las últimas fechas se guardan; al tocar un filtro se vuelve a pintar sin pedir nada al servidor.
- **Arrastrar con red de seguridad.** Al soltar algo, la isla manda la fecha nueva a `/calendario/mover/`.
  Si el servidor dice que no (no es tuyo, está cancelado), `info.revert()` lo devuelve a su sitio y se
  muestra el porqué. La comprobación de verdad está en el servidor: la casilla `editable` solo evita
  que se intente.
- **Días enteros.** FullCalendar (y el formato .ics) dan como final de lo que ocupa días enteros el día
  *siguiente* al último. Aquí se guarda el último día, que es lo que entiende una persona; la conversión
  se hace solo al hablar con FullCalendar y al escribir el .ics.
- **El .ics es texto.** Una suscripción de calendario es un fichero de texto con bloques
  `BEGIN:VEVENT … END:VEVENT`. Dos detalles de la norma: las comas, los puntos y coma y los saltos de línea
  se escapan con `\`, y ninguna línea puede pasar de 75 *bytes* (una «ñ» ocupa 2): las largas se parten y
  la continuación empieza con un espacio.
- **Una vista sin sesión.** Los programas de calendario no inician sesión, así que la vista del .ics lleva
  `@login_not_required` y se protege con una clave secreta larga en la dirección. Por eso se puede
  cambiar: la anterior deja de funcionar al momento.

## 24. Series: tablas abstractas, la hora de aquí y «solo una vez al día» (13 de noviembre de 2026)

- **Una tabla abstracta.** `Evento` y `Serie` tienen casi los mismos campos. En lugar de copiarlos, se
  escriben una vez en `DatosDeEvento` con `class Meta: abstract = True`: esa tabla no existe en la base de
  datos, solo «presta» sus campos a las que heredan de ella. Así el formulario de la serie es el del
  evento con dos campos más (`FormularioDeSerie` hereda de `FormularioDeEvento`).
- **La hora de aquí.** «Todos los lunes a las 18:00» no es «cada 168 horas»: el último domingo de marzo el
  reloj se adelanta una hora. Por eso las fechas se calculan con el día y la hora de aquí (sin zona) y
  después se les pone la zona (`timezone.make_aware`), y no sumando horas a un momento ya con zona.
- **Cada vez es un evento propio.** Así cada una tiene su «¿Vas a ir?» y sus cometidos sin nada especial.
  La serie solo recuerda qué fecha le tocaba a cada vez (`en_la_serie`) y si alguien la cambió a mano
  (`tocado`): esas ya no se tocan al cambiar la serie.
- **Solo una vez al día, aunque haya dos trabajadores.** `cache.add(clave, valor)` solo guarda si la clave
  no existía, y en Redis eso es atómico: si dos procesos lo intentan a la vez, solo uno gana. Con una clave
  por día («tareas_diarias:2026-11-13») basta para que las tareas diarias se ejecuten una sola vez.

## 25. Árboles de profundidad libre y arrastrar en las pruebas (13 de noviembre de 2026)

- **Padre y raíz.** Un proyecto guarda su padre (para saber dónde va) y la raíz de su árbol. Con la raíz,
  una sola consulta trae el árbol entero (`raiz_id = …`), y el resto (antecesores, subárbol, sangrado)
  se calcula en Python con un diccionario. Para los grupos se usó otra técnica, la tabla de cierre
  (`Contencion`), porque se consultan muchísimo y desde todas partes; aquí basta con algo más sencillo.
- **Pintar un árbol en una lista.** `en_arbol()` recorre el árbol en profundidad y devuelve cada proyecto
  con su nivel; la plantilla solo sangra según el nivel. Así la plantilla no necesita recursión.
- **Arrastrar en Playwright.** SortableJS con `forceFallback` sigue el ratón «a mano», y `drag_to` salta
  de golpe al destino: no se entera. En la prueba se mueve el ratón en 20 pasos (`arrastrar()` de
  `proyectos/tests/test_navegador.py`).

## 26. Limpiar sin que un módulo conozca a los demás (13 de noviembre de 2026)

- **El módulo dice qué está terminado; la limpieza decide cuándo.** Cada módulo declara sus `Limpiable`
  con una función `terminados(antes)` que devuelve una consulta (un QuerySet sin ejecutar). `limpieza` la
  llama con «ahora menos los días del plazo», le pide `pk`, `titulo` y `audiencia_id` con `values_list` y
  le pone la fecha con un `update`: dos consultas por tipo, sin importar ningún módulo funcional.
- **Dos copias pequeñas en lugar de preguntar.** La tabla `Archivado` guarda el título, el enlace y la
  audiencia de lo archivado. Así el archivo se lista con una consulta (filtrada con `filtrar_visibles`,
  como todo) aunque mezcle proyectos, eventos y recordatorios.
- **Guardar a la vez lo que va junto.** Proyecto y Tarea apuntan cuándo terminaron en su `save()`: así da
  igual desde dónde cambie el estado (el formulario, el kanban, el calendario). Si el `save()` recibe
  `update_fields`, hay que añadirle esos campos, o no se guardarían.
- **Pruebas con el reloj en la mano.** `limpiar(ahora)` recibe el momento: las pruebas «viajan» 16 días al
  futuro sin esperar ni trucar el reloj del sistema.

## 27. Dependencias: un grafo pequeño y una regla que se aplica sola (13 de noviembre de 2026)

- **Una relación de una tabla consigo misma.** `Tarea.espera_a` es un `ManyToManyField("self",
  symmetrical=False)`: «A espera a B» no implica que «B espera a A». Por el otro lado, `related_name=
  "desbloquea"` da las tareas que esperan a una.
- **Buscar círculos sin recursión en la base de datos.** Antes de guardar, se cargan todas las esperas
  del árbol con una consulta (la tabla intermedia, `Tarea.espera_a.through`) y se recorren en Python
  desde las tareas elegidas: si se llega a la tarea que se edita, habría un círculo.
- **Una sola función que pone al día.** `poner_al_dia(tareas)` decide el estado según las esperas, y la
  llaman todos los sitios donde algo cambia (mover, editar, crear, borrar). Así la regla vive en un solo
  sitio. El campo `bloqueo_automatico` distingue lo que bloqueó la aplicación (que también desbloquea)
  de lo que bloqueó una persona (que se respeta).
- **La isla se entera de los cambios ajenos.** Cuando mover una tarjeta cambia otras, el servidor lo dice
  en la respuesta (`"otras": 1`) y la isla recarga el tablero, en lugar de intentar recolocar tarjetas.

## 28. Reutilizar en lugar de repetir (13 de noviembre de 2026)

- **Etiquetas en un módulo nuevo, sin código nuevo de etiquetas.** `proyectos` usa el campo común
  `CampoDeEtiquetas` en su formulario y `etiquetar()` al guardar, con su ancla `proyectos.proyecto`. Para
  la lista, una sola consulta trae las etiquetas de todos los proyectos (`etiquetas_de_varios`) y se
  cuelgan de cada objeto antes de pintar: así no hay una consulta por fila.
- **Herencia igual que los campos.** `tareas_modelo_de()` sigue la misma receta que `campos_de()`: la
  cadena de la tipología da el nivel de cada una y se ordena por (nivel, orden). Una receta conocida es
  más fácil de leer que una nueva.
- **Las tareas modelo se apoyan en las dependencias.** «Espera a la anterior» no necesita nada propio:
  al crear las tareas se pasa `espera_a=[la anterior]` y la regla de bloqueo hace el resto.

## 29. Diagramas que viven en el texto (13 de noviembre de 2026)

- **Mermaid** dibuja un diagrama a partir de unas líneas de texto (`A --> B`). Al estar dentro del
  Markdown, el diagrama se cambia como cualquier otro texto y queda en git con su historia: no hay un
  dibujo aparte que se quede viejo.
- **El servidor no dibuja nada.** Python-Markdown deja cada bloque como `<pre><code class="language-mermaid">`
  y la isla «documento» (Alpine) los busca, carga Mermaid solo si hay alguno (`cargarUnaVez`) y cambia cada
  bloque por su SVG. Con `securityLevel: "strict"` el texto no puede meter HTML ni código.
- **Dibujar solo lo que se va a ver.** Un `IntersectionObserver` avisa cuando un bloque se acerca a la
  vista y solo entonces se dibuja, uno detrás de otro (una promesa en cola). Ojo: en esta aplicación no
  se desplaza la ventana sino `#desplazable`, así que hay que dárselo como `root`; si no, el vigilante
  nunca ve entrar nada. Y no se guarda el vigilante en el estado de Alpine: lo envolvería en un proxy.
- **Acercar y mover** un SVG lo hace svg-pan-zoom: envuelve el dibujo en un grupo y le cambia la
  transformación (`transform="matrix(…)"`). La prueba en el navegador comprueba justo eso.
- **Ver una entrada del menú sin el permiso.** `EntradaDeMenu.tambien_si` apunta a una función que
  recibe el usuario: si dice que sí, la entrada se ve aunque falte el permiso. Así las guías se abren a
  todo el mundo en desarrollo sin tocar los permisos de nadie.

## 30. Un menú que se ordena en un solo sitio y un panel que no se vuelve a pintar (14 de noviembre de 2026)

- **Datos en lugar de números.** Antes cada módulo decía `orden=850` y `dentro_de="tipologias.configuracion"`:
  para mover algo había que buscar en veinte ficheros y encontrar un número libre. Ahora `config/menu.py`
  es una tupla de códigos que dibuja el árbol del menú tal cual se ve. El registro la recorre con una
  función que se llama a sí misma para cada nivel (`_colocar`) y, como las fichas son inmutables
  (`frozen=True`), crea copias con sus subsecciones nuevas (`dataclasses.replace`). Lo que no cuadra
  (una entrada sin colocar, un código que no existe) se apunta como error y lo enseña `manage.py check`.
- **Lo que está fuera de la zona no se toca.** htmx solo sustituye `#zona`; el menú izquierdo y el panel
  de ayuda están fuera, así que siguen igual al navegar. Para llenar el panel se usa `htmx.ajax("GET",
  direccion, { target, swap: "innerHTML" })`: htmx manda la cabecera `HX-Target` con el id del destino y
  el servidor (`base/contexto.py`) elige con ella qué marco pintar (`zona.html` o `panel.html`). Las
  vistas no se enteran: heredan de `interfaz.plantilla`.
- **Escuchar «en captura».** Un clic baja primero desde `<html>` hasta el enlace (fase de captura) y luego
  sube (burbuja). Con `@click.capture` el panel ve el clic antes que el propio enlace, que es donde htmx
  escucha; si es una página de la ayuda, `preventDefault()` y `stopPropagation()` lo frenan y el panel la
  abre él mismo. Si no, lo deja pasar y htmx lo lleva a la zona principal.
- **Arrastrar con eventos de puntero.** `pointerdown`, `pointermove` y `pointerup` sirven igual para
  ratón, dedo y lápiz. `setPointerCapture` hace que la línea siga recibiendo los movimientos aunque el
  puntero se salga de ella (lo normal al arrastrar deprisa). El ancho es una variable de CSS
  (`--ancho-del-panel`) en `<html>`, y la clase `md:w-(--ancho-del-panel)` la usa.
- **Que no salte al recargar.** El script de la cabecera lee del navegador si el panel estaba abierto y su
  ancho, y lo pone en `<html>` antes de pintar nada (`data-panel-de-ayuda` y la variable). Tailwind tiene
  una variante propia, `panel-abierto:`, que se activa con ese atributo (igual que `plegado:` con el
  menú).
- **Tamaño según la caja, no según la pantalla.** `lg:` mira el ancho de la ventana; `@3xl:` (consultas de
  contenedor) mira el de la caja con clase `@container`. Así el mismo documento pone el índice al lado en
  la zona ancha y encima en el panel estrecho, sin plantillas distintas.
- **Esperar a htmx.** Los scripts con `defer` se ejecutan en orden, pero Alpine arranca en cuanto se
  ejecuta el suyo, antes que htmx. Si un componente necesita htmx al arrancar, espera a
  `DOMContentLoaded` (`htmxListo()`).
- **Markdown deja pasar el HTML.** Un «`<script>`» escrito fuera de las comillas de código llegaba a la
  página como etiqueta de verdad. Se quitan las dos piezas de Python-Markdown que lo permiten
  (`html_block` y `html`) y entonces se escapa: `&lt;script&gt;`.
- **Agrandar solo una parte de la pantalla.** Las clases de Tailwind miden en `rem` (la letra de `<html>`),
  así que cambiar la letra de una caja no las agranda. `zoom` de CSS sí: agranda todo lo de dentro y
  vuelve a repartir las líneas en el ancho que hay. Pero si algo dentro es más ancho que la caja (un
  código largo sin espacios, una rejilla que crece con su contenido), se sale de lado: se arregla en su
  origen (`grid-cols-[minmax(0,1fr)]`, `overflow-wrap: anywhere`), no compensando el ancho del zoom.
- **Un filtro con argumento no perdona.** `{{ a|default:b.c }}` falla si `b` es `None` (el argumento de
  un filtro no se resuelve «en silencio» como una variable suelta), y la página salía con la zona vacía.
  `{% firstof a b.c "Asambleas" %}` hace lo mismo sin fallar.

## 31. Elegir personas: cercanía con la tabla de cierre y no dar pistas (14 de noviembre de 2026)

- **La tabla de cierre responde «¿qué tan lejos?» con una consulta.** `Contencion` guarda cada pareja
  antecesor–descendiente con su distancia. Para saber a qué distancia está el grupo de una persona del grupo
  de referencia, basta con mirar qué grupos de encima del de referencia (también él mismo) lo contienen:
  si lo contiene el propio grupo, es un subgrupo; si no, manda el antecesor común más bajo. Todo con tres
  consultas (los de encima, las pertenencias y sus contenedores), sean 10 personas o 1000
  (`audiencias/cercania.py`).
- **Pedir la lista solo al abrirla.** La ventana pide la lista en JSON (`fetch`) la primera vez que se abre,
  y otra vez solo si cambia lo que la condiciona (la visibilidad elegida). Abrir el formulario no cuesta
  nada de más.
- **Filtrar en el navegador.** Con la lista ya en la página, el buscador no hace peticiones: `normalizar()`
  quita tildes y mayúsculas y cada palabra escrita tiene que aparecer en el alias, el grupo o la marca.
- **El mismo error para todo.** Si al escribir un alias que no ves la respuesta fuera «no existe» unas
  veces y «no ve esto» otras, cualquiera podría averiguar qué alias existen en otras organizaciones. Por eso
  el mensaje es siempre el mismo: «No está entre quienes ven esto».
- **Comprobar solo al guardar.** El campo recibe una **función** (`permitidas`) en lugar de la lista de ids:
  así solo se calcula si se envía el formulario, no cada vez que se pinta.
- **Las clases de Tailwind, en la plantilla.** Tailwind solo genera las clases que encuentra en las
  plantillas. Para elegir el color por nivel desde Alpine se escribe la lista de clases en la propia
  plantilla (`:class="['border-marca bg-marca/10', …][nivel]"`), no en `interfaz.js`, que Tailwind no lee.

## 32. Una portada que junta módulos sin importarlos (14 de noviembre de 2026)

- **El problema.** «Inicio → Panel» enseña comunicaciones, solicitudes y proyectos, pero la pantalla vive en
  `base`, la capa de abajo, que no puede importar módulos de más arriba (la regla de dependencias lo
  prohíbe y la prueba `base/tests/test_dependencias.py` falla si alguien lo hace).
- **La solución: que cada módulo traiga lo suyo.** Igual que las fuentes del calendario, cada módulo
  declara en su contrato una `TarjetaDeInicio` con la **ruta de una función como texto**
  (`"solicitudes.inicio.pendientes"`). `base/inicio.py` la carga con `import_string` (una función de Django
  que convierte el texto «paquete.modulo.funcion» en la función de verdad) y la llama. `base` nunca escribe
  `import solicitudes`.

  *Ejemplo: cuando exista «debates», bastará con que declare su tarjeta «Debates abiertos» y la coloque en
  `config/inicio.py`; la pantalla de Inicio no cambia.*
- **Datos, no HTML.** La función devuelve datos (`ResumenDeTarjeta` → `ApartadoDeTarjeta` → `FilaDeResumen`:
  texto, enlace, detalle, fecha) y una sola plantilla, `base/portada.html`, los pinta todos igual. Si una
  tarjeta necesita un dibujo propio (el árbol de grupos), da su plantilla y `base` la pinta con
  `render_to_string` (la función de Django que convierte una plantilla y sus datos en texto HTML).
- **El orden, en un solo sitio.** `config/inicio.py` dice qué tarjeta va en qué fila, como `config/menu.py`
  con el menú. Y `python manage.py check` (la orden de Django que revisa el proyecto antes de arrancar) avisa
  si una tarjeta está sin colocar o colocada dos veces.
- **No contar dos veces.** Los totales de lo recibido («Recibidas (3)») son los mismos números que salen en
  el menú, y el menú ya los ha guardado en la caché (Redis) al pintar la página: la tarjeta los pide a la
  misma función y no cuestan consultas.
- **Subconsultas en lugar de dos viajes.** Para «las solicitudes de mis grupos», en vez de pedir primero
  mis grupos y luego las solicitudes, se escribe `grupo_id__in=Contencion.objects.filter(...).values(...)`:
  Django lo convierte en una sola consulta con una subconsulta dentro.

## 33. Cambiar un dato sin recargar la página: htmx y un trozo de plantilla (14 de noviembre de 2026)

- **La idea.** En la ficha de una tarea, cada dato ya escrito es un pequeño formulario escondido. Alpine
  (`x-data="{ editando: false }"`) solo decide si se ve el dato o su cuadro. Al guardar, **htmx** manda ese
  formulario al servidor (`hx-post`) y sustituye el trozo de la página por lo que el servidor devuelve
  (`hx-target` y `hx-swap="outerHTML"`): el mismo trozo, ya con el valor nuevo.

  *Ejemplo: Nutria pulsa «Pendiente», elige «En curso» y pulsa Intro; solo cambia esa línea de la ficha.*
- **Una sola plantilla para pintar y para responder.** `proyectos/_campo_de_tarea.html` la incluye la ficha
  al pintarse y la devuelve la vista `tarea_campo` al guardar. Así el dato se ve siempre igual, antes y
  después de cambiarlo.
- **Los errores también vuelven en el trozo.** Si el valor no vale (un título vacío), la vista devuelve el
  trozo abierto y con el error, para corregirlo ahí mismo.
- **Las mismas reglas que el formulario grande.** La vista valida el dato con el campo del propio
  formulario (`FormularioDeTarea.base_fields[campo].clean(...)`, que es lo que Django hace por dentro con
  cada campo) y lo guarda con el mismo servicio, `editar_tarea`. No hay dos maneras de guardar una tarea.
- **`form.reset()`** devuelve cada cuadro de un formulario a su valor de partida: es lo que hace
  «Cancelar».

## 34. Colgar cosas de otras sin importarlas, y el voto secreto (15 de noviembre de 2026)

- **Anclas: «tipo + número».** Un debate que cuelga de una reunión guarda `ancla_tipo = "eventos.evento"` y
  `ancla_id = 12`, no una clave ajena a la tabla de eventos (eso obligaría a importar el módulo).
  `base/anclas.py` encuentra el elemento con `apps.get_model` (la función de Django que da un modelo por su
  nombre, «eventos.Evento», sin importarlo), y de él se toman su grupo y su audiencia.

  *Ejemplo: Lince pulsa «+ Debate» en la ficha de la asamblea; el debate nace con el grupo y la
  visibilidad de la asamblea, sin que Lince tenga que elegirlos.*
- **El recuadro «Cuelga de aquí».** Cada módulo declara un `Colgante` en su contrato y la ficha solo
  escribe `{% colgantes "eventos.evento" evento.pk %}`: una **etiqueta de plantilla** propia (código Python
  que se llama desde una plantilla de Django con `{% … %}`; se carga con `{% load colgantes %}`).
- **Avisarse sin importarse.** Al aprobar un acta, `documentos` emite `documentos.acuerdo_tomado` con todos
  los datos de la decisión; `decisiones` lo escucha y la apunta. Ninguno sabe que el otro existe; los une el
  registro.
- **Votar en secreto.** Se guardan dos cosas por separado: que Nutria ha votado (para que no vote dos veces)
  y una papeleta sin nombre ni hora con lo que votó. Si se permite cambiar el voto, la papeleta lleva una
  **clave HMAC** (un resumen que solo se puede calcular conociendo un secreto, `hmac` de la biblioteca de
  Python) del par consulta-persona: así se encuentra su papeleta para sustituirla sin guardar su nombre en
  ella.
- **Markdown seguro.** Lo que escriben las personas se convierte con Python-Markdown quitando el HTML y
  revisando cada enlace: un `[pulsa](javascript:…)` acabaría ejecutando código en el navegador de quien lo
  pulse (ataque XSS), así que se cambia por `#`.
- **Quién escribió cada párrafo.** `difflib` (biblioteca de Python que compara listas, la de las
  herramientas de diferencias) compara los párrafos de antes y de después y dice cuáles son iguales,
  cuáles cambian, cuáles se añaden y cuáles se quitan.

## 35. Escribir a la vez: Yjs, un servidor aparte y pases firmados (15 de noviembre de 2026)

- **El problema.** Si dos personas escriben a la vez y cada una guarda su texto entero, la segunda pisa a
  la primera. Hace falta unir los cambios letra a letra.
- **Yjs** es una librería de JavaScript que guarda el texto como una lista de letras, cada una con quién y
  cuándo la puso. Dos cambios hechos a la vez se unen siempre igual, en cualquier orden (es un **CRDT**:
  «tipo de dato que se replica sin conflictos»). **Hocuspocus** es el servidor que reparte esos cambios
  por **WebSocket** (una conexión que queda abierta y por la que el servidor puede mandar cosas sin que
  se las pidan).

  *Ejemplo: Lince escribe «Regar los martes.» y Nutria, a la vez, «Y los jueves.»; las dos ven las dos
  frases en menos de un segundo.*
- **Una pieza aparte.** El editor (carpeta `editor/`, en Node) no sabe nada de asambleas. Para que lo use
  otra aplicación basta con darla de alta con un nombre, un secreto y una dirección.
- **Pases firmados (JWT).** Un JWT es un texto en tres trozos separados por puntos:
  - la cabecera;
  - los datos (alias, sala, permiso, caducidad), en base64;
  - una **firma HMAC** de los dos anteriores con un secreto.

  El editor recalcula la firma con el mismo secreto. Si coincide, sabe que el pase lo hizo la plataforma y
  que nadie ha cambiado el permiso. No tiene que preguntar a nadie.
- **Firmar también entre servidores.** Cuando el editor llama a la plataforma («dame el texto», «esto es lo
  escrito»), firma el cuerpo y la hora. La hora sirve para que una petición copiada no se pueda repetir más
  tarde.
- **Quién manda.** La plataforma decide los permisos y guarda el texto bueno. El editor solo une los
  cambios y los reparte. Si el editor se cae, la plataforma sigue teniendo lo último guardado.
- **Un contrato más.** `documentos` declara un `TextoEditable` con tres funciones (qué puede hacer cada
  persona, el texto inicial, guardar). `base` hace de puente, así que mañana un proyecto puede tener su
  propia documentación en tiempo real sin tocar el editor.

## 36. Límites en cascada, compilar sin bloquear y comentarios anclados (15 de noviembre de 2026)

- **Límites en cascada.** Cada nivel guarda solo lo suyo:
  - la plataforma, en una fila sin dueño;
  - una organización, en una fila con su organización;
  - un grupo, en una fila con su grupo;
  - un debate, en una fila con su debate.

  Para saber lo que vale, se leen todas las filas que tocan en una consulta y se toma el **mínimo** de cada
  campo (`base/limites.py`). Los grupos de arriba se encuentran con la **tabla de cierre** (`Contencion`:
  una fila por cada par antecesor-descendiente, a cualquier distancia), sin recorrer el árbol.

  *Ejemplo: la organización pone 400 palabras, GRU Tajo 300 y el debate 200: valen 200.*
- **Una restricción única con vacíos.** Para que no haya dos filas del mismo nivel,
  `UniqueConstraint(..., nulls_distinct=False)` trata los vacíos como iguales. Así solo puede haber una fila
  «de la plataforma».
- **Compilar sin bloquear.** Node atiende a todo el mundo con un solo hilo. Una compilación larga lo
  pararía, así que Typst va en un **hilo de trabajo** (`worker_threads`) con un reloj: si tarda demasiado,
  se mata y se crea otro.
- **Comentarios que no se mueven.** Un comentario no guarda «de la letra 120 a la 130», que cambia al
  escribir delante. Guarda una **posición relativa** de Yjs: «justo después de esta letra concreta». Yjs la
  traduce al número de ahora cada vez que se pinta.
- **Una urna para que el voto sea secreto de verdad.** Cuando dos filas se crean en la misma operación de
  la base de datos, quedan unidas aunque no compartan ninguna columna: tienen el mismo número de
  transacción, números seguidos y están juntas en el disco. Por eso la papeleta espera en una lista de
  Redis y se guarda junto a otras cuatro o más, en desorden y con un número al azar (`uuid4`).

## 37. Cifrar con un sello, saber quién es sin saber quién es, y ficheros que no existen (15 de noviembre de 2026)

- **Cifrar y sellar a la vez (AES-256-GCM).** Cifrar esconde lo que hay; no impide que alguien cambie bytes
  a ciegas. GCM añade un **sello** (16 bytes) que se calcula con la clave: al descifrar, si un solo byte
  no cuadra, da error. Cada fichero lleva además su número al azar (*iv*), para que dos textos iguales no
  se parezcan cifrados, y un «para qué» sellado (`indice`, `imagen:<número>`): así no se puede cambiar un
  fichero cifrado por otro (`editor/src/cifrado.mjs`).
- **La clave importa más que el candado.** Quien tiene la clave lo lee todo; quien la pierde, lo pierde
  todo. Por eso va en una variable de entorno, fuera del código y de los datos, y hay que guardarla aparte.
- **Un número que identifica sin delatar.** El editor tiene que saber que «esto es de la misma persona que
  ayer», pero no quién es. La plataforma le da `HMAC(secreto, "usuario:12")`: siempre sale lo mismo para la
  misma persona y, sin el secreto, no se puede volver al 12 (`base/editor.py`, `id_para_editor`).
- **Ámbitos en vez de grupos.** El editor no sabe qué es una organización ni un grupo: solo recibe
  «ámbitos» con un nombre y si los administras. Cada aplicación decide qué es un ámbito. Así el mismo
  editor sirve a otras herramientas (`editor/src/biblioteca.mjs`).
- **Mirar los primeros bytes, no el nombre.** Un fichero se puede llamar `foto.png` y ser otra cosa. Los
  formatos de imagen empiezan siempre igual (PNG por `89 50 4E 47`, JPEG por `FF D8 FF`, GIF por `GIF8`), y
  eso es lo que se mira. El SVG no se admite: es texto y puede llevar código.
- **Ficheros que no existen (sombras).** El compilador de Typst solo ve una carpeta vacía. Para que pueda
  poner una imagen, se le da en memoria con `mapShadow(ruta, bytes)`: la ve como si estuviera en el disco,
  pero nunca se escribe. Antes de cada compilación se borran todas (`resetShadow`), y solo se le dan las
  imágenes que ve quien compila.
- **Lo elegido vive con el texto.** La plantilla y la cabecera y pie de un documento van en un mapa de Yjs
  dentro de la propia sala. Así se reparten a todo el mundo como cualquier cambio del texto, y solo los
  cambia quien puede escribir, sin código de más.

## 38. Controles dentro de una tabla, capas por petición y plazos que solo bajan (15 de noviembre de 2026)

- **Un formulario no puede ir dentro de otro.** La tabla filtrable ya tiene su formulario (el buscador). Para
  poner casillas y botones en sus filas, cada control lleva `form="miembros-acciones"`: pertenece a ese
  formulario aunque esté en otro sitio de la página. El botón pulsado manda su `name` y su `value`
  («accion=sacar:12»), y así un solo formulario sirve para todas las filas y para «Aplicar a las marcadas».
- **Celdas con plantilla propia.** `Columna(..., plantilla="…html")` pinta la celda con esa plantilla y le
  pasa la fila entera; el texto de la celda se sigue usando para buscar, filtrar y ordenar.
- **Una capa (middleware) que pasa por cada petición.** `ApuntarActividad` mira si hoy ya consta el día de
  la persona; si no, lo apunta con un `update` (sin `save`, que tocaría todos los campos). Así cuesta una
  consulta al día por persona, no una por página.
- **Un plazo que solo se puede bajar.** Cada nivel guarda su número y se toma el menor; después se aplica el
  mínimo: `max(min(candidatos), minimo)`. El formulario comprueba además que nadie suba por encima del de la
  plataforma.


## 39. Contar lo no leído sin una consulta por fila, y parejas sin repetir (15 de noviembre de 2026)

- **Subconsultas dentro de la consulta (`Subquery` y `OuterRef`).** En «Con grupos» cada grupo enseña
  cuántos mensajes nuevos tiene. En vez de preguntar grupo a grupo, la consulta de los grupos lleva dentro
  otra pequeña: «cuenta los mensajes de *este* grupo (`OuterRef("pk")`) con número mayor que el último que
  leí». PostgreSQL la resuelve para cada fila en una sola ida y vuelta.
- **Leer hasta un número, no mensaje a mensaje.** Para saber qué es nuevo en una sala basta con guardar el
  número del último mensaje visto (`LecturaDeSala.ultimo_leido`): todo lo que tenga un número mayor es
  nuevo. Una fila por persona y sala, haya los mensajes que haya.
- **Una pareja, una fila.** Una conversación entre Lince y Nutria es la misma que entre Nutria y Lince. Se
  guarda siempre con el número más bajo primero, y la base lo exige con una restricción (`CheckConstraint`
  `primera < segunda`) y otra de unicidad: así nunca hay dos conversaciones de la misma pareja.
- **Números del menú en la caché, con versión.** Cada mensaje en una sala sube un número de «versión» en
  Redis; la clave de cada recuento lleva esa versión, así que los recuentos viejos dejan de usarse solos sin
  tener que buscarlos uno a uno para borrarlos.

## 40. Subir archivos sin fiarse del nombre, hablar con un antivirus y una papelera (15 de noviembre de 2026)

- **La extensión no basta.** Cualquiera puede llamar «informe.pdf» a un programa. Cada formato empieza con
  unos bytes fijos, su «firma»: un PDF empieza por `%PDF-`, un PNG por `\x89PNG`. Un documento abierto
  (odt, ods) es un zip cuyo primer fichero, `mimetype`, dice qué es. `documentos/archivos.py` lo comprueba.
- **Hablar con un servicio por su protocolo.** ClamAV escucha en un puerto; se le manda `zINSTREAM\0` y
  después el archivo en trozos, cada uno precedido de su tamaño en 4 bytes (`struct.pack("!L", n)`), y un
  trozo de tamaño 0 para acabar. Responde «stream: OK» o «… FOUND». Son 15 líneas con `socket`, sin
  librerías. En las pruebas, un servidor de mentira (`socketserver`) hace de ClamAV.
- **Ficheros privados.** Se guardan con un nombre al azar (`uuid4`) en una carpeta que no se sirve sola;
  una vista mira quién ve el documento y entrega el fichero con `FileResponse`, avisando al navegador con
  `nosniff` para que no lo interprete como otra cosa.
- **Borrar sin borrar (papelera).** Eliminar solo pone una fecha (`en_papelera_desde`); las listas
  esconden lo que la tiene. La limpieza diaria borra de verdad lo que lleva más de 30 días, y después sus
  ficheros del disco.
- **Preguntar a otro módulo sin importarlo.** Que una consulta abierta congele sus documentos lo dice la
  propia consulta en su contrato (`Ancla(..., congela="consultas.servicios.congela")`); `documentos` busca
  esa función en el registro con `import_string`. Igual para las tareas de un proyecto (`dentro`).

## 41. Páginas sin sesión, una foto de lo publicado y una barra de camino (15 de noviembre de 2026)

- **Abrir una puerta a propósito.** Toda la aplicación exige sesión (`LoginRequiredMiddleware`); las vistas de
  la portada llevan `@login_not_required`, y nada más. Así lo público es una lista corta y a la vista.
- **Borrador y foto publicada.** La página guarda dos cosas: el borrador (Markdown, que cambia mientras se
  escribe) y la foto publicada (el HTML seguro de ese momento). Lo que ve la gente es la foto; por eso se
  puede seguir escribiendo sin que cambie nada hasta volver a pulsar «Publicar».
- **Quién ve de arriba abajo.** La tabla de cierre (`Contencion`) guarda cada pareja antecesor-descendiente.
  Los grupos «de encima» de los míos son justo los que me tocan: si estoy en GRU Sorbe, veo las webs de GRU
  Sorbe, GRU Henares, GRU Jarama y GRU Tajo. Con una consulta (`grupos_de`) se sabe todo.
- **Desplegables sin JavaScript.** `<details>` y `<summary>` son HTML normal: se abren y se cierran solos.
- **Un botón en la cabecera sin que la cabecera lo conozca.** El módulo lo declara en su contrato
  (`EnlaceDeCabecera`) y la plantilla general pinta lo que haya en el registro, como el menú.

