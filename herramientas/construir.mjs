// Prepara las librerías de JavaScript de la interfaz para que las sirva el propio servidor (sin CDN).
//
// Lo ejecutan las órdenes «npm run construir» y «npm run vigilar» (definidas en package.json), antes de
// compilar el CSS con Tailwind. Copia htmx, Alpine, SortableJS, Leaflet (mapas) y FullCalendar (calendario) desde node_modules (donde las deja «npm install»)
// a static/generado/, la carpeta que Django sirve como ficheros estáticos. Esa carpeta no se guarda en
// Git: se regenera al crear el contenedor.

import { copyFileSync, cpSync, mkdirSync } from "node:fs";

// Carpeta de destino de los ficheros generados.
const destino = "static/generado";

// Ficheros que se copian: de dónde salen (dentro de node_modules) y con qué nombre se guardan.
const ficheros = [
  // htmx: pide trozos de HTML al servidor y los coloca en la página sin recargarla.
  ["node_modules/htmx.org/dist/htmx.min.js", "htmx.min.js"],
  // Alpine.js: pequeños comportamientos en la página (abrir y cerrar menús, ventanas, el tema).
  ["node_modules/alpinejs/dist/cdn.min.js", "alpine.min.js"],
  // SortableJS: ordenar listas arrastrando (los campos de una tipología; más adelante, el kanban).
  ["node_modules/sortablejs/Sortable.min.js", "sortable.min.js"],
  // Leaflet: mapas (la isla del mapa de lugares), con su hoja de estilos.
  ["node_modules/leaflet/dist/leaflet.js", "leaflet/leaflet.js"],
  ["node_modules/leaflet/dist/leaflet.css", "leaflet/leaflet.css"],
  // Complemento de Leaflet que agrupa las chinchetas cercanas en un círculo con su número.
  ["node_modules/leaflet.markercluster/dist/leaflet.markercluster.js", "leaflet/leaflet.markercluster.js"],
  ["node_modules/leaflet.markercluster/dist/MarkerCluster.css", "leaflet/MarkerCluster.css"],
  ["node_modules/leaflet.markercluster/dist/MarkerCluster.Default.css", "leaflet/MarkerCluster.Default.css"],
  // FullCalendar (licencia MIT): la isla del calendario, con todas sus vistas (mes, semana, día, lista)
  // y la posibilidad de arrastrar. Trae sus estilos dentro. Y sus textos en castellano.
  ["node_modules/fullcalendar/index.global.min.js", "fullcalendar/index.global.min.js"],
  ["node_modules/@fullcalendar/core/locales/es.global.min.js", "fullcalendar/es.global.min.js"],
];

// Carpetas que se copian enteras: las imágenes de las chinchetas de Leaflet (su CSS las busca en
// «images/», junto a él).
const carpetas = [["node_modules/leaflet/dist/images", "leaflet/images"]];

// Crea las carpetas de destino si no existen («recursive» crea también las carpetas intermedias).
mkdirSync(`${destino}/leaflet`, { recursive: true });
mkdirSync(`${destino}/fullcalendar`, { recursive: true });

// Copia cada fichero y lo anuncia en la terminal.
for (const [origen, nombre] of ficheros) {
  copyFileSync(origen, `${destino}/${nombre}`);
  console.log(`Copiado ${origen} → ${destino}/${nombre}`);
}

// Copia cada carpeta entera («recursive»: con todo lo que tiene dentro).
for (const [origen, nombre] of carpetas) {
  cpSync(origen, `${destino}/${nombre}`, { recursive: true });
  console.log(`Copiada ${origen} → ${destino}/${nombre}`);
}
