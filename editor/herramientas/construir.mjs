// Construye el editor para el navegador: junta src/cliente/editor.mjs con sus librerías (CodeMirror, Yjs,
// Hocuspocus) en un solo fichero, publico/cliente.js, que el servidor sirve en /cliente.js.
// Se ejecuta con «npm run construir» (dentro de la carpeta editor/).

import { build } from "esbuild";

// Opciones de esbuild:
//   - entryPoints: el fichero de partida.
//   - bundle: mete dentro todo lo que importa.
//   - format "iife": un script normal, que se carga con <script src>.
//   - minify: lo más pequeño posible.
//   - target: navegadores de los últimos años.
await build({
  entryPoints: ["src/cliente/editor.mjs"],
  outfile: "publico/cliente.js",
  bundle: true,
  format: "iife",
  minify: true,
  target: ["es2020"],
  logLevel: "info",
});
