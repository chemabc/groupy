// El editor en el navegador: un cuadro de texto (CodeMirror) unido a una sala del servidor. Lo que escribe
// cada persona llega a las demás al momento, con su cursor y su nombre en color. Se construye con «npm run
// construir» en publico/cliente.js y el servidor lo sirve en /cliente.js.
//
// Sin colores de Markdown a propósito: pesan el doble (traen HTML, CSS y JavaScript) y la vista previa ya
// enseña cómo queda.
//
// Cualquier aplicación lo usa igual: carga /cliente.js y llama a
//   EditorColaborativo.montar(elemento, { url, sala, pase, alias, color, permiso, alCambiar, alPersonas, alEstado })
// (ver LEEME.md). Si no puede escribir, el cuadro es de solo lectura.

import { EditorState } from "@codemirror/state";
import { HocuspocusProvider } from "@hocuspocus/provider";
import { EditorView, minimalSetup } from "codemirror";
import { yCollab } from "y-codemirror.next";

// Monta el editor dentro de un elemento de la página. Devuelve { vista, proveedor, destruir }.
//   - url: dirección WebSocket del servidor («ws://localhost:1234»).
//   - sala: nombre completo de la sala («asambleas/documentos.documento:12»).
//   - pase: el pase firmado, o una función que devuelve uno nuevo (se llama al reconectar, porque los
//     pases duran pocos minutos).
//   - alias, color: cómo se ve a esta persona en los cursores de las demás.
//   - permiso: «leer», «comentar» o «escribir».
//   - alCambiar(texto): se llama con el texto entero cada vez que cambia (para la vista previa).
//   - alPersonas(lista): se llama con quién está en la sala ([{ name, color }]).
//   - alEstado(estado): «connecting», «connected» o «disconnected».
function montar(elemento, opciones) {
  const { url, sala, pase, alias, color = "#7c3aed", permiso = "leer", alCambiar, alPersonas, alEstado } = opciones;
  const proveedor = new HocuspocusProvider({ url, name: sala, token: pase });
  const texto = proveedor.document.getText("texto");
  proveedor.awareness.setLocalStateField("user", { name: alias, color, colorLight: `${color}33` });
  const vista = new EditorView({
    parent: elemento,
    state: EditorState.create({
      doc: texto.toString(),
      extensions: [
        minimalSetup,
        EditorView.lineWrapping,
        yCollab(texto, proveedor.awareness),
        EditorState.readOnly.of(permiso !== "escribir"),
        EditorView.updateListener.of((cambio) => cambio.docChanged && alCambiar?.(cambio.state.doc.toString())),
      ],
    }),
  });
  // Al terminar de recibir el texto del servidor, se avisa una vez (para la primera vista previa).
  proveedor.on("synced", () => alCambiar?.(texto.toString()));
  proveedor.on("status", ({ status }) => alEstado?.(status));
  proveedor.awareness.on("change", () => alPersonas?.([...proveedor.awareness.getStates().values()].map((estado) => estado.user).filter(Boolean)));
  return {
    vista,
    proveedor,
    // Desconecta y quita el editor de la página (al salir de la pantalla).
    destruir() {
      proveedor.destroy();
      vista.destroy();
    },
  };
}

window.EditorColaborativo = { montar };
