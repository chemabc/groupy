# Seguridad y privacidad

15 de noviembre de 2026. Qué protege hoy la plataforma, qué riesgo queda en cada caso y qué se puede hacer
más adelante para reducirlo. Es una lista viva: **cada pieza nueva que guarde datos de personas, cuente
votos o abra una puerta hacia fuera añade aquí su entrada** (igual que añade su sección a «Comprobaciones
pendientes»).

Cada entrada tiene tres partes:
- **Qué se hace:** la medida que ya está programada (y dónde).
- **Riesgo que queda:** lo que la medida no cubre, dicho sin rebajarlo.
- **Para el futuro:** cómo se podría resolver, con su coste.

> **Quién puede ver qué, en general.** Una persona solo ve lo que su audiencia le deja. La administración de
> un grupo ve lo que necesita para administrarlo. El superadmin, desde la trastienda, ve todas las tablas de
> la plataforma. Quien tiene la base de datos (o una copia de seguridad) ve todo lo que está guardado en ella.
> Las medidas de este documento distinguen siempre esos cuatro niveles.

---

## 1. Principios

- **Nada se ve sin sesión** y **nada es público por defecto**: todo nace privado y se abre a propósito.
- **Seudónimo:** en la plataforma se actúa con un alias. La identidad real vive aparte, en la bóveda, sin
  ninguna columna que una las dos bases.
- **Recuentos en vez de nombres:** donde basta un número (votos de los debates, personas de un lugar,
  talentos de un grupo), se enseña el número y no quiénes.
- **Umbrales mínimos:** un recuento pequeño puede delatar a alguien; por eso algunos solo salen a partir de
  cierto número.
- **Lo mínimo:** no se guarda lo que no hace falta (por ejemplo, la hora de un voto secreto).
- **Borrar a tiempo:** lo terminado se archiva y, al año, se borra (con aviso).

---

## 2. Acceso y cuentas

### 2.1 Sesión obligatoria
- **Qué se hace:** todas las pantallas piden sesión, salvo la de entrada (`usuarios/middleware.py`,
  `EntradaObligatoria`). Las cookies de sesión y de CSRF llevan nombres propios para no mezclarse con la
  versión 1 en el mismo dominio.
- **Riesgo que queda:** el calendario por suscripción (.ics) se descarga sin sesión, con una clave en la
  dirección (ver 6.2).
- **Para el futuro:** nada más previsto.

### 2.2 Contraseñas
- **Qué se hace:** se guardan con **Argon2** (lo recomendado hoy). Al cambiarlas se piden las comprobaciones
  de Django: longitud mínima, que no se parezca al alias, que no sea común y que no sea solo números.
- **Riesgo que queda:**
  - No hay **límite de intentos** al entrar: alguien podría probar muchas contraseñas seguidas contra un alias.
  - No hay **segundo factor**.
  - Mientras dura el alta directa (registro A), el superadmin da la primera contraseña y la conoce hasta
    que la persona la cambia.
- **Para el futuro:**
  - Límite de intentos por alias y por dirección en Redis (pocas líneas, sin librería nueva), con espera
    creciente.
  - Segundo factor opcional (TOTP) para el superadmin y la administración.
  - Obligar a cambiar la contraseña en la primera entrada.

### 2.3 Formularios y páginas
- **Qué se hace:** protección CSRF en todos los formularios (también en las peticiones de htmx). Se prohíbe
  pintar la plataforma dentro de otra página (`XFrameOptionsMiddleware`). Las plantillas de Django escapan
  todo lo escrito por las personas.
