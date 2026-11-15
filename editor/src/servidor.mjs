// Servidor del editor colaborativo en tiempo real.
//
// Varias personas escriben a la vez el mismo texto desde su navegador. Yjs une lo que escribe cada una
// sin pisarse y Hocuspocus (MIT) reparte los cambios por WebSocket. El servidor no conoce a las personas
// ni tiene base de datos de usuarios: se fía de los pases que firma cada aplicación (ver pases.mjs) y le
// devuelve lo escrito (ver aplicaciones.mjs).
//
// Además del WebSocket, responde a unas pocas direcciones HTTP:
//   - GET  /salud                → «bien» (para saber si está en marcha).
//   - GET  /cliente.js           → el editor para el navegador (se construye con «npm run construir»).
//   - POST /salas/cerrar         → echa a todo el mundo de una sala (lo pide la aplicación, firmado, por
//                                  ejemplo al aprobar un acta o al quitarle a alguien el permiso).
//   - GET  /pdf?pase=…           → el PDF del texto con Typst (esqueleto: responde 501 mientras falte).
//
// Se arranca con «npm run arrancar» (o «node src/servidor.mjs»). Variables de entorno:
//   - EDITOR_PUERTO: el puerto (de partida, 1234).
//   - EDITOR_APLICACIONES: las aplicaciones que lo usan, en JSON (ver aplicaciones.mjs).
//   - EDITOR_DATOS: carpeta donde guarda su copia de cada sala (de partida, ./datos).

import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { Hocuspocus } from "@hocuspocus/server";
import * as Y from "yjs";

import { guardar, leer } from "./almacen.mjs";
import { avisarGuardado, leerAplicaciones, pedirTexto } from "./aplicaciones.mjs";
import { firmaValida, leerPase, nombreDeSala } from "./pases.mjs";

// Carpeta del editor (la de package.json).
const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..");
// Nombre del texto compartido dentro de cada documento de Yjs (el cliente usa el mismo).
export const CAMPO = "texto";

// Separa el nombre interno de una sala en su aplicación y su sala («asambleas/documentos.documento:12»).
function partes(nombre) {
  const corte = nombre.indexOf("/");
  return { app: nombre.slice(0, corte), sala: nombre.slice(corte + 1) };
}

// Lee entero el cuerpo de una petición HTTP, como texto.
async function cuerpoDe(peticion) {
  let texto = "";
  for await (const trozo of peticion) texto += trozo;
  return texto;
}

// Responde a una petición HTTP y corta la cadena de Hocuspocus (que, si no, respondería «OK»).
function responder(respuesta, estado, contenido, tipo = "text/plain; charset=utf-8") {
  respuesta.writeHead(estado, { "Content-Type": tipo });
  respuesta.end(contenido);
  throw null; // así lo pide Hocuspocus para decir «ya he respondido yo»
}

