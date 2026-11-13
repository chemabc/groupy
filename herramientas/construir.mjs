// Prepara las librerías de JavaScript de la interfaz para que las sirva el propio servidor (sin CDN).
//
// Lo ejecutan las órdenes «npm run construir» y «npm run vigilar» (definidas en package.json), antes de
// compilar el CSS con Tailwind. Copia htmx, Alpine y SortableJS desde node_modules (donde las deja «npm install»)
// a static/generado/, la carpeta que Django sirve como ficheros estáticos. Esa carpeta no se guarda en
// Git: se regenera al crear el contenedor.

import { copyFileSync, mkdirSync } from "node:fs";

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
];

// Crea la carpeta de destino si no existe («recursive» crea también las carpetas intermedias).
mkdirSync(destino, { recursive: true });

// Copia cada fichero y lo anuncia en la terminal.
for (const [origen, nombre] of ficheros) {
  copyFileSync(origen, `${destino}/${nombre}`);
  console.log(`Copiado ${origen} → ${destino}/${nombre}`);
}
