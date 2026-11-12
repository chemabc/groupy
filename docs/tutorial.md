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
