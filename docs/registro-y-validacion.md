# Registro y validación: cómo funciona, explicado para no olvidarlo

12 de noviembre de 2026. Resume lo decidido en la versión 1 sobre la bóveda de identidad, más las propuestas para el proyecto
nuevo, que van marcadas como tales. Forma parte del diseño ([diseno.md](diseno.md), apartado 7).

> **Palabras:** en la aplicación, la cuenta de cada persona se llama **usuario**, y su nombre visible
> (el seudónimo) es su **alias**. En este documento se dice «alias» cuando importa subrayar que es un
> seudónimo.

---

## 1. La idea en dos frases

1. Queremos saber que **detrás de cada cuenta hay una persona real**, que **nadie tiene dos cuentas** y
   que quien es expulsado **no puede volver con otra**.
2. Y a la vez, que **nadie pueda saber qué persona está detrás de cada cuenta**: ni las demás
   personas, ni los admin, ni la propia aplicación.

**Comparación:** es como votar en unas elecciones. En la mesa comprueban tu DNI y te tachan del censo
(saben que has votado), pero tu papeleta va en un sobre cerrado a la urna (nadie sabe qué has
votado). Aquí, la «mesa» es la **bóveda** y la «urna» es la **plataforma**.

---

## 2. Las dos casas que no se hablan

| | **Bóveda** (identidad real) | **Plataforma** (la aplicación) |
|---|---|---|
| Qué sabe | Quién eres de verdad y si estás validada | Tu alias, tus grupos y lo que haces |
| Qué **no** sabe | Cuál es tu alias | Quién eres de verdad |
| Dónde vive | Base de datos «boveda», con su propio usuario | Base de datos «asambleas» |

- **Ninguna columna une las dos bases.** El programa prohíbe expresamente crear una relación entre
  ellas.
- Lo único que pasa de una casa a la otra es un **pase**, y gracias a la **firma ciega** (apartado 4) no
  deja rastro de quién lo llevó.

---

## 3. Palabras clave

| Palabra | Qué es |
|---|---|
| **Persona** | La identidad real (nombre, correo oficial). Solo existe en la bóveda. En las listas aparece como «Persona 3f2a9c1e». |
| **Alias** | La cuenta con seudónimo con la que se actúa en la plataforma. Nunca contiene datos reales. |
| **Asamblea base** | El grupo más local de la persona: donde pide entrar y donde se valida. |
| **Validar** | Comprobar que la persona es quien dice ser y que no está ya dentro. |
| **Pase** | Un «vale» de un solo uso que da la bóveda a una persona validada. Sirve para activar **un** alias. |
| **Firma ciega** | Forma de firmar un pase **sin verlo**, de modo que después no se puede reconocer. Es el estándar RFC 9474. |
| **Huella (HMAC)** | Un código que se calcula a partir de un dato (DNI, correo) y sirve para saber si ese dato ya está registrado, sin guardar el dato. Con la huella no se puede reconstruir el DNI. |
| **Sobre de identidad** | Un certificado cifrado, colgado del alias, que solo se abre ante una denuncia grave. Es la única forma prevista de unir alias y persona. |
| **Ronda** | *(Propuesta)* Una revalidación general: todo el mundo vuelve a conseguir un pase en un plazo. |

---

## 4. El pase y la firma ciega: qué son, quién los usa, para qué y cuándo

**Qué es un pase.** Un número aleatorio que fabrica el navegador de la persona y que la bóveda firma.
La firma dice: «quien traiga esto es una persona validada de la asamblea base X». No dice quién.

**Por qué «a ciegas».** Antes de enviarlo a firmar, el navegador **tapa** el pase con otro número
aleatorio que solo él conoce. La bóveda firma el pase tapado. Luego el navegador lo **destapa** y la
firma sigue valiendo.

> **Comparación:** firmas un sobre cerrado que lleva dentro papel de calco. La firma se calca en el
> papel de dentro, pero tú nunca ves ese papel. Si mañana alguien te lo enseña, no puedes saber a quién
> se lo firmaste.

**Quién lo usa y cuándo:**