// Crea (sin arrancarlo) el servidor del editor. Lo usan este fichero y las pruebas.
//   - aplicaciones: { nombre: { secreto, url } }.
//   - carpeta: dónde guarda su copia de cada sala.
//   - espera, esperaMaxima: milisegundos que espera, tras el último cambio, para avisar a la aplicación
//     (y como mucho, aunque no se deje de escribir).
export function crearServidor({ aplicaciones, carpeta, espera = 2000, esperaMaxima = 10000 }) {
  // Quién ha escrito en cada sala desde el último aviso a la aplicación: nombre de sala → Set de alias.
  const autores = new Map();
  // Versión de la aplicación con la que va cada sala: nombre de sala → número.
  const versiones = new Map();

  const servidor = new Hocuspocus({
    quiet: true,
    debounce: espera,
    maxDebounce: esperaMaxima,

    // Al conectarse alguien: comprueba su pase y que es de esta sala. Si no puede escribir, su conexión es
    // de solo lectura (Hocuspocus descarta lo que intente cambiar). Lo devuelto queda como «context».
    async onAuthenticate({ token, documentName, connection }) {
      const datos = leerPase(token, aplicaciones);
      if (nombreDeSala(datos.app, datos.sala) !== documentName) throw new Error("El pase es de otra sala.");
      connection.readOnly = datos.permiso !== "escribir";
      return { alias: datos.alias, permiso: datos.permiso };
    },

    // Al abrirse una sala que no está en memoria: usa su copia si va con la misma versión que la
    // aplicación; si no (no hay copia, o la aplicación cambió el texto por su cuenta), empieza con el texto
    // de la aplicación. Si la aplicación no responde, sigue con la copia, si la hay.
    async onLoadDocument({ document, documentName }) {
      const { app, sala } = partes(documentName);
      const copia = await leer(carpeta, documentName);
      let remoto = null;
      try {
        remoto = await pedirTexto(aplicaciones[app], sala);
      } catch (error) {
        if (!copia) throw error;
      }
      if (copia && (remoto === null || remoto.version === copia.version)) {
        Y.applyUpdate(document, copia.estado);
        versiones.set(documentName, copia.version);
      } else {
        document.getText(CAMPO).insert(0, remoto.texto || "");
        versiones.set(documentName, remoto.version);
      }
    },

    // Cada cambio: apunta quién lo ha hecho (para la autoría que guarda la aplicación).
    async onChange({ documentName, context }) {
      if (context?.permiso !== "escribir") return;
      if (!autores.has(documentName)) autores.set(documentName, new Set());
      autores.get(documentName).add(context.alias);
    },

    // Unos segundos después de los cambios: avisa a la aplicación con el texto y quién ha escrito, y guarda
    // su propia copia. Si la aplicación ya no acepta cambios, echa a todo el mundo de la sala.
    async onStoreDocument({ document, documentName }) {
      const quienes = autores.get(documentName);
      autores.set(documentName, new Set());
      if (quienes?.size) {
        const { app, sala } = partes(documentName);
        const texto = document.getText(CAMPO).toString();
        const respuesta = await avisarGuardado(aplicaciones[app], { sala, texto, alias: [...quienes], version: versiones.get(documentName) });
        if (respuesta.cerrada) {
          servidor.closeConnections(documentName);
          return;
        }
        versiones.set(documentName, respuesta.version);
      }
      await guardar(carpeta, documentName, Y.encodeStateAsUpdate(document), versiones.get(documentName));
    },

    // Las direcciones HTTP (ver arriba).
    async onRequest({ request, response }) {
      const direccion = new URL(request.url, "http://editor");
      if (request.method === "GET" && direccion.pathname === "/salud") responder(response, 200, "bien");
      if (request.method === "GET" && direccion.pathname === "/cliente.js") {
        const codigo = await readFile(join(RAIZ, "publico", "cliente.js")).catch(() => null);
        if (codigo === null) responder(response, 404, "Falta construir el cliente: npm run construir");
        responder(response, 200, codigo, "text/javascript; charset=utf-8");
      }
      if (request.method === "POST" && direccion.pathname === "/salas/cerrar") {
        const cuerpo = await cuerpoDe(request);
        const app = request.headers["x-editor-app"];
        if (!aplicaciones[app] || !firmaValida(request.headers, cuerpo, aplicaciones[app].secreto)) responder(response, 403, "Firma no válida.");
        servidor.closeConnections(nombreDeSala(app, JSON.parse(cuerpo).sala));
        responder(response, 200, "cerrada");
      }
      if (request.method === "GET" && direccion.pathname === "/pdf") {
        try {
          leerPase(direccion.searchParams.get("pase"), aplicaciones);
        } catch (error) {
          responder(response, 403, error.message);
        }
        // Esqueleto: aquí se compilará el texto con Typst (ver LEEME.md, «PDF con Typst»).
        responder(response, 501, "Aún no: el PDF con Typst está por hacer.");
      }
      responder(response, 404, "No existe.");
    },
  });
  return servidor;
}

// Si se ejecuta este fichero directamente (y no desde las pruebas), arranca el servidor.
if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const puerto = Number(process.env.EDITOR_PUERTO || 1234);
  const servidor = crearServidor({ aplicaciones: leerAplicaciones(), carpeta: process.env.EDITOR_DATOS || join(RAIZ, "datos") });
  await servidor.listen(puerto);
  console.log(`Editor colaborativo en marcha en el puerto ${puerto}.`);
}