- **Riesgo que queda:** **en producción falta todavía la configuración de HTTPS**:
  - redirigir a HTTPS;
  - HSTS;
  - cookies solo por HTTPS (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`);
  - una política de contenidos (CSP) que solo deje cargar los scripts propios.
- **Para el futuro:** añadirlas al preparar el despliegue y pasar `python manage.py check --deploy`. La CSP
  pide revisar los `x-data` y los `onclick` en línea.

### 2.4 Secretos
- **Qué se hace:** `DJANGO_SECRET_KEY` y `BOVEDA_CLAVE_HMAC` vienen de variables de entorno, fuera de las
  bases de datos.
- **Riesgo que queda:** las dos tienen un **valor de respaldo para desarrollo**. Si producción arrancara sin
  ellas, usaría ese valor, que está en el repositorio.
- **Para el futuro:** que la plataforma **no arranque** en producción (`DEBUG` apagado) sin las dos claves.
  Es una comprobación de pocas líneas en `config/settings.py`.

---

## 3. Identidad y seudónimo

### 3.1 La bóveda, separada
- **Qué se hace:** la identidad real (nombre, correo oficial, dominios por organización) va en su propia
  base de datos (`boveda`, `config/enrutador.py`), sin ninguna columna que la una con la plataforma. El
  correo y el DNI se guardan como **huellas** (HMAC con `BOVEDA_CLAVE_HMAC`), que solo sirven para saber si
  ya están registrados. El detalle está en «Registro y validación».
- **Riesgo que queda:**
  - Con el **alta provisional** de ahora, el superadmin registra a la persona en la bóveda **y** le crea el
    alias: sabe quién es quién.
  - Las dos bases están en el mismo servidor de PostgreSQL. Quien lo administra tiene las dos.
- **Para el futuro:**
  - Registro real de la fase 8 (firma ciega y espera de unos días): ni la bóveda ni el superadmin saben qué
    alias tiene cada persona.
  - Bóveda en otro servidor y con otra administración.

### 3.2 Lo que se sabe de cada alias
- **Qué se hace:** el lugar privado de cada persona solo lo ven ella y el superadmin; los demás ven cuántas
  personas hay en un lugar a partir de 5 (`lugares/servicios.py`, `MINIMO_PARA_CONTAR`). Los talentos se
  comparten por grupo y los recuentos no llevan nombres.
- **Riesgo que queda:** en un grupo pequeño, cruzar datos (asamblea base, lugar, talentos, horarios de
  actividad) puede bastar para adivinar quién hay detrás de un alias.
- **Para el futuro:** revisar los umbrales con grupos reales. Evitar mostrar a la vez varios datos de un
  mismo alias a quien no administra.

---

## 4. Visibilidad y permisos

### 4.1 Audiencias
- **Qué se hace:**
  - Cada cosa lleva su audiencia (privado, grupo, grupo padre, organización…) y las listas se filtran con
    ella (`audiencias/servicios.py`, `filtrar_visibles`, `puede_ver`).
  - **Regla dura entre organizaciones:** nada pasa de una organización a otra sin una invitación hecha y
    aceptada con privilegios.
  - Un debate solo se amplía a más gente, nunca a menos: quien ya participaba seguiría teniendo lo escrito.
- **Riesgo que queda:**
  - Los permisos y las audiencias de cada persona se guardan en Redis para no recalcularlos. Si un cambio
    no borrara bien esa caché, alguien podría seguir viendo algo **un rato** después de perder el acceso.
  - Hay pruebas para los casos conocidos, pero cada pantalla nueva tiene que acordarse de filtrar.
- **Para el futuro:**
  - Una prueba común que recorra todas las pantallas de lista con una persona de otra organización y
    compruebe que no ve nada.
  - Caducidad corta en la caché como red de seguridad.

### 4.2 Roles, cometidos y permisos
- **Qué se hace:** cada acción se comprueba en el servicio (`permisos.servicios.exigir`), no solo
  escondiendo el botón. La pantalla 403 explica qué falta. Los cometidos (facilitación, redacción,
  coordinación…) dan permisos solo sobre aquello concreto.
- **Riesgo que queda:** el **superadmin**, desde la trastienda, ve y cambia las tablas que cada módulo le
  enseña (no la bóveda). Las de votos de los debates y de las consultas no están en la trastienda.
- **Para el futuro:** registro de lo que se hace desde la trastienda (quién, qué tabla y cuándo), visible
  para el resto de la administración. Y una regla: ninguna tabla de votos entra en la trastienda.

---

## 5. Votos y opiniones

### 5.1 Debates
- **Qué se hace:**
  - En la pantalla solo se ven **recuentos**: nadie ve quién ha votado qué.
  - Las justificaciones de ⭐ y ⛔ salen **sin nombre**.
  - Los argumentos sí van firmados con el alias, a propósito.
- **Riesgo que queda:** la tabla de votos (`debates.Voto`) guarda **quién** ha votado, para poder quitar o
  cambiar el voto y para que nadie vote dos veces. Quien tenga la base de datos lo ve. La trastienda no la
  enseña.
- **Para el futuro:** guardar en vez del usuario una huella (HMAC del par debate-persona), como en las
  consultas con cambio de voto. Tiene el mismo límite, el secreto, hasta la bóveda.

### 5.2 Consultas: voto secreto
- **Qué se hace:**
  - **Quién ha votado** (`Participacion`) y **qué se ha votado** (`Papeleta`) van en tablas distintas.
  - Ninguna guarda la hora.
  - La papeleta no tiene usuario: solo la asamblea base, para el desglose por grupos, que sale solo con
    **10 votos o más**.
  - Sin cambio de voto, la papeleta lleva una clave al azar.
  - Con cambio de voto, la clave es un HMAC del par consulta-persona con un secreto derivado de
    `SECRET_KEY`.
- **Riesgo que queda:**
  - **Con cambio de voto:** quien tenga la base de datos **y** el secreto puede recalcular la clave de cada
    persona y saber qué votó. *(Aceptado el 15 de noviembre de 2026 hasta la bóveda real de la fase 8.)*
  - **Orden de llegada:** las dos filas de un voto se crean juntas y reciben números correlativos. Quien
    tenga la base de datos podría emparejar la n-ésima participación con la n-ésima papeleta. Con esto, el
    voto secreto es real **desde la plataforma**, pero **no frente a quien tiene la base de datos**.
  - Si cambia `SECRET_KEY` con una consulta abierta, quien ya votó no puede cambiar su voto (votaría de
    nuevo).
- **Para el futuro:**
  - **Fácil:** números al azar (UUID) en las papeletas y repartirlas en un orden desordenado. Así se quita el
    emparejamiento por número; queda el orden físico en el disco, más difícil de aprovechar.
  - **Completo (fase 8):** la persona vota con un pase de un solo uso firmado a ciegas. La plataforma no sabe
    de quién es la papeleta ni necesita guardar quién ha votado.

### 5.3 Solicitudes con apoyos
- **Qué se hace:** quien pide y quien apoya o rechaza se ve por su alias, a propósito: es un acto público
  dentro del grupo.
- **Riesgo que queda:** apoyar o no apoyar algo queda a la vista del grupo, y eso puede presionar.
- **Para el futuro:** decidir si algún tipo de solicitud debería tener apoyos anónimos.

---

## 6. Contenido y enlaces

### 6.1 Texto escrito por las personas (Markdown)
- **Qué se hace:** `base/markdown.py` desactiva el HTML y anula los enlaces `javascript:`, `data:` y
  `vbscript:`, también los disfrazados con entidades, espacios o mayúsculas.
- **Riesgo que queda:** se permiten **imágenes de otras webs** (`![](https://…)`). Al abrir el documento,
  el navegador de quien lee las pide a esa web, que puede saber desde qué dirección y cuándo se ha leído.
- **Para el futuro:** solo imágenes subidas a la plataforma, o pasar las de fuera por un intermediario propio
  que no revele a quien lee.

### 6.2 Calendario por suscripción (.ics)
- **Qué se hace:** cada persona tiene una clave secreta larga en su dirección de suscripción y puede
  cambiarla (la vieja deja de valer).
- **Riesgo que queda:** quien consiga la dirección ve los recordatorios de esa persona sin sesión. Las
  aplicaciones de calendario la guardan en sus servidores.
- **Para el futuro:** dar la opción de que la suscripción solo traiga títulos genéricos («Reunión») sin
  detalles.

### 6.3 Autoría y registro de cambios de los documentos
- **Qué se hace:** cada párrafo dice quién lo escribió y el registro de cambios no se puede borrar
  (transparencia de las actas).
- **Riesgo que queda:** el alias queda unido para siempre a lo escrito en un acta, aunque la persona se vaya
  del grupo.
- **Para el futuro:** al borrar una cuenta, cambiar su alias por «persona que ya no está» en las autorías.

---

## 7. Borrado y copias

- **Qué se hace:** `limpieza` archiva lo terminado a los 30 días y, al año, avisa 15 días antes y lo borra
  (salvo «Conservar»). Guarda un registro de borrados (qué tipo, su título y cuándo, sin el contenido) y quita las
  notificaciones viejas.
- **Riesgo que queda:** las **copias de seguridad** siguen teniendo lo borrado hasta que caducan. Aún no hay
  política de copias.
- **Para el futuro:** copias cifradas, con caducidad conocida y anotada aquí.

---

## 8. Desarrollo

- **Qué se hace:**
  - La barra de depuración solo existe con `DEBUG`.
  - En producción, las guías de desarrollo solo las ve el superadmin (`GUIAS_DE_DESARROLLO_PARA_TODOS`).
  - Los datos de ejemplo usan una contraseña común conocida, solo para desarrollo.
- **Riesgo que queda:** si se ejecutara `ejemplos crear` en producción, existirían cuentas con esa contraseña.
- **Para el futuro:** que la orden se niegue a funcionar sin `DEBUG`.

---

## 9. Editor colaborativo en tiempo real

Es un servicio aparte (carpeta `editor/`; ver «Diseño», apartado 13.2, y `editor/LEEME.md`).

### 9.1 Quién entra y qué puede hacer
- **Qué se hace:**
  - La plataforma decide en cada texto quién lo escribe, quién lo comenta y quién solo lo lee.
  - Se lo dice al editor con un **pase firmado** (JWT HS256) que dura **5 minutos** y lleva el alias, la
    sala y el permiso.
  - El editor no ve la base de datos ni conoce a las personas. Quien no puede escribir entra de solo
    lectura: el servidor descarta sus cambios aunque los mande a mano.
  - Al reconectar se pide un pase nuevo; si se ha perdido el permiso, ya no se entra.
  - Al aprobar un acta o al quitar la redacción a alguien, la plataforma pide al editor que cierre la sala.
- **Riesgo que queda:**
  - Si el editor no recibe ese aviso (caído, red), quien ya está dentro sigue con su permiso hasta que se
    desconecta.
  - El secreto es **compartido** (HS256): quien tenga el del editor podría fabricar pases.
- **Para el futuro:**
  - Pases asimétricos (Ed25519): la plataforma firma y el editor solo comprueba.

### 9.2 Las llamadas entre servidores
- **Qué se hace:**
  - El texto inicial, lo guardado y «cerrar sala» van firmados con HMAC del cuerpo y de la hora.
  - Se rechaza una firma de hace más de 5 minutos.
- **Riesgo que queda:** dentro de esos 5 minutos, una petición de guardado copiada se podría repetir. Solo
  volvería a poner un texto que ya estuvo, y quedaría en el registro de cambios.
- **Para el futuro:** un número de un solo uso en cada petición. Y HTTPS entre los dos servidores en
  producción.

### 9.3 Una copia más del texto
- **Qué se hace:**
  - El editor guarda en su carpeta (`EDITOR_DATOS`) el estado de Yjs de cada sala. Ese estado lleva la
    historia fina: también lo borrado.
  - La plataforma tiene siempre el texto bueno.
- **Riesgo que queda:**
  - Esa copia no se borra cuando `limpieza` borra el documento.
  - Su historia guarda texto que se escribió y se quitó (por ejemplo, un nombre puesto por error).
- **Para el futuro:**
  - Que la plataforma pida al editor borrar la sala al borrar o aprobar el documento.
  - Compactar la historia al aprobar.
  - Cifrar la carpeta.

### 9.4 Compilar con Typst
- **Qué se hace:**
  - Se compila en el servidor del editor, en un hilo aparte, con 8 segundos como mucho (si no, se mata el
    hilo).
  - Compila de una en una, en una carpeta vacía: un texto no puede leer ficheros del servidor (probado).
  - No se permiten paquetes (`@preview/…`), que se descargarían de internet.
  - Solo compila quien trae un pase de la sala.
  - Apagada, la vista no pide nada.
- **Riesgo que queda:** mucha gente con la vista encendida a la vez, o alguien pidiendo compilaciones sin
  parar, puede llenar la cola y hacer esperar a los demás.
- **Para el futuro:** un límite de compilaciones por pase y minuto, y varias compilaciones a la vez si el
  servidor tiene procesadores de sobra.

### 9.5 Comentarios dentro del texto
- **Qué se hace:**
  - Viven en el editor, en una sala aparte de cada texto.
  - Llevan el alias y el color de quien comenta.
  - Quien solo lee no puede escribirlos: el servidor descarta lo que mande.
- **Riesgo que queda:**
  - La plataforma no los tiene: no salen en su búsqueda ni los borra `limpieza`.
  - «Resuelto» los esconde, pero siguen guardados.
- **Para el futuro:** que el editor avise a la plataforma de los comentarios, y borrarlos al aprobar o
  borrar el documento.

### 9.6 El cliente en el navegador
- **Qué se hace:** el script del editor se sirve desde el propio editor (`/cliente.js`).
- **Riesgo que queda:** sin una política de contenidos (CSP), la página confía en todo lo que sirva esa
  dirección.
- **Para el futuro:** al poner la CSP (apartado 2.3), permitir solo el script y el WebSocket del editor. O
  servir el cliente desde los estáticos de la plataforma, con su huella (SRI).
