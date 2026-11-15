// Las aplicaciones que usan el editor y cómo se habla con ellas.
//
// Cada aplicación se da de alta con un nombre, un secreto (para los pases y las firmas) y la dirección
// en la que el editor la llama. Se leen de la variable de entorno EDITOR_APLICACIONES, en JSON:
//   {"asambleas": {"secreto": "…", "url": "http://app:8000/editor"}}
//
// Cada aplicación responde a dos llamadas del editor (las dos firmadas; ver pases.mjs):
//   - GET  <url>/texto/?sala=<sala>  →  {"texto": "…", "version": 3}
//       El texto con el que empieza una sala que el editor aún no tiene (o que la aplicación ha
//       cambiado por su cuenta: su versión ya no coincide).
//   - POST <url>/guardado/  con {"sala", "texto", "alias": [...], "version"}  →  {"version": 4}
//       Lo escrito, cada pocos segundos mientras se escribe, con quién ha escrito desde el último aviso.
//       La aplicación lo guarda (autoría, registro de cambios…) y devuelve su versión nueva. Si responde
//       409, ya no acepta cambios (el texto se ha aprobado): el editor cierra la sala.

import { cabecerasFirmadas } from "./pases.mjs";

// Lee las aplicaciones de la variable de entorno. Sin ella, ninguna (el editor no deja entrar a nadie).
export function leerAplicaciones(texto = process.env.EDITOR_APLICACIONES || "{}") {
  const aplicaciones = JSON.parse(texto);
  for (const [nombre, datos] of Object.entries(aplicaciones)) {
    if (!datos.secreto || !datos.url) throw new Error(`A la aplicación «${nombre}» le falta el secreto o la dirección.`);
  }
  return aplicaciones;
}

// Pide a la aplicación el texto inicial de una sala. Devuelve { texto, version }.
export async function pedirTexto(aplicacion, sala) {
  const direccion = `${aplicacion.url}/texto/?sala=${encodeURIComponent(sala)}`;
  const respuesta = await fetch(direccion, { headers: cabecerasFirmadas(sala, aplicacion.secreto) });
  if (!respuesta.ok) throw new Error(`La aplicación no da el texto de «${sala}» (${respuesta.status}).`);
  return respuesta.json();
}

// Avisa a la aplicación de lo escrito. Devuelve { version } o, si ya no acepta cambios, { cerrada: true }.
export async function avisarGuardado(aplicacion, datos) {
  const cuerpo = JSON.stringify(datos);
  const respuesta = await fetch(`${aplicacion.url}/guardado/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...cabecerasFirmadas(cuerpo, aplicacion.secreto) },
    body: cuerpo,
  });
  if (respuesta.status === 409) return { cerrada: true };
  if (!respuesta.ok) throw new Error(`La aplicación no ha guardado «${datos.sala}» (${respuesta.status}).`);
  return respuesta.json();
}
