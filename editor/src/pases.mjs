// Pases y firmas: cómo se fían el editor y las aplicaciones que lo usan.
//
// - El PASE lo fabrica la aplicación (la plataforma de asambleas u otra) para una persona y un texto
//   concretos: dice quién es (su alias), qué texto (la sala) y qué puede hacer (leer, comentar, escribir).
//   Es un JWT estándar firmado con HS256 con el secreto de esa aplicación, y dura pocos minutos. El
//   navegador lo trae al conectarse; el editor lo comprueba sin preguntar a nadie.
// - Las PETICIONES entre servidores (el editor pide el texto inicial o avisa de lo guardado; la aplicación
//   pide cerrar una sala) llevan una firma HMAC del cuerpo y de la hora, con el mismo secreto. Así nadie
//   puede hacerse pasar por la otra parte ni repetir una petición vieja.
//
// No usa librerías: solo el módulo «crypto» de Node.

import { createHmac, timingSafeEqual } from "node:crypto";

// Permisos posibles dentro de una sala, de menos a más.
export const PERMISOS = ["leer", "comentar", "escribir"];
// Margen, en segundos (5 minutos), para la hora de una petición firmada (relojes algo desajustados).
const MARGEN_DE_HORA = 5 * 60;

// Pasa bytes o texto a base64url (la variante de base64 que va en las direcciones y en los JWT).
function aBase64url(datos) {
  return Buffer.from(datos).toString("base64url");
}

// Calcula la firma HMAC-SHA256 de un texto con un secreto, en base64url (la de los JWT).
function firmar(texto, secreto) {
  return createHmac("sha256", secreto).update(texto).digest("base64url");
}

// Compara dos firmas sin dar pistas por el tiempo que tarda (si fuera más rápido al fallar pronto,
// alguien podría adivinar la firma letra a letra).
function iguales(a, b) {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
}

// Fabrica un pase (JWT HS256). Lo usan las pruebas; en la vida real lo fabrica cada aplicación con su
// propio código (en la plataforma, base/editor.py).
//   - datos: { app, sala, alias, permiso, color, exp } (exp: segundos desde 1970 hasta los que vale).
//   - secreto: el secreto de esa aplicación.
export function crearPase(datos, secreto) {
  const cabecera = aBase64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const cuerpo = aBase64url(JSON.stringify(datos));
  return `${cabecera}.${cuerpo}.${firmar(`${cabecera}.${cuerpo}`, secreto)}`;
}

// Lee y comprueba un pase. Devuelve sus datos o lanza un error que explica qué falla.
//   - pase: el texto del JWT.
//   - aplicaciones: las aplicaciones conocidas ({ nombre: { secreto, url } }; ver aplicaciones.mjs).
//   - ahora: segundos desde 1970 (para las pruebas; por defecto, ahora mismo).
export function leerPase(pase, aplicaciones, ahora = Math.floor(Date.now() / 1000)) {
  const partes = String(pase || "").split(".");
  if (partes.length !== 3) throw new Error("El pase no tiene la forma de un JWT.");
  const [cabecera, cuerpo, firma] = partes;
  let datos;
  try {
    if (JSON.parse(Buffer.from(cabecera, "base64url")).alg !== "HS256") throw new Error();
    datos = JSON.parse(Buffer.from(cuerpo, "base64url"));
  } catch {
    throw new Error("El pase no se puede leer.");
  }
  const aplicacion = aplicaciones[datos.app];
  if (!aplicacion) throw new Error(`No se conoce la aplicación «${datos.app}».`);
  if (!iguales(firma, firmar(`${cabecera}.${cuerpo}`, aplicacion.secreto))) throw new Error("La firma del pase no vale.");
  if (typeof datos.exp !== "number" || datos.exp < ahora) throw new Error("El pase ha caducado.");
  if (!PERMISOS.includes(datos.permiso)) throw new Error("El pase no dice un permiso válido.");
  if (!datos.sala || !datos.alias) throw new Error("Al pase le falta la sala o el alias.");
  return datos;
}

// Nombre interno de una sala: la aplicación y su sala («asambleas/documentos.documento:12»). Así dos
// aplicaciones pueden usar el mismo nombre de sala sin mezclarse.
export function nombreDeSala(app, sala) {
  return `${app}/${sala}`;
}

// Cabeceras de una petición firmada entre servidores.
//   - cuerpo: el texto que se envía (vacío en un GET; entonces se firma la dirección).
//   - secreto: el de la aplicación.
export function cabecerasFirmadas(cuerpo, secreto, ahora = Math.floor(Date.now() / 1000)) {
  return { "X-Editor-Hora": String(ahora), "X-Editor-Firma": firmar(`${ahora}.${cuerpo}`, secreto) };
}

// Comprueba la firma de una petición que llega de una aplicación. Devuelve true o false.
//   - cabeceras: las de la petición (en minúsculas, como las da Node).
//   - cuerpo: el texto recibido.
export function firmaValida(cabeceras, cuerpo, secreto, ahora = Math.floor(Date.now() / 1000)) {
  const hora = Number(cabeceras["x-editor-hora"]);
  const firma = String(cabeceras["x-editor-firma"] || "");
  if (!Number.isFinite(hora) || Math.abs(ahora - hora) > MARGEN_DE_HORA) return false;
  return iguales(firma, firmar(`${hora}.${cuerpo}`, secreto));
}
