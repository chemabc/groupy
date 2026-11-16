#!/usr/bin/env bash
# Deja la plataforma al día y comprueba que todo responde, antes de una ronda de comprobaciones a mano
# (docs/comprobaciones.md). Se ejecuta dentro del contenedor, en la terminal de VS Code:
#
#     bash herramientas/al_dia.sh
#
# Hace, en orden: dice en qué versión está cada repositorio, instala las librerías que falten, construye la
# interfaz, pone al día las dos bases de datos, comprueba que el código no tiene cambios de tablas sin
# migración, pregunta a las bases, a Redis, al editor, al antivirus y al trabajador si responden, crea los
# datos de ejemplo que falten y ejecuta las tareas diarias. No borra nada.
#
# Cada paso dice ✔ (bien) o ✘ (mal, con el motivo debajo). Si uno falla, sigue con los demás y al final
# dice cuántos han fallado. Lo explica docs/arranque.md, apartado 5.

# Va a la carpeta del proyecto (la de encima de herramientas/), se ejecute desde donde se ejecute.
#   - dirname "$0": la carpeta de este script
#   - /..: la de encima
cd "$(dirname "$0")/.." || exit 1

# Cuántos pasos han fallado.
fallos=0

# Ejecuta un paso: escribe su nombre, ejecuta la orden sin enseñar lo que dice y escribe ✔ o ✘. Si falla,
# enseña las últimas líneas de lo que dijo, para saber por qué.
#   - $1: nombre del paso, para leer
#   - el resto: la orden que se ejecuta
paso() {
  local nombre="$1"
  shift
  local salida
  # 2>&1: junta los errores con la salida normal, para guardarlo todo
  if salida=$("$@" 2>&1); then
    echo "✔ $nombre"
  else
    echo "✘ $nombre"
    # tail -n 15: solo las 15 últimas líneas
    echo "$salida" | tail -n 15 | sed 's/^/    /'
    fallos=$((fallos + 1))
  fi
}

# Comprueba que lo que escribe una orden contiene un texto esperado (para «bien», «PONG», «403»…).
#   - $1: el texto que tiene que salir
#   - el resto: la orden
contiene() {
  local esperado="$1"
  shift
  local salida
  salida=$("$@" 2>&1)
  # grep -q: solo dice si lo encuentra, sin escribir nada
  #   -F: busca el texto tal cual, sin comodines
  if echo "$salida" | grep -qF "$esperado"; then
    return 0
  fi
  echo "Se esperaba «$esperado» y ha salido: $salida"
  return 1
}

echo "── Versiones ──"
# git log -1 --format: el último commit, con su número corto, su fecha y su mensaje
#   - %h: número corto · %cd: fecha · %s: mensaje
#   - --date=format:…: la fecha como día/mes hora:minutos
echo "  Plataforma: $(git log -1 --date=format:'%d/%m %H:%M' --format='%h %cd %s')"
# -C editor: lo mismo dentro de la carpeta del editor (es otro repositorio)
echo "  Editor:     $(git -C editor log -1 --date=format:'%d/%m %H:%M' --format='%h %cd %s')"
# git status --short: lo cambiado y sin guardar en un commit (vacío si no hay nada)
#   - grep -v '^?? .claude/': sin la carpeta de Claude, que no se sube nunca
cambios=$(git status --short | grep -v '^?? .claude/')
if [ -n "$cambios" ]; then
  echo "  (Aviso) Hay cambios sin guardar en la plataforma:"
  echo "$cambios" | sed 's/^/    /'
fi

echo "── Librerías e interfaz ──"
# pip install: instala las librerías de Python que falten (si ya están, solo lo comprueba)
#   - --user: en la carpeta del usuario
#   - -q: sin detalles
#   - -r requirements.txt: las de esa lista
paso "Librerías de Python" pip install --user -q -r requirements.txt
# npm install: instala las librerías de la interfaz que falten
#   - --no-audit --no-fund: sin avisos de más
paso "Librerías de la interfaz" npm install --no-audit --no-fund
# npm run construir: copia htmx, Alpine y las demás a static/generado/ y compila el CSS con las clases nuevas
paso "Interfaz construida (CSS y JavaScript)" npm run construir
# Si algún fichero del editor es más nuevo que su cliente construido, el editor no se ha reiniciado desde
# el último cambio (al arrancar lo construye).
#   - find editor/src -newer editor/publico/cliente.js: los ficheros cambiados después de construirlo
if [ -n "$(find editor/src -newer editor/publico/cliente.js 2>/dev/null)" ] || [ ! -f editor/publico/cliente.js ]; then
  echo "✘ Cliente del editor al día: hay cambios en editor/src más nuevos. Reinicia el editor (bloque 1: docs/arranque.md, apartado 5.1)."
  fallos=$((fallos + 1))
else
  echo "✔ Cliente del editor al día"
fi

