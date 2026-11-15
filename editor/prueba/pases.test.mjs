// Pruebas de los pases y las firmas (src/pases.mjs): un pase bueno se lee; uno con otra firma, caducado o
// de una aplicación desconocida, no; y las peticiones firmadas solo valen con el secreto y a su hora.

import assert from "node:assert/strict";
import { test } from "node:test";

import { cabecerasFirmadas, crearPase, firmaValida, leerPase } from "../src/pases.mjs";

const APLICACIONES = { asambleas: { secreto: "secreto-de-prueba", url: "http://x" } };
const AHORA = 1_800_000_000;
const DATOS = { app: "asambleas", sala: "documentos.documento:1", alias: "Lince", permiso: "escribir", exp: AHORA + 300 };

// Un pase bien firmado y a tiempo se lee con sus datos.
test("un pase bueno se lee", () => {
  assert.equal(leerPase(crearPase(DATOS, "secreto-de-prueba"), APLICACIONES, AHORA).alias, "Lince");
});

// Con otro secreto, caducado, de otra aplicación o con un permiso inventado, no.
test("los pases malos no se leen", () => {
  assert.throws(() => leerPase(crearPase(DATOS, "otro"), APLICACIONES, AHORA), /firma/);
  assert.throws(() => leerPase(crearPase(DATOS, "secreto-de-prueba"), APLICACIONES, AHORA + 301), /caducado/);
  assert.throws(() => leerPase(crearPase({ ...DATOS, app: "otra" }, "secreto-de-prueba"), APLICACIONES, AHORA), /aplicación/);
  assert.throws(() => leerPase(crearPase({ ...DATOS, permiso: "todo" }, "secreto-de-prueba"), APLICACIONES, AHORA), /permiso/);
  assert.throws(() => leerPase("basura", APLICACIONES, AHORA), /forma/);
});

// Una petición firmada vale con su cuerpo, su secreto y a su hora; cambiando cualquiera, no.
test("las peticiones firmadas", () => {
  const cabeceras = Object.fromEntries(Object.entries(cabecerasFirmadas("{}", "s", AHORA)).map(([k, v]) => [k.toLowerCase(), v]));
  assert.ok(firmaValida(cabeceras, "{}", "s", AHORA + 10));
  assert.ok(!firmaValida(cabeceras, "{ }", "s", AHORA));
  assert.ok(!firmaValida(cabeceras, "{}", "otro", AHORA));
  assert.ok(!firmaValida(cabeceras, "{}", "s", AHORA + 3600));
});