| Momento | Quién | Qué pasa | Qué queda guardado |
|---|---|---|---|
| Tras validarse | Navegador de la persona → bóveda | La bóveda firma el pase tapado | Bóveda: «Persona X ya recibió su pase, el día D» (sin el pase) |
| Unos días después | Navegador de la persona → plataforma | La plataforma comprueba la firma y activa el alias | Plataforma: «se usó un pase con esta huella el día D» (**sin decir qué alias**) |

**Para qué sirve:**
- **Un pase por persona** (y una huella de DNI única): nadie tiene dos alias, y quien es expulsado no
  consigue un segundo pase.
- Un pase **solo se puede usar una vez**: la plataforma apunta su huella.
- **Ni juntando las dos bases** se puede saber qué alias es de qué persona.

**Por qué se espera unos días y se guardan solo fechas, nunca horas.** Si a las 10:03 se firmó un
pase y a las 10:04 se activó un alias, se emparejan solos. Con solo el día y unos días de espera, el
cruce deja de funcionar.

**Decidido:** en ninguna pantalla se muestra qué pase usó cada alias. En la ficha del alias solo
puede figurar «activado el día X».

---

## 5. El registro, paso a paso

```
PERSONA (su navegador)            BÓVEDA                           PLATAFORMA
  1. Nombre, correo oficial,  ──► [Persona: pendiente;
     asamblea base                 huella del correo]
     (alias y contraseña se
      quedan en su navegador)
  2. Se valida (apartado 6)  ◄──► [Validación: método, día]
                                   Si se aprueba: se BORRA el
                                   correo oficial y queda su huella
  3. Tapa el pase            ──►  firma sin verlo
                             ◄──  [PaseEmitido: persona, día]
  4. Destapa el pase y fabrica
     el sobre de identidad
  5. Espera unos días
  6. Envía alias, contraseña,
     correo alternativo, pase
     y sobre                 ───────────────────────────────►  comprueba firma y pase sin usar
                                                               [Pase usado: huella, día]
                                                               [Alias activo + sobre]
                                                               [Pertenencia a su asamblea base]
```

- El alias se elige al principio, pero la plataforma **no lo recibe hasta el paso 6**. Así no puede
  saber que se creó el mismo día que alguien pidió el alta en la bóveda.
- El **correo alternativo** es el que usa la plataforma desde entonces (avisos, recuperación). El correo
  oficial ya no existe en ningún sitio.
- **Recuperar el alias** solo se puede hacer con un código de recuperación que guarda la propia
  persona.

**Variante: alta hecha por el superadmin.** El superadmin registra a la persona en la bóveda. La bóveda
le envía al correo oficial un enlace de un solo uso y después borra el correo. Desde ahí, la persona
sigue los pasos 3 a 6 ella sola. El superadmin sabe quién es la persona, pero **no qué alias elige**.

**Lo que se hace hoy (provisional, versión 1).** La firma ciega, el sobre y los documentos no están
programados. El superadmin crea el alias directamente en el panel y se lo comunica a la persona. En la
bóveda no queda nada. Cuando se programe el registro real, habrá que dar de alta en la bóveda a estas
personas con su pase marcado como «ya emitido», para que no puedan conseguir un segundo alias.

---

## 6. Los cinco métodos para validar la identidad

El superadmin elige cuáles se aceptan en cada organización (patrón «estrategia»: cada método es una
pieza intercambiable).

| # | Método | Cómo funciona | Qué se guarda | Úsalo cuando… |
|---|---|---|---|---|
| 1 | **Dominio de correo** | La persona escribe su correo institucional (p. ej. `@educa.madrid.org`) y recibe un código. Si lo introduce, queda validada. | Huella del correo, método y día. | El colectivo tiene un correo institucional común. Es el método más cómodo. |
| 2 | **Documentos firmados** | Sube un PDF oficial firmado digitalmente (nombramiento, hoja de servicios…). Se comprueba que la firma cubre el fichero entero, que la autoridad y el firmante son de la lista permitida y que la letra del DNI es correcta. | Huella del DNI, tipo de documento y día. **El PDF se borra.** | Se quiere una prueba fuerte o no hay un correo común. |
| 3 | **Documentos y dominio** | Los dos anteriores a la vez. | Lo de ambos. | Hace falta la máxima seguridad. |
| 4 | **Alta por el superadmin** | El superadmin conoce a la persona y la registra él mismo. | Método «superadmin» y día. | Las primeras personas, o casos especiales. |
| 5 | **Validación colectiva** | La asamblea base avala a la persona (5 avales por defecto, con plazo). Puede presentarse con su nombre o con un **alias provisional** distinto del definitivo. Las dudas son anónimas para ella, pero el admin y el superadmin las ven, y abren un canal de conversación. | En la bóveda, solo «aprobada» o «rechazada» y el día. Los avales y las dudas se quedan en la plataforma, entre alias. | Grupos sin documentos ni correo común que se conocen en persona. |

