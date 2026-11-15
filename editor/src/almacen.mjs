// Dónde guarda el editor su propia copia de cada sala: el estado de Yjs (el texto con su historia, que
// permite unir lo que escriben varias personas a la vez) y la versión de la aplicación con la que va.
// Va en ficheros, un par por sala, dentro de CARPETA_DE_DATOS. Sin base de datos ni librerías nativas:
// si algún día hace falta, se cambia por otra forma de guardar sin tocar el resto.

import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { join } from "node:path";

// Nombre de fichero seguro para una sala (sin barras ni caracteres raros).
function base(carpeta, nombre) {
  return join(carpeta, encodeURIComponent(nombre));
}

// Lee la copia de una sala. Devuelve { estado (Uint8Array), version } o null si no hay.
export async function leer(carpeta, nombre) {
  try {
    const [estado, meta] = await Promise.all([readFile(`${base(carpeta, nombre)}.yjs`), readFile(`${base(carpeta, nombre)}.json`, "utf8")]);
    return { estado: new Uint8Array(estado), version: JSON.parse(meta).version };
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }
}

// Guarda la copia de una sala. Escribe primero en un fichero temporal y después lo renombra, para que un
// corte a mitad no deje un fichero roto.
export async function guardar(carpeta, nombre, estado, version) {
  await mkdir(carpeta, { recursive: true });
  const ruta = base(carpeta, nombre);
  await writeFile(`${ruta}.yjs.tmp`, estado);
  await rename(`${ruta}.yjs.tmp`, `${ruta}.yjs`);
  await writeFile(`${ruta}.json`, JSON.stringify({ version }));
}