echo "── Bases de datos ──"
# migrate: aplica las migraciones que falten en la base de la plataforma (si no falta ninguna, no hace nada)
paso "Tablas de la plataforma al día" python manage.py migrate --noinput
# --database=boveda: lo mismo en la base de la bóveda, que va aparte
paso "Tablas de la bóveda al día" python manage.py migrate --database=boveda --noinput
# makemigrations --check --dry-run: falla si el código tiene cambios de tablas sin su migración (no crea nada)
paso "Sin cambios de tablas pendientes" python manage.py makemigrations --check --dry-run
# check: revisa la configuración de Django
paso "Configuración de Django" python manage.py check
# Pregunta a cada base cómo se llama (si responde, funciona)
#   - shell -c: ejecuta el Python que va entre comillas con Django ya cargado
paso "La base de la plataforma responde" contiene "asambleas" python manage.py shell -c "
from django.db import connections
with connections['default'].cursor() as cursor:
    cursor.execute('select current_database()')
    print(cursor.fetchone()[0])"
paso "La base de la bóveda responde" contiene "boveda" python manage.py shell -c "
from django.db import connections
with connections['boveda'].cursor() as cursor:
    cursor.execute('select current_database()')
    print(cursor.fetchone()[0])"
# Redis: caché, permisos precalculados y la urna de las consultas secretas
#   - -c: ejecuta la línea de Python que va entre comillas
paso "Redis responde" contiene "True" python -c "import redis; print(redis.Redis(host='redis').ping())"
# Redis guarda cada cambio en disco (para no perder papeletas de la urna si se reinicia)
paso "Redis guarda en disco" contiene "yes" python -c "import redis; print(redis.Redis(host='redis').config_get('appendonly')['appendonly'])"

echo "── Servicios ──"
# curl: pide una dirección
#   - -s: sin barra de progreso
#   - -m 5: espera 5 segundos como mucho
paso "El editor responde" contiene "bien" curl -s -m 5 http://editor:1234/salud
# La plataforma vista desde el editor (por el nombre «app»): «403» quiere decir que la petición llega y
# solo falta la firma, que es lo correcto. Necesita el servidor en marcha.
#   - -o /dev/null: no enseña la respuesta
#   - -w "%{http_code}": escribe solo el código de la respuesta
paso "La plataforma responde al editor" contiene "403" curl -s -m 5 -o /dev/null -w "%{http_code}" "http://app:8000/editor/texto/?sala=x"
# El antivirus contesta PONG a PING (la primera vez tras reconstruir tarda unos minutos en descargar firmas)
paso "El antivirus responde" contiene "PONG" python -c "import socket; s=socket.create_connection(('antivirus',3310),5); s.sendall(b'zPING\0'); print(s.recv(10))"
# El trabajador vacía la bandeja de avisos: se cuentan, se esperan 5 segundos y se cuentan otra vez. Bien si
# está vacía o si baja.
contar_bandeja() {
  python manage.py shell -c "from eventos_sw.models import AvisoPendiente; print(AvisoPendiente.objects.count())" 2>/dev/null | tail -n 1
}
trabajador() {
  local antes despues
  antes=$(contar_bandeja)
  [ "$antes" = "0" ] && return 0
  sleep 5
  despues=$(contar_bandeja)
  [ "$despues" -lt "$antes" ] && return 0
  echo "La bandeja tiene $despues avisos y no baja: el trabajador está parado o con código viejo. Reinícialo"
  echo "(bloque 1: docs/arranque.md, apartado 5.1). Último error de un aviso atascado:"
  # La última línea del error guardado del aviso con más intentos (vacío si ninguno ha fallado aún)
  python manage.py shell -c "
from eventos_sw.models import AvisoPendiente
aviso = AvisoPendiente.objects.exclude(ultimo_error='').order_by('-intentos').first()
print(aviso.ultimo_error.strip().splitlines()[-1] if aviso else '(ninguno ha fallado: el trabajador no está en marcha)')" 2>/dev/null | tail -n 1
  return 1
}
paso "El trabajador reparte los avisos" trabajador

echo "── Datos ──"
# ejemplos crear: crea los datos de ejemplo que falten (no toca lo que ya hay)
paso "Datos de ejemplo" python manage.py ejemplos crear
# tareas_diarias: series de eventos, solicitudes caducadas y limpieza, una vez
paso "Tareas diarias" python manage.py tareas_diarias
# La plataforma en el navegador: «200» o «302» (lleva a la entrada) quiere decir que el servidor está en marcha.
servidor() {
  local codigo
  codigo=$(curl -s -m 5 -o /dev/null -w "%{http_code}" http://localhost:8000/)
  [ "$codigo" = "200" ] || [ "$codigo" = "302" ] && return 0
  echo "Responde «$codigo». Arranca el servidor en otra terminal: python manage.py runserver 0.0.0.0:8000"
  return 1
}
paso "El servidor está en marcha" servidor

echo
if [ "$fallos" -eq 0 ]; then
  echo "Todo bien. Abre http://localhost:8000 y recarga con Ctrl+F5. Empieza por la «Guía rápida de comprobación»."
else
  echo "Han fallado $fallos paso(s). Mira el motivo debajo de cada ✘ y docs/arranque.md, apartado 5."
fi
# Termina con 0 si todo ha ido bien y con 1 si algo ha fallado (para usarlo desde otras órdenes)
[ "$fallos" -eq 0 ]
