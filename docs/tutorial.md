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
