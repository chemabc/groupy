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
