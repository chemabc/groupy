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

### 3.3 Actividad de cada persona («Sin actividad» en «Miembros»)
- **Qué se hace:**
  - Se guarda **solo el día** en que cada persona usa la plataforma (`Usuario.ultima_actividad`), una vez al
    día. Ni la hora, ni qué hace, ni desde dónde.
  - Nadie ve ese día. La administración de sus grupos solo ve la marca «Sin actividad (más de N días)»
    cuando se pasa del plazo, y el plazo no baja del mínimo que pone el superadmin (de partida, 30 días).
- **Riesgo que queda:**
  - Con el plazo mínimo y mirando la lista cada día, se puede deducir aproximadamente cuándo dejó de entrar
    alguien.
  - El superadmin puede leer el día en la base de datos o en la trastienda.
- **Para el futuro:**
  - Guardar solo la semana en lugar del día.
  - Que cada persona pueda ver en «Mis datos» que se guarda y para qué.

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
  - Cada consulta es **secreta** (de partida) o **pública**, y la ficha lo dice siempre.
  - En una secreta, **quién ha votado** (`Participacion`) y **qué se ha votado** (`Papeleta`) van en
    tablas distintas, sin hora.
  - La papeleta no tiene usuario: solo la asamblea base, para el desglose por grupos, que sale con **10 votos
    o más**.
  - La papeleta **no se guarda al votar**: espera en una urna (Redis) y se guarda en **tandas de 5 o más,
    desordenadas**, con un número al azar (UUID). Así no se puede emparejar con la participación ni por el
    número, ni por la operación en la que se creó, ni por el orden en el disco. Al cerrar se guarda lo que
    quede.
  - Sin cambio de voto, la clave de la papeleta es al azar.
  - Con cambio de voto, la clave es un HMAC del par consulta-persona con un secreto derivado de
    `SECRET_KEY`.
- **Riesgo que queda:**
  - **Con cambio de voto:** quien tenga la base de datos **y** el secreto puede recalcular la clave de cada
    persona y saber qué votó. *(Aceptado el 15 de noviembre de 2026 hasta la bóveda real de la fase 8.)* La
    ficha lo avisa.
  - **Quien vigile el servidor en directo** (Redis y la base a la vez, mientras se vota) podría ver llegar
    una papeleta a la urna justo cuando aparece una participación. Las tandas protegen lo guardado, no a
    quien mira en el momento.
  - **La última tanda** puede ser pequeña: si al cerrar quedan 2 papeletas, esas 2 se distinguen como «las
    últimas en votar». El desglose por grupos sigue pidiendo 10.
  - Si Redis perdiera sus datos (disco roto), se perderían las papeletas que esperaban. Por eso guarda cada
    cambio en disco.
  - Si cambia `SECRET_KEY` con una consulta abierta, quien ya votó no puede cambiar su voto (votaría de
    nuevo).
- **Para el futuro:** votar con un pase de un solo uso firmado a ciegas (fase 8). La plataforma no sabría
  de quién es la papeleta ni necesitaría guardar quién ha votado.

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

### 6.4 Conversaciones entre personas y salas de grupo
- **Qué se hace:**
  - Una conversación entre dos personas **solo la leen esas dos**: para cualquier otra, la dirección no
    existe (404), también para la administración y el superadmin. La sala de un grupo solo la leen sus
    miembros directos (403 a los demás, también al superadmin si no es miembro).
  - Solo se empieza a escribir a quien **comparte algún grupo**; a quien no, el error es el mismo exista o
    no el alias.
  - **Bloqueo:** cualquiera de las dos corta la conversación en los dos sentidos; el superadmin recibe un
    aviso con los dos alias, nunca el texto. Las tablas no están en la trastienda.
- **Riesgo que queda:**
  - Los mensajes se guardan **en claro** en la base de la plataforma: quien tenga la base (o una copia) los
    lee. Ni la administración ni el superadmin los ven desde la interfaz, pero sí quien administre el
    servidor.
  - Quien es bloqueado lo nota (la conversación dice que está bloqueada).
  - El aviso al superadmin cuenta quién bloqueó a quién: es un dato sobre la relación entre dos personas.
  - Quien conoce un alias que comparte grupo puede mandar un primer mensaje no deseado (no hay petición
    previa: decisión 3B de [A-56]).
- **Para el futuro:** cifrar los mensajes entre personas (de extremo a extremo, o al menos con una clave
  aparte, como la biblioteca del editor); límite de mensajes a desconocidos por día; denunciar un mensaje
  concreto con `moderacion` (el superadmin lo lee solo entonces, con registro y aviso, apartado 5.1 del
  diseño).

### 6.5 Archivos subidos
- **Qué se hace:**
  - Solo PDF, imágenes, formatos abiertos de oficina y texto; nunca de Microsoft (decisión de [A-60]: suelen
    llevar macros y metadatos). Se mira la **firma del contenido**, no solo la extensión, y hasta 20 MB.
  - Cada archivo pasa por **ClamAV** antes de guardarse; si hay virus o el antivirus no responde, no se
    guarda.
  - Los ficheros se guardan con un **nombre al azar** fuera de las carpetas públicas y los entrega una vista
    que comprueba quién ve el documento, con `X-Content-Type-Options: nosniff` (el navegador no «adivina»
    otro tipo). Solo los PDF y las imágenes se abren en el navegador; lo demás se descarga.
  - Espacio máximo por organización y papelera de 30 días antes de borrar el fichero de verdad.
