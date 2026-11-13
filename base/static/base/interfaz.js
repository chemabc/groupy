// Comportamiento común de la interfaz, con Alpine.js: preferencias (tema, letra, densidad), menú
// izquierdo plegable que conserva su posición y marca de la sección actual.
//
// La plantilla general (base/templates/base/pagina.html) carga este fichero ANTES que Alpine, para que
// los componentes estén registrados cuando Alpine arranque.

// Lee un valor guardado en el navegador (localStorage). Si no hay o el navegador no deja leer (modo
// privado estricto), devuelve el valor por defecto. Lo usan los componentes de abajo.
function leerGuardado(clave, porDefecto) {
  try {
    const valor = localStorage.getItem(clave);
    return valor === null ? porDefecto : JSON.parse(valor);
  } catch {
    return porDefecto;
  }
}

// Guarda un valor en el navegador. Si no se puede, no pasa nada: solo se pierde al recargar.
function guardar(clave, valor) {
  try {
    localStorage.setItem(clave, JSON.stringify(valor));
  } catch {
    // Sin almacenamiento disponible: se sigue sin guardar.
  }
}

// Pasa un texto a minúsculas y le quita las tildes y diéresis («Reunión» → «reunion»), igual que
// normalizar() de base/tablas.py, para que buscar no dependa de ellas. La usa el filtro de las tablas.
function normalizar(texto) {
  return texto.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

// Da a un texto la «forma de frase» de las etiquetas, igual que forma_de_frase() de base/tablas.py: sin
// espacios de más, sin tildes ni diéresis (pero conservando la ñ), todo en minúsculas salvo la primera
// letra («  REUNIÓN  general» → «Reunion general»). La usa el selector de palabras con data-forma="frase".
function formaDeFrase(texto) {
  const minusculas = texto
    .trim()
    .replace(/\s+/g, " ")
    .normalize("NFD")
    .replace(/([nN])\u0303/g, "$1\u0000")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/\u0000/g, "\u0303")
    .normalize("NFC")
    .toLowerCase();
  return minusculas.charAt(0).toUpperCase() + minusculas.slice(1);
}

// Copia un texto al portapapeles con el método antiguo (un cuadro de texto oculto y la orden «copy»).
// Hace falta cuando el navegador no deja usar el portapapeles moderno: por ejemplo, si se entra por la
// dirección de la red local sin https. La usa el componente «copiar».
function copiarALaAntigua(texto) {
  const cuadro = document.createElement("textarea");
  cuadro.value = texto;
  cuadro.style.position = "fixed";
  cuadro.style.opacity = "0";
  document.body.appendChild(cuadro);
  cuadro.select();
  document.execCommand("copy");
  cuadro.remove();
}

