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