- **Riesgo que queda:**
  - Sin antivirus configurado (desarrollo) los archivos quedan «sin revisar», y la ficha lo dice.
  - Un PDF puede llevar JavaScript o enlaces engañosos: el visor del navegador los limita, pero no se quitan.
  - Las imágenes y los PDF conservan sus **metadatos** (autor, GPS de una foto…).
  - Los ficheros no están cifrados en el disco; quien tenga el servidor los lee.
  - Si la transacción falla después de guardar el fichero (raro), puede quedar un fichero suelto sin
    documento.
- **Para el futuro:** quitar metadatos al subir (fotos y PDF), pasar los PDF por un «limpiador» que quite el
  JavaScript, cifrar los ficheros en el disco y una tarea que busque ficheros sueltos.

### 6.6 Portada pública y miniwebs
- **Qué se hace:**
  - Sin sesión solo se ve lo marcado «público» y publicado (portadas de la plataforma y de las
    organizaciones) y sus imágenes; cualquier otra dirección pide entrar. Una página de un grupo nunca
    puede ser pública (lo impide la base de datos).
  - Lo publicado es una foto en HTML seguro (sin HTML escrito a mano ni enlaces `javascript:`), y las
    imágenes se entregan con `nosniff`.
  - Las miniwebs internas solo las ve el grupo y lo que cuelga de él, quien lo administra y los grupos que
    han **aceptado** recibirlas (entre organizaciones, nada sin un sí).
- **Riesgo que queda:**
  - Lo público lo puede copiar e indexar cualquiera, también los buscadores; retirarlo no lo borra de fuera.
  - Las imágenes conservan sus metadatos (por ejemplo, el GPS de una foto).
  - Una página interna puede enlazar a otra web que registre quién llega desde ella.
- **Para el futuro:** quitar metadatos al subir imágenes, avisar antes de publicar algo público y la lista
  de lo publicado de cada ámbito para retirarlo rápido (diseño, apartado 15).

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
  - Viven en el editor, en una sala aparte de cada texto, con el alias de quien comenta.
  - Quien solo lee no puede escribirlos: el servidor descarta lo que mande.
  - Cada vez que cambian, el editor se los manda a la plataforma (firmado), que los guarda con el
    documento y los enseña en su ficha.
- **Riesgo que queda:**
  - Se guardan en dos sitios: el editor y la plataforma.
  - «Resuelto» los esconde en el editor, pero siguen guardados en los dos.
- **Para el futuro:** borrar la sala del editor (texto y comentarios) cuando la plataforma borra el
  documento.

### 9.6 El cliente en el navegador
- **Qué se hace:** el script del editor se sirve desde el propio editor (`/cliente.js`).
- **Riesgo que queda:** sin una política de contenidos (CSP), la página confía en todo lo que sirva esa
  dirección.
- **Para el futuro:** al poner la CSP (apartado 2.3), permitir solo el script y el WebSocket del editor. O
  servir el cliente desde los estáticos de la plataforma, con su huella (SRI).

### 9.7 Biblioteca del editor (plantillas, fragmentos, cabeceras y pies, imágenes)
- **Qué se hace:**
  - Todo se guarda **cifrado** con AES-256-GCM y la clave `EDITOR_CLAVE`: el índice (nombres, textos, con
    quién se comparte) y cada imagen. Cada fichero va sellado: si se toca o se cambia por otro, no se lee.
  - El editor no sabe quién es cada persona: el pase lleva un número sacado con HMAC de su número en la
    plataforma, que no se puede volver atrás, y los ámbitos a los que pertenece.
  - Se ve solo lo de tus ámbitos, lo tuyo y lo compartido contigo; se cambia lo de los ámbitos que
    administras y lo tuyo. Lo de una aplicación nunca lo ve otra.
  - Para compartir con una persona, la plataforma solo devuelve a quien ya se puede ver en las listas de
    miembros, con el número del editor (nunca el de la plataforma).
  - Las imágenes se comprueban por sus primeros bytes (solo PNG, JPEG y GIF; nada de SVG, que puede llevar
    código), con 2 MB como mucho, y se sirven con `nosniff` y sin caché compartida.
  - Al compilar, solo se dan al compilador las imágenes que ve quien compila, en memoria.
- **Riesgo que queda:**
  - La clave está en el mismo servidor que los datos: protege si se roban el disco o una copia, no si
    alguien controla el servidor del editor mientras funciona.
  - **Si se pierde la clave, se pierde la biblioteca.** Hay que guardarla aparte.
  - Los ámbitos viajan en el pase: si alguien deja un grupo, sigue viendo lo compartido con ese grupo hasta
    que caduca su pase (5 minutos).
  - Quien recibe algo compartido puede copiarlo; dejar de compartir no lo borra de donde lo copió.
  - Las imágenes se ven con el pase en la dirección (`?pase=…`, para poder usar `<img>`): puede quedar en
    los registros del servidor, aunque caduca en 5 minutos.
- **Para el futuro:**
  - Guardar la clave en un gestor de secretos y poder cambiarla (descifrar con la vieja y cifrar con la
    nueva).
  - Una clave por aplicación, sacada de la principal.
  - Ver las imágenes con un permiso de un solo uso en vez del pase.
