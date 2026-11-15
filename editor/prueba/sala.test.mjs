// Prueba de una sala de verdad: arranca el editor y una aplicación de mentira (un servidor HTTP que da
// el texto inicial y apunta lo guardado). Dos personas se conectan: lo que escribe Lince le llega a
// Nutria, que solo puede leer y cuyos cambios no se aceptan; y a la aplicación le llega el texto con
// quién lo ha escrito.

import assert from "node:assert/strict";
import { mkdtemp } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import { HocuspocusProvider, HocuspocusProviderWebsocket } from "@hocuspocus/provider";
import WebSocket from "ws";

import { crearPase, firmaValida } from "../src/pases.mjs";
import { crearServidor } from "../src/servidor.mjs";

const SECRETO = "secreto-de-prueba";

// Espera hasta que se cumpla una condición (o falla a los 5 segundos).
async function hasta(condicion) {
  for (let intento = 0; intento < 100; intento++) {
    if (condicion()) return;
    await new Promise((listo) => setTimeout(listo, 50));
  }
  throw new Error("No se ha cumplido a tiempo.");
}

// Conecta a una persona a la sala con su permiso. Devuelve su proveedor (ya sincronizado); al acabar se
// cierra con cerrar(proveedor), que cierra también su conexión.
async function conectar(puerto, alias, permiso) {
  const pase = crearPase({ app: "asambleas", sala: "documentos.documento:1", alias, permiso, exp: Math.floor(Date.now() / 1000) + 300 }, SECRETO);
  const socket = new HocuspocusProviderWebsocket({ url: `ws://127.0.0.1:${puerto}`, WebSocketPolyfill: WebSocket });
  const proveedor = new HocuspocusProvider({ websocketProvider: socket, name: "asambleas/documentos.documento:1", token: pase });
  await new Promise((listo) => proveedor.on("synced", listo));
  proveedor.socket = socket;
  return proveedor;
}

// Cierra el proveedor de una persona y su conexión.
function cerrar(proveedor) {
  proveedor.destroy();
  proveedor.socket.destroy();
}

test("dos personas en una sala", async () => {
  const guardados = [];
  // La aplicación de mentira: responde al texto inicial y apunta los guardados (si la firma vale).
  const aplicacion = createServer(async (peticion, respuesta) => {
    let cuerpo = "";
    for await (const trozo of peticion) cuerpo += trozo;
    const firmado = peticion.method === "GET" ? new URL(peticion.url, "http://x").searchParams.get("sala") : cuerpo;
    if (!firmaValida(peticion.headers, firmado, SECRETO)) {
      respuesta.writeHead(403).end();
      return;
    }
    respuesta.writeHead(200, { "Content-Type": "application/json" });
    if (peticion.method === "GET") return respuesta.end(JSON.stringify({ texto: "## Puntos\n", version: 1 }));
    guardados.push(JSON.parse(cuerpo));
    respuesta.end(JSON.stringify({ version: 1 + guardados.length }));
  });
  await new Promise((listo) => aplicacion.listen(0, "127.0.0.1", listo));
  const aplicaciones = { asambleas: { secreto: SECRETO, url: `http://127.0.0.1:${aplicacion.address().port}` } };
  const servidor = crearServidor({ aplicaciones, carpeta: await mkdtemp(join(tmpdir(), "editor-")), espera: 50, esperaMaxima: 200 });
  await servidor.listen(0);
  const puerto = servidor.address.port;
  try {
    const lince = await conectar(puerto, "Lince", "escribir");
    const nutria = await conectar(puerto, "Nutria", "leer");
    assert.equal(nutria.document.getText("texto").toString(), "## Puntos\n");
    lince.document.getText("texto").insert(10, "1. Huerto\n");
    await hasta(() => nutria.document.getText("texto").toString().includes("Huerto"));
    nutria.document.getText("texto").insert(0, "Hola ");
    await hasta(() => guardados.length > 0);
    await new Promise((listo) => setTimeout(listo, 300));
    assert.equal(lince.document.getText("texto").toString(), "## Puntos\n1. Huerto\n");
    assert.deepEqual(guardados.at(-1).alias, ["Lince"]);
    assert.equal(guardados.at(-1).texto, "## Puntos\n1. Huerto\n");
    cerrar(lince);
    cerrar(nutria);
  } finally {
    await servidor.destroy();
    aplicacion.closeAllConnections();
    aplicacion.close();
  }
});