**Tipos de documento.** El superadmin los define en un editor: autoridades de certificación, firmantes
permitidos, qué comprobar en el contenido y documentos que se exigen juntos. Se puede probar con un
PDF real, que no se guarda. Vienen cargados los cinco documentos de docentes de Madrid.

**Licencia.** La comprobación de documentos se programa con código propio. No se copia mlsurvey,
porque es GPLv3.

---

## 7. Otras «validaciones» que **no** son de identidad

Se llaman parecido, pero son cosas distintas. Conviene no mezclarlas.

| Qué | Qué comprueba | Dónde ocurre | Quién decide |
|---|---|---|---|
| **Validar la identidad** (apartado 6) | Que es una persona real y única | Bóveda | Los métodos 1 a 5 |
| **Validar el centro** | Que el alias trabaja o estudia en el centro que dice (su instituto, su escuela…) | Plataforma | 3 avales de alias del mismo centro o de un grupo directo común, o el superadmin. Las dudas paran el proceso hasta que decide el superadmin. Cambiar de centro obliga a validarlo de nuevo. |
| **Admitir en un grupo** | Que el grupo acepta a ese usuario. Nadie pertenece a una organización sin pertenecer a uno de sus grupos | Plataforma | El superadmin, el admin_org o el voto del admin_grupo (cuántos votos más hacen falta está pendiente de decidir). Solo ven el alias. |
| **Revalidación general** *(propuesta)* | Que cada alias sigue teniendo una persona propia detrás | Bóveda y plataforma, con firma ciega | Ronda abierta por el superadmin con un motivo público (apartado 9) |

**Privacidad del centro.** Solo ven el centro la propia persona y el superadmin, y además quienes avalan
(es un coste aceptado). En mapas y grupos solo se dice cuántas personas hay en cada centro, y solo si
son al menos 5.

---

## 8. Qué ve cada quién (se mantiene lo de la versión 1)

| Dato | Superadmin | Admin_org / admin_grupo | Resto de alias |
|---|---|---|---|
| Nombre real | Solo dentro de la ficha de la persona en la bóveda. En las listas aparece «Persona 3f2a9c1e» | Nunca | Nunca |
| Correo oficial | Solo mientras se valida; después se borra | Nunca | Nunca |
| DNI | Nunca (solo existe su huella) | Nunca | Nunca |
| Documentos | Nunca (se borran); se ve «validada por documento el día X» | Nunca | Nunca |
| Qué pase usó un alias | Nadie lo sabe, ni siquiera el sistema | — | — |
| Alias, grupos y actividad | Sí | Los de su ámbito | Según lo que comparten |
| Centro de un alias | Sí | No | No (solo recuentos de 5 o más) |
| Quién ofrece cada talento | — | No (solo cuántas personas) | No (solo cuántas personas) |

Además, los cambios en la bóveda **no se apuntan en el historial del panel**, porque ese historial
guarda la hora exacta en la base de la plataforma.

---

## 9. Revalidación general por rondas *(propuesta para el proyecto nuevo)*

**Para qué.** Si se sospecha que hay cuentas duplicadas, compradas o falsas, pero no se sabe cuáles (el
sistema impide saberlo), se pide a todo el mundo que vuelva a conseguir un pase.

**Cómo funciona:**
1. El superadmin abre la ronda N+1: elige el alcance (por defecto, toda la organización; nunca una
   asamblea pequeña sola), el plazo (por ejemplo, 14 días) y un **motivo público**.
2. Cada persona se identifica otra vez en la bóveda y recibe un pase nuevo, con firma ciega y con la
   clave de esa ronda. Solo hay un pase por persona y ronda.