// Alpine lanza «alpine:init» justo antes de arrancar: es el momento de registrar almacenes y componentes.
document.addEventListener("alpine:init", () => {
  // Almacén de preferencias de presentación. Las aplica como atributos de <html> (data-tema,
  // data-letra, data-densidad), que la hoja de estilos usa para cambiar colores, tamaño y espacios.
  // El script del <head> ya las aplicó al cargar; aquí se leen de nuevo para poder cambiarlas.
  // Se guardan en el navegador y, si hay sesión, también en la cuenta (usuarios/views.py,
  // guardar_preferencia), para que sigan a la persona en cualquier dispositivo.
  Alpine.store("preferencias", {
    tema: document.documentElement.dataset.tema,
    letra: document.documentElement.dataset.letra,
    densidad: document.documentElement.dataset.densidad,

    // Cambia una preferencia, la aplica a la página y la guarda en el navegador y en la cuenta.
    //   - clave: «tema», «letra» o «densidad».
    //   - valor: por ejemplo «oscuro», «grande» o «compacta».
    poner(clave, valor) {
      this[clave] = valor;
      document.documentElement.dataset[clave] = valor;
      guardar(clave, valor);
      this.guardarEnLaCuenta(clave, valor);
    },

    // Manda la preferencia al servidor para guardarla en la cuenta. Solo si hay sesión: entonces <html>
    // lleva la dirección en data-guardar-preferencias (ver base/templates/base/cabeza.html). Si falla
    // (por ejemplo, sin conexión), el cambio sigue aplicado y guardado en este navegador.
    guardarEnLaCuenta(clave, valor) {
      const direccion = document.documentElement.dataset.guardarPreferencias;
      if (!direccion) return;
      const claveCsrf = document.querySelector('meta[name="csrf-token"]').content;
      fetch(direccion, {
        method: "POST",
        headers: { "X-CSRFToken": claveCsrf },
        body: new URLSearchParams({ clave, valor }),
      }).catch(() => {});
    },

    // Pasa al tema siguiente: claro → día (claro con más contraste) → oscuro → claro… Lo usa el botón
    // del tema de la cabecera.
    siguienteTema() {
      const orden = ["claro", "dia", "oscuro"];
      const siguiente = orden[(orden.indexOf(this.tema) + 1) % orden.length];
      this.poner("tema", siguiente);
    },

    // Icono del botón del tema según el tema actual: ☀ claro, ◐ día, ☾ oscuro.
    iconoDelTema() {
      return { claro: "☀", dia: "◐", oscuro: "☾" }[this.tema] || "☀";
    },
  });

  // Almacén con los códigos de la sección actual y de las que la contienen. Lo rellena la zona
  // central cada vez que se pinta (también tras navegar con htmx) y el menú lo lee para marcarlas.
  Alpine.store("navegacion", { secciones: [] });

  // Componente del menú izquierdo: si está plegado, qué secciones tienen abiertas sus subsecciones y
  // hasta dónde se había bajado. Todo se guarda en el navegador para que el menú no salte al recargar.
  // El plegado se aplica como atributo data-menu de <html> («plegado» o «desplegado»): la hoja de estilos
  // cambia con él la anchura del menú y oculta sus textos (variante «plegado:»), y el script del <head>
  // lo aplica antes de pintar.
  Alpine.data("menuLateral", () => ({
    abiertas: leerGuardado("menu.abiertas", []),

    // Al arrancar, vuelve a bajar el menú hasta donde estaba.
    init() {
      this.$el.scrollTop = leerGuardado("menu.desplazamiento", 0);
    },

    // Pliega o despliega el menú entero. Lo usa el botón ☰ de la cabecera.
    alternarPlegado() {
      const plegado = document.documentElement.dataset.menu !== "plegado";
      document.documentElement.dataset.menu = plegado ? "plegado" : "desplegado";
      guardar("menu.plegado", plegado);
    },

    // Dice si las subsecciones de una sección se ven: si se abrieron a mano o si se está dentro de ella
    // (así, al entrar en una subsección, su sección aparece abierta aunque no se hubiera abierto).
    //   - codigo: código de la sección.
    estaAbierta(codigo) {
      return this.abiertas.includes(codigo) || Alpine.store("navegacion").secciones.includes(codigo);
    },

    // Abre o cierra las subsecciones de una sección.
    //   - codigo: código de la sección, como «grupos.organizaciones».
    alternarSeccion(codigo) {
      this.abiertas = this.abiertas.includes(codigo)
        ? this.abiertas.filter((abierta) => abierta !== codigo)
        : [...this.abiertas, codigo];
      guardar("menu.abiertas", this.abiertas);
    },

    // Apunta hasta dónde se ha bajado en el menú. Se llama al desplazarlo.
    apuntarDesplazamiento() {
      guardar("menu.desplazamiento", this.$el.scrollTop);
    },
  }));

  // Componente de una tabla filtrable que se filtra en el navegador (hasta 500 filas; ver
  // base/tablas.py y base/templates/base/tabla.html). Filtra y ordena las filas que ya están en la
  // página, sin peticiones, y apunta los filtros en la dirección para que sobrevivan a una recarga.
  //
  // Ojo: dentro de sus funciones se usa this.$root (la raíz del componente, el bloque de la tabla) y no
  // this.$el, porque $el es el elemento donde ha ocurrido la acción (el cuadro en el que se escribe, el
  // botón de la columna…), y desde ahí no se encuentran las filas.
  Alpine.data("tablaLocal", () => ({
    total: 0,
    visibles: 0,

    // Al arrancar: reúne las filas y aplica los filtros que vengan en la dirección.
    init() {
      this.filas = [...this.$root.querySelectorAll("tbody tr[data-texto]")];
      this.total = this.filas.length;
      this.filtrar();
    },

    // Pares [nombre, valor] de todos los campos de la tabla (buscador, desplegables, filtros de columna
    // y orden).
    parametros() {
      return [...this.$root.querySelectorAll("[name]")].map((campo) => [campo.name, campo.value]);
    },

    // Oculta las filas que no cumplen todos los filtros:
    //   - el buscador general: todas las palabras deben estar en el texto de búsqueda de la fila;
    //   - los desplegables: la categoría de la fila debe ser la elegida;
    //   - los filtros de columna: el texto de la celda debe contener lo escrito.
    // Nunca importan las tildes ni las mayúsculas. Se llama al escribir o al cambiar un desplegable.
    filtrar() {
      const identificador = this.$root.dataset.identificador;
      const valores = Object.fromEntries(this.parametros());
      const palabras = normalizar(valores[`${identificador}-q`] || "").split(/\s+/).filter(Boolean);
      const categorias = [...this.$root.querySelectorAll("select[data-campo]")]
        .filter((desplegable) => desplegable.value)
        .map((desplegable) => [desplegable.dataset.campo, desplegable.value]);
      const porColumna = [...this.$root.querySelectorAll("thead input[data-indice]")]
        .filter((cuadro) => cuadro.value.trim())
        .map((cuadro) => [Number(cuadro.dataset.indice), normalizar(cuadro.value.trim())]);
      let visibles = 0;
      for (const fila of this.filas) {
        const coincide =
          palabras.every((palabra) => fila.dataset.texto.includes(palabra)) &&
          categorias.every(([campo, valor]) => fila.getAttribute(`data-filtro-${campo}`) === valor) &&
          porColumna.every(([indice, texto]) => normalizar(fila.cells[indice].textContent).includes(texto));
        fila.hidden = !coincide;
        if (coincide) visibles += 1;
      }
      this.visibles = visibles;
      this.actualizarDireccion();
    },

    // Ordena las filas por una columna: la primera vez, ascendente; si ya lo estaba, descendente.
    // Compara los valores de data-valor como lo haría una persona («2» antes que «10», sin mirar tildes).
    //   - boton: el botón del título de la columna, con data-indice y data-campo.
    ordenar(boton) {
      const indice = Number(boton.dataset.indice);
      const campo = boton.dataset.campo;
      const descendente = this.$refs.orden.value === campo;
      this.$refs.orden.value = descendente ? `-${campo}` : campo;
      const colador = new Intl.Collator("es", { numeric: true, sensitivity: "base" });
      const signo = descendente ? -1 : 1;
      this.filas.sort((a, b) => signo * colador.compare(a.cells[indice].dataset.valor, b.cells[indice].dataset.valor));
      // Volver a añadir cada fila al final del cuerpo de la tabla las deja en el orden nuevo.
      const cuerpo = this.$root.querySelector("tbody");
      for (const fila of this.filas) cuerpo.appendChild(fila);
      for (const flecha of this.$root.querySelectorAll("[data-flecha]")) flecha.textContent = "";
      boton.querySelector("[data-flecha]").textContent = descendente ? "▼" : "▲";
      this.actualizarDireccion();
    },

    // Texto del recuento bajo la tabla.
    recuento() {
      return this.visibles === this.total ? `${this.total} filas` : `${this.visibles} de ${this.total} filas`;
    },

    // Escribe los filtros en la dirección sin recargar (history.replaceState), para que se puedan
    // compartir y sigan ahí al recargar. Los vacíos se quitan.
    actualizarDireccion() {
      const direccion = new URL(window.location.href);
      for (const [nombre, valor] of this.parametros()) {
        if (valor) direccion.searchParams.set(nombre, valor);
        else direccion.searchParams.delete(nombre);
      }
      history.replaceState(history.state, "", direccion);
    },
  }));

  // Componente de una lista que se ordena arrastrando sus elementos por el asa (⠿), con SortableJS. Al
  // soltar, manda el orden nuevo al servidor: {tipologia, orden: [ids]} a la dirección de data-url, con
  // la clave CSRF. Cada elemento lleva su id en data-id. Si no hay asas (no se puede editar), no hace nada.
  // Lo usa la pantalla de tipologías (tipologias/templates/tipologias/tipologias.html).
  Alpine.data("listaOrdenable", () => ({
    // Al arrancar: prepara SortableJS sobre la lista. forceFallback: arrastra con el ratón «a mano» en
    // lugar del arrastre nativo del navegador, que se comporta distinto en cada uno.
    init() {
      if (!this.$root.querySelector(".asa") || typeof Sortable === "undefined") return;
      Sortable.create(this.$root, {
        handle: ".asa",
        animation: 150,
        forceFallback: true,
        onEnd: () => this.guardar(),
      });
    },

    // Manda al servidor el orden actual de los elementos. Si no se puede guardar (sin conexión, sin
    // permiso…), lo avisa y recarga la página, para no dejar a la vista un orden que no se ha guardado.
    async guardar() {
      const orden = [...this.$root.querySelectorAll("[data-id]")].map((elemento) => elemento.dataset.id);
      let guardado = false;
      try {
        const respuesta = await fetch(this.$root.dataset.url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content,
          },
          body: JSON.stringify({ tipologia: this.$root.dataset.tipologia, orden }),
        });
        guardado = respuesta.ok;
      } catch {
        guardado = false;
      }
      if (!guardado) {
        alert("No se ha podido guardar el nuevo orden. Se vuelve a cargar la página.");
        window.location.reload();
      }
    },
  }));

  // Componente del selector de varias palabras (etiquetas…) con sugerencias: base/formularios.py,
  // SelectorDePalabras, y su plantilla base/templates/base/selector_de_palabras.html. Guarda las palabras
  // elegidas, pide sugerencias al servidor mientras se escribe y no deja repetir ninguna (sin contar
  // mayúsculas ni tildes). Cada palabra se envía en un campo oculto que pinta la plantilla.
  Alpine.data("selectorDePalabras", () => ({
    palabras: [],
    texto: "",
    sugerencias: [],
    nombre: "",

    // Al arrancar: las palabras que ya tenía el campo y el nombre de los campos ocultos.
    init() {
      this.palabras = JSON.parse(this.$root.dataset.valores || "[]");
      this.nombre = this.$root.dataset.nombre;
    },

    // Dice si una palabra ya está elegida.
    tiene(palabra) {
      return this.palabras.some((elegida) => normalizar(elegida) === normalizar(palabra));
    },

    // Pide al servidor las sugerencias para lo escrito y quita las ya elegidas. Si falla, no sugiere nada.
    async buscar() {
      const texto = this.texto.trim();
      const direccion = this.$root.dataset.url;
      if (!texto || !direccion) {
        this.sugerencias = [];
        return;
      }
      try {
        const separador = direccion.includes("?") ? "&" : "?";
        const respuesta = await fetch(`${direccion}${separador}q=${encodeURIComponent(texto)}`);
        const datos = await respuesta.json();
        this.sugerencias = datos.sugerencias.filter((sugerencia) => !this.tiene(sugerencia.nombre));
      } catch {
        this.sugerencias = [];
      }
    },

    // Añade una palabra (la escrita o una sugerencia), limpia de comas y espacios de más, si no está ya.
    // Si el selector lleva data-forma="frase" (las etiquetas), la pasa a esa forma al añadirla, para
    // que se vea ya tal como se guardará.
    anadir(palabra) {
      let limpia = palabra.replace(/,/g, " ").trim().replace(/\s+/g, " ");
      if (limpia && this.$root.dataset.forma === "frase") limpia = formaDeFrase(limpia);
      if (limpia && !this.tiene(limpia)) this.palabras.push(limpia);
      this.texto = "";
      this.sugerencias = [];
    },

    // Quita la palabra de esa posición (la × de su pastilla).
    quitar(indice) {
      this.palabras.splice(indice, 1);
    },

    // Con el cuadro vacío, la tecla de borrar quita la última palabra.
    borrarUltima() {
      if (!this.texto && this.palabras.length) this.palabras.pop();
    },
  }));

  // Componente del botón «copiar» que acompaña a cada campo de formulario (base/templates/base/campo.html).
  // Copia el valor del campo (en un desplegable, el texto de la opción elegida) para pegarlo en otro sitio,
  // y durante un momento muestra ✓.
  Alpine.data("copiar", () => ({
    copiado: false,

    // Copia el valor del campo cuyo id está en data-objetivo.
    async copiar() {
      const campo = document.getElementById(this.$el.dataset.objetivo);
      if (!campo) return;
      const texto =
        campo.tagName === "SELECT" ? [...campo.selectedOptions].map((opcion) => opcion.text).join(", ") : campo.value;
      try {
        await navigator.clipboard.writeText(texto);
      } catch {
        copiarALaAntigua(texto);
      }
      this.copiado = true;
      setTimeout(() => (this.copiado = false), 1500);
    },
  }));
  // Isla de mapa (Leaflet), para los mapas de la aplicación (de momento, el de lugares). Se usa así:
  //   <div x-data="mapa" data-estaticos="/static/generado/leaflet/" data-puntos="id-del-json">
  //     <div x-ref="lienzo" class="h-96"></div>
  //   </div>
  // donde «id-del-json» es un <script type="application/json"> (json_script de Django) con una lista de
  // puntos {lat, lon, titulo, texto, personas, enlace}. Leaflet no se carga en todas las páginas: lo pide
  // este componente la primera vez que hace falta. Las chinchetas cercanas se agrupan (Leaflet.markercluster).
  Alpine.data("mapa", () => ({
    // El mapa de Leaflet, para poder quitarlo al salir de la página.
    mapa: null,

    // Al arrancar: carga Leaflet (si aún no estaba), pinta el mapa con las teselas de OpenStreetMap y pone
    // una chincheta por punto, con una ventanita que muestra sus datos y un enlace.
    async init() {
      const base = this.$root.dataset.estaticos;
      for (const fichero of ["leaflet.css", "MarkerCluster.css", "MarkerCluster.Default.css", "leaflet.js", "leaflet.markercluster.js"]) {
        await cargarUnaVez(base + fichero);
      }
      const puntos = JSON.parse(document.getElementById(this.$root.dataset.puntos).textContent);
      this.mapa = L.map(this.$refs.lienzo);
      // Teselas de OpenStreetMap: piden enviar la página de origen (referrerPolicy) y la atribución.
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        referrerPolicy: "strict-origin-when-cross-origin",
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">colaboradores de OpenStreetMap</a>',
      }).addTo(this.mapa);
      const chinchetas = L.markerClusterGroup();
      for (const punto of puntos) {
        chinchetas.addLayer(L.marker([punto.lat, punto.lon], { title: punto.titulo }).bindPopup(ventanita(punto)));
      }
      this.mapa.addLayer(chinchetas);
      if (puntos.length) {
        this.mapa.fitBounds(chinchetas.getBounds(), { padding: [30, 30], maxZoom: 15 });
      } else {
        this.mapa.setView([40.4, -3.7], 6);
      }
    },

    // Al quitar el componente (al navegar a otra página): libera el mapa.
    destroy() {
      if (this.mapa) this.mapa.remove();
    },
  }));
});

// Ficheros (scripts u hojas de estilo) ya pedidos, para no cargarlos dos veces: {dirección: promesa}.
const ficherosCargados = {};

// Carga un script o una hoja de estilos (por su terminación) y devuelve una promesa que se cumple cuando
// está listo. Si ya se pidió antes, devuelve la misma promesa. La usa el componente «mapa».
//   - direccion: la dirección del fichero.
function cargarUnaVez(direccion) {
  if (!ficherosCargados[direccion]) {
    ficherosCargados[direccion] = new Promise((resolver, fallar) => {
      const esEstilo = direccion.endsWith(".css");
      const elemento = document.createElement(esEstilo ? "link" : "script");
      if (esEstilo) {
        elemento.rel = "stylesheet";
        elemento.href = direccion;
      } else {
        elemento.src = direccion;
      }
      elemento.onload = resolver;
      elemento.onerror = () => fallar(new Error(`No se ha podido cargar ${direccion}`));
      document.head.appendChild(elemento);
    });
  }
  return ficherosCargados[direccion];
}

// Contenido de la ventanita de una chincheta: título (enlace a su ficha), texto y número de personas.
// Se construye con elementos y textContent (no con HTML escrito a mano), para que un nombre con «<» no
// pueda colar código en la página.
//   - punto: {titulo, texto, personas, enlace}.
function ventanita(punto) {
  const caja = document.createElement("div");
  const titulo = document.createElement(punto.enlace ? "a" : "strong");
  titulo.textContent = punto.titulo;
  if (punto.enlace) titulo.href = punto.enlace;
  titulo.className = "font-semibold";
  caja.appendChild(titulo);
  if (punto.texto) {
    const texto = document.createElement("div");
    texto.textContent = punto.texto;
    caja.appendChild(texto);
  }
  if (punto.personas) {
    const personas = document.createElement("div");
    personas.textContent = `${punto.personas} personas`;
    caja.appendChild(personas);
  }
  return caja;
}