3. Desde su alias, canjea el pase. La plataforma apunta «validado en la ronda N+1», sin fecha.
4. Al acabar el plazo, los alias que no se han revalidado quedan **suspendidos**: pueden leer, pero no
   participar. No se borran y se reactivan si se revalidan más tarde.
5. Se publican los recuentos: cuántas personas y cuántos alias se han revalidado. La diferencia es el
   número de alias que no tenían una persona propia detrás.

**Lo que no resuelve:** que una persona real preste su identidad a otra.

---

## 10. El sobre de identidad y los custodios (la única «puerta trasera», y con testigos)

**Para qué existe.** Si alguien comete algo grave con su alias (amenazas, acoso, suplantación) y hay una
denuncia, la comunidad puede necesitar saber quién es. Sin ninguna puerta, sería imposible. Con una
puerta que abre una sola persona sin control, el anonimato no valdría nada. El sobre es una puerta
**cerrada, que deja rastro y que (en la versión 2) solo se abre entre varias personas**.

**Qué es el sobre.** Al activar el alias, el navegador de la persona fabrica un certificado de la bóveda
que dice «este alias es la Persona nº X» y lo **cifra** (lo mete en una caja fuerte digital). La caja se
guarda colgada del usuario en la plataforma. Nadie puede leerla sin la llave.

**Versión 1 (la de ahora): una sola llave.**
- La llave la tiene el superadmin, guardada fuera del servidor.
- Solo abre un sobre ante una denuncia grave.
- Cada apertura **se registra** y **se avisa a la persona** con el motivo.
- El alta lo explica: no se promete un anonimato total.

**Versión 2: custodios de identidad.**
- La llave se **parte en trozos** con una técnica llamada *cifrado umbral*: con un número mínimo de
  trozos (por ejemplo 5) se puede abrir; con menos, no se averigua nada.
- Cada trozo lo guarda un **custodio de identidad**: una persona elegida de antemano por su grupo, que lo
  tiene en su propio dispositivo. El servidor nunca tiene los trozos.
- **Qué hace un custodio:** recibe las peticiones de apertura con su motivo, las estudia y aprueba o
  rechaza. Si se juntan al menos 5 aprobaciones de custodios **de grupos distintos** (de la asamblea base
  de la persona, del grupo de coordinación y de otros grupos), el sobre se abre.
- **Qué no hace:** no ve datos de nadie, no modera y no tiene ningún otro poder en la plataforma. Su
  trozo, solo, no sirve para nada.
- **Relevo:** cuando un custodio deja su grupo, se reparten trozos nuevos de la misma llave, sin abrir
  ningún sobre.
- **Paso de la versión 1 a la 2:** el superadmin abre cada sobre por última vez, lo cifra con la llave
  repartida y destruye la suya.

## 11. Riesgos que quedan (resumen)

| Riesgo | Cómo se reduce |
|---|---|
| Asambleas muy pequeñas: aparece un alias nuevo justo después de un alta | Esperar unos días antes de activar el alias; activaciones por tandas |
| Forma de escribir, horarios o talentos raros | Talentos anónimos (solo recuentos) |
| El superadmin de la versión 1 lo administra todo | Registro y aviso de aperturas; custodia repartida en la versión 2 |
| Quien se haga con el servidor | Claves fuera de la base, gestor de secretos, servidores separados |
| Direcciones IP en los registros | Se borran a las 24 horas; activar el alias desde otra red |
| Copias de seguridad conjuntas | Copias separadas y cifradas con claves distintas |
| Centro + asamblea base dejan pocos candidatos | El centro solo lo ven la persona y el superadmin; recuentos de 5 o más |

---

## 12. Estado

| Pieza | Estado |
|---|---|
| Dos bases separadas, huellas, solo fechas, UUID, «Persona 3f2a9c1e» | Hecho (versión 1) |
| Alta provisional por el superadmin en el panel | Hecho (versión 1) |
| Validación del centro por avales | Hecho (versión 1) |
| Firma ciega, pase y activación del alias | Pendiente |
| Sobre de identidad y registro de aperturas | Pendiente |
| Validación por dominio, por documentos y colectiva | Pendiente |
| Rondas de revalidación | Propuesta |
| Admisión en grupos | Decidido quién admite; falta decidir cuántos votos (ver diseno.md, apartado 20) |
