// Comportamiento común de la interfaz, con Alpine.js: preferencias (tema, letra, densidad), menú
// izquierdo plegable que conserva su posición, marca de la sección actual y panel de ayuda de la derecha.
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

  // Componente del panel de ayuda de la derecha (base/templates/base/pagina.html). Abre páginas de ayuda
  // sin dejar la pantalla en la que se está: como está fuera de la zona central, navegar con el menú no lo
  // toca ni lo vuelve a pintar. Recuerda en el navegador si está abierto, qué página tenía y su ancho, y
  // así sigue igual al recargar (el script de la cabecera ya lo aplica antes de pintar).
  //   - Se abre con el evento «abrir-ayuda» ({ direccion }), que lanza el menú del botón «?» rojo de la
  //     cabecera (el «?» gris de cada sección no: abre su miniayuda en una ventana emergente). Pide la
  //     página con htmx al propio panel, y el servidor la manda con base/panel.html (sin cabecera de
  //     sección ni menús).
  //   - Los enlaces que se pulsan dentro: las anclas («#titulo») bajan hasta el título dentro del panel;
  //     las páginas de la ayuda (data-direcciones) se abren en el panel; las demás, y las que llevan
  //     data-fuera-del-panel, siguen su camino normal (htmx las lleva a la zona principal).
  //   - El ancho es la variable de CSS --ancho-del-panel de <html>: se cambia arrastrando la línea de
  //     separación (o con las flechas del teclado sobre ella) y vuelve al de partida con doble clic.
  //   - Los botones − y + cambian el tamaño de la letra del panel (solo del panel), y se recuerda.
  Alpine.data("panelDeAyuda", () => ({
    // Dirección de la página que se ve en el panel (con su «#ancla», si la tiene).
    direccion: "",
    // Si se está arrastrando la línea de separación.
    arrastrando: false,
    // Tamaño de la letra del panel: 1 es el normal; 1.2, un 20 % más grande. Se aplica con «zoom».
    letra: leerGuardado("ayuda.letra", 1),

    // Al arrancar: si se dejó abierto, vuelve a cargar la página que tenía.
    init() {
      this.direcciones = (this.$root.dataset.direcciones || "").split(" ").filter(Boolean);
      const guardado = leerGuardado("ayuda.panel", {}) || {};
      if (guardado.abierto && guardado.direccion) this.abrir(guardado.direccion);
    },

    // Abre el panel (si estaba cerrado) con una página. Si la dirección lleva «#ancla», baja hasta ella.
    //   - direccion: por ejemplo «/ayuda/tutorial/» o «/ayuda/tutorial/#htmx».
    async abrir(direccion) {
      this.direccion = direccion;
      document.documentElement.dataset.panelDeAyuda = "abierto";
      guardar("ayuda.panel", { abierto: true, direccion });
      const contenido = this.$refs.contenido;
      await htmxListo();
      await htmx.ajax("GET", direccion.split("#")[0], { target: contenido, swap: "innerHTML" });
      const ancla = direccion.split("#")[1];
      if (ancla) this.bajarHasta(ancla);
      else this.$refs.desplazable.scrollTop = 0;
    },

    // Cierra el panel. La zona principal vuelve a ocupar todo el ancho.
    cerrar() {
      document.documentElement.dataset.panelDeAyuda = "cerrado";
      guardar("ayuda.panel", { abierto: false, direccion: this.direccion });
    },

    // Baja, dentro del panel, hasta el elemento con ese id (un título del documento). Se busca dentro
    // del panel porque la zona principal puede tener el mismo documento, con los mismos ids.
    //   - ancla: el id, sin «#».
    bajarHasta(ancla) {
      const destino = this.$refs.contenido.querySelector(`[id="${CSS.escape(decodeURIComponent(ancla))}"]`);
      if (destino) destino.scrollIntoView({ block: "start" });
    },

    // Decide qué hacer con un clic dentro del panel (se escucha «en captura», antes de que llegue al
    // enlace y htmx lo siga). Ver la explicación del componente.
    //   - evento: el clic.
    alPulsar(evento) {
      const enlace = evento.target.closest("a[href]");
      if (!enlace || !this.$refs.contenido.contains(enlace)) return;
      if (evento.button !== 0 || evento.ctrlKey || evento.metaKey || evento.shiftKey || enlace.target === "_blank") return;
      if (enlace.hasAttribute("data-fuera-del-panel")) return;
      const escrito = enlace.getAttribute("href");
      if (escrito.startsWith("#")) {
        evento.preventDefault();
        evento.stopPropagation();
        this.bajarHasta(escrito.slice(1));
        return;
      }
      const destino = new URL(enlace.href, window.location.href);
      if (destino.origin !== window.location.origin || !this.direcciones.includes(destino.pathname)) return;
      evento.preventDefault();
      evento.stopPropagation();
      this.abrir(destino.pathname + destino.hash);
    },

    // Agranda o achica la letra del panel un paso (de TAMANOS_DE_LETRA_DEL_PANEL) y lo guarda. La usan los
    // botones + y −.
    //   - pasos: 1 para agrandar, -1 para achicar.
    cambiarLetra(pasos) {
      const actual = TAMANOS_DE_LETRA_DEL_PANEL.indexOf(this.letra);
      const posicion = Math.min(Math.max((actual === -1 ? TAMANOS_DE_LETRA_DEL_PANEL.indexOf(1) : actual) + pasos, 0), TAMANOS_DE_LETRA_DEL_PANEL.length - 1);
      this.letra = TAMANOS_DE_LETRA_DEL_PANEL[posicion];
      guardar("ayuda.letra", this.letra);
    },

    // Si se puede achicar más la letra (para desactivar el botón −).
    sePuedeAchicar() {
      return this.letra > TAMANOS_DE_LETRA_DEL_PANEL[0];
    },

    // Si se puede agrandar más la letra (para desactivar el botón +).
    sePuedeAgrandar() {
      return this.letra < TAMANOS_DE_LETRA_DEL_PANEL.at(-1);
    },

    // Empieza a arrastrar la línea de separación: desde ahora, el ratón (o el dedo) mueve la línea aunque
    // salga de ella (setPointerCapture), y no se selecciona texto al arrastrar.
    //   - evento: el «pointerdown» sobre la línea.
    empezarAArrastrar(evento) {
      if (evento.button !== 0) return;
      this.arrastrando = true;
      evento.target.setPointerCapture(evento.pointerId);
      document.body.style.userSelect = "none";
    },

    // Mientras se arrastra: el panel ocupa desde la línea hasta el borde derecho de la ventana.
    //   - evento: el «pointermove».
    arrastrar(evento) {
      if (this.arrastrando) this.ponerAncho(window.innerWidth - evento.clientX);
    },

    // Al soltar: deja de arrastrar y guarda el ancho.
    soltar(evento) {
      if (!this.arrastrando) return;
      this.arrastrando = false;
      evento.target.releasePointerCapture(evento.pointerId);
      document.body.style.userSelect = "";
      guardar("ayuda.ancho", this.anchoActual());
    },

    // Ensancha (o estrecha, con un número negativo) el panel unos píxeles y lo guarda. Lo usan las flechas.
    //   - pixeles: cuánto.
    ensanchar(pixeles) {
      this.ponerAncho(this.anchoActual() + pixeles);
      guardar("ayuda.ancho", this.anchoActual());
    },

    // Vuelve al ancho de partida (doble clic en la línea) y olvida el guardado.
    anchoDePartida() {
      this.ponerAncho(anchoDePartidaDelPanel());
      guardar("ayuda.ancho", 0);
    },

    // Ancho actual del panel, en píxeles (el de la variable --ancho-del-panel).
    anchoActual() {
      return parseInt(getComputedStyle(document.documentElement).getPropertyValue("--ancho-del-panel"), 10) || anchoDePartidaDelPanel();
    },

    // Pone el ancho del panel, sin pasar de unos límites: al menos 260 píxeles y dejando al menos 320
    // para el resto de la pantalla.
    //   - pixeles: el ancho pedido.
    ponerAncho(pixeles) {
      const ancho = Math.round(Math.min(Math.max(pixeles, 260), window.innerWidth - 320));
      document.documentElement.style.setProperty("--ancho-del-panel", `${ancho}px`);
    },
  }));

  // Componente del índice de un documento de la ayuda (ayuda/templates/ayuda/documento.html): lo pliega y
  // lo despliega con su botón, y recuerda en el navegador cómo se dejó. En el panel de ayuda (estrecho) se
  // recuerda aparte y, de entrada, sale plegado; en la zona principal, desplegado.
  Alpine.data("indice", () => ({
    plegado: false,

    // Al arrancar: mira si está en el panel y lee cómo se dejó.
    init() {
      const enElPanel = Boolean(this.$root.closest("#panel-de-ayuda"));
      this.clave = enElPanel ? "indice.plegado.panel" : "indice.plegado";
      this.plegado = leerGuardado(this.clave, enElPanel);
    },

    // Pliega o despliega el índice y lo guarda.
    alternar() {
      this.plegado = !this.plegado;
      guardar(this.clave, this.plegado);
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
  // Componente del selector de personas (base/templates/base/selector_de_personas.html; ver
  // SelectorDePersonas en base/formularios.py). Guarda los alias elegidos (uno o varios) y, al abrir la
  // ventana, pide la lista de quienes ven aquello (JSON de audiencias/cercania.py) en bloques por cercanía.
  // La lista se pide la primera vez que se abre y otra vez si cambia algún campo del formulario del que
  // depende (data-parametros, por ejemplo «visibilidad»). El buscador filtra sin peticiones.
  Alpine.data("selectorDePersonas", () => ({
    // Alias elegidos.
    elegidas: [],
    // Nombre de los campos ocultos (el del campo del formulario).
    nombre: "",
    // Si se pueden elegir varias personas o solo una.
    varias: false,
    // Si la ventana está abierta.
    abierta: false,
    // La lista recibida: bloques por cercanía, y si se puede ver (si no, solo se escribe el alias).
    bloques: [],
    veLaLista: true,
    // Estado de la petición.
    cargando: false,
    error: "",
    // Dirección (con sus parámetros) de la última lista pedida, para no pedirla dos veces.
    pedida: "",
    // Lo escrito en el buscador y en el cuadro del alias exacto.
    texto: "",
    aliasEscrito: "",
    // Posiciones de los bloques que se han abierto o cerrado a mano: {posición: abierto}.
    plegado: {},

    // Al arrancar: lo que ya tenía el campo.
    init() {
      this.elegidas = JSON.parse(this.$root.dataset.valores || "[]");
      this.nombre = this.$root.dataset.nombre;
      this.varias = this.$root.dataset.varias === "1";
    },

    // Abre la ventana, pide la lista si hace falta y pone el cursor en el buscador.
    async abrir() {
      this.abierta = true;
      this.texto = "";
      const direccion = this.direccion();
      if (direccion !== this.pedida) await this.cargar(direccion);
      this.$nextTick(() => (this.$refs.buscador || this.$refs.alias)?.focus());
    },

    // Cierra la ventana.
    cerrar() {
      this.abierta = false;
    },

    // Dirección de la lista, con el valor actual de los campos del formulario de los que depende.
    direccion() {
      const base = this.$root.dataset.url;
      const formulario = this.$root.closest("form");
      const parametros = new URLSearchParams();
      for (const nombre of (this.$root.dataset.parametros || "").split(" ").filter(Boolean)) {
        const campo = formulario?.elements.namedItem(nombre);
        if (campo && campo.value) parametros.set(nombre, campo.value);
      }
      const extra = parametros.toString();
      return extra ? `${base}${base.includes("?") ? "&" : "?"}${extra}` : base;
    },

    // Pide la lista al servidor. Si falla, lo dice en la ventana.
    //   - direccion: la dirección completa.
    async cargar(direccion) {
      this.cargando = true;
      this.error = "";
      try {
        const respuesta = await fetch(direccion, { headers: { Accept: "application/json" } });
        if (!respuesta.ok) throw new Error();
        const datos = await respuesta.json();
        this.bloques = datos.bloques;
        this.veLaLista = datos.ve_la_lista;
        this.plegado = {};
        this.pedida = direccion;
      } catch {
        this.bloques = [];
        this.error = "No se ha podido cargar la lista. Prueba otra vez.";
      } finally {
        this.cargando = false;
      }
    },

    // Dice si un alias está elegido (sin distinguir mayúsculas).
    esta(alias) {
      return this.elegidas.some((elegida) => elegida.toLowerCase() === alias.toLowerCase());
    },

    // Elige una persona. Si son varias, la pone o la quita; si es una sola, la deja como la elegida y
    // cierra la ventana.
    elegir(alias) {
      if (!this.varias) {
        this.elegidas = [alias];
        this.cerrar();
      } else if (this.esta(alias)) {
        this.quitar(alias);
      } else {
        this.elegidas.push(alias);
      }
    },

    // Quita una persona elegida (la × de su pastilla).
    quitar(alias) {
      this.elegidas = this.elegidas.filter((elegida) => elegida.toLowerCase() !== alias.toLowerCase());
    },

    // Añade el alias escrito a mano (cuando no se puede ver la lista). Se comprueba al guardar.
    anadirEscrito() {
      const alias = this.aliasEscrito.trim();
      if (alias && !this.esta(alias)) this.elegir(alias);
      this.aliasEscrito = "";
    },

    // Dice si una persona coincide con lo buscado: cada palabra escrita debe estar en su alias, en su
    // grupo o en su marca, sin importar tildes ni mayúsculas.
    //   - persona: {alias, marca}.
    //   - grupo: {nombre}.
    coincide(persona, grupo) {
      const palabras = normalizar(this.texto).split(/\s+/).filter(Boolean);
      if (!palabras.length) return true;
      const donde = normalizar(`${persona.alias} ${grupo.nombre} ${persona.marca}`);
      return palabras.every((palabra) => donde.includes(palabra));
    },

    // Cuántas personas de un grupo coinciden con lo buscado.
    cuantasDelGrupo(grupo) {
      return grupo.personas.filter((persona) => this.coincide(persona, grupo)).length;
    },

    // Cuántas personas de un bloque coinciden con lo buscado.
    cuantasDelBloque(bloque) {
      return bloque.grupos.reduce((total, grupo) => total + this.cuantasDelGrupo(grupo), 0);
    },

    // Si alguna persona coincide con lo buscado (si no, se dice que nadie).
    hayCoincidencias() {
      return this.bloques.some((bloque) => this.cuantasDelBloque(bloque) > 0);
    },

    // Si un bloque se ve desplegado: mientras se busca, todos; si no, los dos más cercanos, salvo que se
    // hayan abierto o cerrado a mano.
    //   - numero: posición del bloque.
    estaAbierto(numero) {
      if (this.texto.trim()) return true;
      return numero in this.plegado ? this.plegado[numero] : this.bloques[numero]?.nivel <= 1;
    },

    // Abre o cierra un bloque a mano.
    alternar(numero) {
      this.plegado = { ...this.plegado, [numero]: !this.estaAbierto(numero) };
    },
  }));

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

  // Isla de kanban (SortableJS), para los tableros de tareas (proyectos/templates/proyectos/kanban.html).
  // Se usa así:
  //   <div x-data="kanban" data-url="/proyectos/tareas/mover/">
  //     <ul class="columna" data-estado="pendiente"> <li data-id="5" class="movible">…</li> … </ul> …
  //   </div>
  // Cada columna es una lista ordenable; las tarjetas con la clase «movible» se arrastran entre columnas.
  // Al soltar una, manda al servidor su columna nueva y el orden de esa columna. Si el servidor no lo
  // acepta, lo explica y vuelve a cargar la página para no dejar a la vista algo que no se ha guardado.
  Alpine.data("kanban", () => ({
    // Mensaje de error (vacío si no hay).
    mensaje: "",

    // Al arrancar: hace ordenable cada columna, todas en el mismo grupo para pasar de una a otra.
    init() {
      if (typeof Sortable === "undefined") return;
      for (const columna of this.$root.querySelectorAll(".columna")) {
        Sortable.create(columna, {
          group: "kanban",
          draggable: ".movible",
          animation: 150,
          forceFallback: true,
          onEnd: (evento) => this.guardar(evento.item, evento.to),
        });
      }
    },

    // Guarda dónde ha quedado una tarjeta.
    //   - tarjeta: el elemento movido (con data-id).
    //   - columna: la lista donde ha caído (con data-estado).
    async guardar(tarjeta, columna) {
      const orden = [...columna.querySelectorAll("[data-id]")].map((elemento) => Number(elemento.dataset.id));
      let respuesta = null;
      try {
        respuesta = await fetch(this.$root.dataset.url, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content },
          body: JSON.stringify({ tarea: Number(tarjeta.dataset.id), estado: columna.dataset.estado, orden }),
        });
      } catch {
        respuesta = null;
      }
      if (respuesta && respuesta.ok) {
        this.mensaje = "";
        // Si otras tarjetas han cambiado de columna solas (esperaban a esta), se recarga el tablero.
        if ((await respuesta.json()).otras) window.location.reload();
        return;
      }
      this.mensaje = respuesta && respuesta.headers.get("Content-Type")?.includes("json") ? (await respuesta.json()).error : "No se ha podido guardar.";
      setTimeout(() => window.location.reload(), 1500);
    },
  }));

  // Isla de los documentos de «Desarrollo y mantenimiento» (Markdown convertido en HTML). Se usa así:
  //   <article x-data="documento" data-estaticos="/static/generado/diagramas/"> …documento… </article>
  // Hace dos cosas:
  //   - Casillas: las de las listas de comprobaciones («- [ ]» en el Markdown) se pueden marcar, y cada
  //     navegador recuerda las suyas (localStorage, por página). Arriba de la primera, «N de M hechas».
  //   - Diagramas: cambia los bloques de código «mermaid» (```mermaid en el Markdown) por su dibujo, en una
  //     caja con botones para acercar, alejar, ajustar y verlo a pantalla completa; se mueve arrastrándolo
  //     y se acerca con doble clic. Mermaid solo se carga si hay diagramas, y cada uno se dibuja cuando
  //     está a punto de verse al bajar por la página (dibujarlos todos de golpe tarda mucho).
  //   - Enlaces (opcional, con data-enlaces): cada nodo del diagrama lleva a una dirección (el grafo de
  //     grupos, grupos/templates/grupos/grafo.html).
  Alpine.data("documento", () => ({
    // Los diagramas ya dibujados (de svg-pan-zoom), para quitarlos al salir de la página.
    dibujos: [],
    // Para dejar de vigilar los bloques al salir de la página (una función; el vigilante en sí no se
    // guarda aquí, porque Alpine lo envolvería y dejaría de funcionar).
    dejarDeVigilar: null,

    // Al arrancar: prepara las casillas y, si hay bloques «mermaid», carga las dos librerías y vigila los
    // bloques para dibujar cada uno cuando quede a menos de una pantalla de la vista.
    async init() {
      this.casillas();
      const bloques = [...this.$root.querySelectorAll("pre > code.language-mermaid")];
      if (!bloques.length) return;
      const base = this.$root.dataset.estaticos;
      await cargarUnaVez(base + "mermaid.min.js");
      await cargarUnaVez(base + "svg-pan-zoom.min.js");
      // securityLevel «strict»: el texto de los diagramas no puede llevar HTML ni enlaces con código.
      window.mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict", flowchart: { curve: "basis" } });
      // Cola de dibujos: Mermaid dibuja uno detrás de otro (dos a la vez se estorban).
      let cola = Promise.resolve();
      const vigilante = new IntersectionObserver((entradas) => {
        for (const entrada of entradas) {
          if (!entrada.isIntersecting) continue;
          vigilante.unobserve(entrada.target);
          const codigo = entrada.target.querySelector("code");
          const numero = bloques.indexOf(codigo);
          cola = cola.then(() => this.dibujar(codigo, numero));
        }
      }, {
        // La página no se desplaza entera sino su parte central (#desplazable, en base/pagina.html) o el
        // panel de ayuda: se vigila contra la que contiene el documento (marcada con data-desplaza), una
        // pantalla por arriba y por abajo.
        root: this.$root.closest("[data-desplaza]") || document.getElementById("desplazable"),
        rootMargin: "100% 0px",
      });
      for (const codigo of bloques) vigilante.observe(codigo.parentElement);
      this.dejarDeVigilar = () => vigilante.disconnect();
    },

    // Activa las casillas: recupera las marcadas de este documento, guarda cada cambio y pone al día el
    // recuento. Se recuerdan por la dirección del documento (data-direccion), no por la de la página, para
    // que sean las mismas en la zona principal y en el panel de ayuda. Si el navegador no deja guardar
    // (modo privado), funcionan igual, sin recordarse.
    casillas() {
      const todas = [...this.$root.querySelectorAll("input[data-casilla]")];
      if (!todas.length) return;
      const clave = `casillas:${this.$root.dataset.direccion || window.location.pathname}`;
      let marcadas = [];
      try {
        marcadas = JSON.parse(localStorage.getItem(clave) || "[]");
      } catch {
        marcadas = [];
      }
      const recuento = document.createElement("p");
      recuento.className = "recuento-de-casillas text-sm font-medium text-marca";
      todas[0].closest("ul, ol").before(recuento);
      const contar = () => {
        recuento.textContent = `${todas.filter((casilla) => casilla.checked).length} de ${todas.length} comprobaciones hechas (se recuerdan en este navegador).`;
      };
      todas.forEach((casilla, numero) => {
        casilla.disabled = false;
        casilla.checked = marcadas.includes(numero);
        casilla.addEventListener("change", () => {
          const ahora = todas.flatMap((otra, posicion) => (otra.checked ? [posicion] : []));
          try {
            localStorage.setItem(clave, JSON.stringify(ahora));
          } catch {
            // Sin almacenamiento: no se recuerda, pero la casilla cambia igual.
          }
          contar();
        });
      });
      contar();
    },

    // Dibuja un bloque: pide el SVG a Mermaid, lo mete en una caja con sus botones en lugar del bloque de
    // código y le da zoom. Si el texto del diagrama tiene un error, deja el código y avisa debajo.
    //   - codigo: el elemento <code> con el texto del diagrama.
    //   - numero: su posición en el documento (para darle un id único).
    async dibujar(codigo, numero) {
      let svg;
      try {
        ({ svg } = await window.mermaid.render(`diagrama-${numero}-${Date.now()}`, codigo.textContent));
      } catch (error) {
        const aviso = document.createElement("p");
        aviso.className = "text-sm text-red-700";
        aviso.textContent = `Este diagrama tiene un error: ${error.message}`;
        codigo.parentElement.after(aviso);
        return;
      }
      const caja = document.createElement("div");
      caja.className = "diagrama";
      const botones = document.createElement("div");
      botones.className = "botones-del-diagrama";
      const lienzo = document.createElement("div");
      lienzo.className = "lienzo-del-diagrama";
      lienzo.innerHTML = svg;
      caja.append(botones, lienzo);
      codigo.parentElement.replaceWith(caja);
      const dibujo = lienzo.querySelector("svg");
      dibujo.removeAttribute("style");
      dibujo.setAttribute("width", "100%");
      dibujo.setAttribute("height", "100%");
      const zoom = window.svgPanZoom(dibujo, {
        zoomEnabled: true, mouseWheelZoomEnabled: false, dblClickZoomEnabled: true, fit: true, center: true, minZoom: 0.2, maxZoom: 30,
        // Cuánto acerca cada pulsación de «+» o cada doble clic (0,6: un 60 % más).
        zoomScaleSensitivity: 0.6,
      });
      this.dibujos.push(zoom);
      this.enlazar(dibujo);
      // Un botón con su texto, su explicación y lo que hace al pulsarlo.
      const boton = (texto, titulo, accion) => {
        const elemento = document.createElement("button");
        elemento.type = "button";
        elemento.textContent = texto;
        elemento.title = titulo;
        elemento.setAttribute("aria-label", titulo);
        elemento.addEventListener("click", accion);
        botones.appendChild(elemento);
      };
      boton("+", "Acercar", () => zoom.zoomIn());
      boton("−", "Alejar", () => zoom.zoomOut());
      boton("⤢", "Ajustar a la caja", () => { zoom.resize(); zoom.fit(); zoom.center(); });
      boton("⛶", "Pantalla completa", async () => {
        if (document.fullscreenElement) await document.exitFullscreen();
        else await caja.requestFullscreen();
        zoom.resize(); zoom.fit(); zoom.center();
      });
    },

    // Si la página trae enlaces para los nodos (data-enlaces: el id de un <script> con {nodo: dirección},
    // como el grafo de grupos), cada nodo se puede pulsar y lleva a su dirección. Mermaid llama a cada nodo
    // «…flowchart-<nombre>-<número>»; de ahí se saca su nombre. Un arrastre para mover el dibujo no cuenta
    // como pulsación.
    //   - dibujo: el <svg> ya dibujado.
    enlazar(dibujo) {
      const fuente = this.$root.dataset.enlaces && document.getElementById(this.$root.dataset.enlaces);
      if (!fuente) return;
      const enlaces = JSON.parse(fuente.textContent);
      for (const nodo of dibujo.querySelectorAll("g.node")) {
        const nombre = (nodo.id.match(/flowchart-(.+)-\d+$/) || [])[1];
        const direccion = enlaces[nombre];
        if (!direccion) continue;
        nodo.style.cursor = "pointer";
        let desde = null;
        nodo.addEventListener("pointerdown", (evento) => { desde = [evento.clientX, evento.clientY]; });
        nodo.addEventListener("click", (evento) => {
          if (desde && Math.hypot(evento.clientX - desde[0], evento.clientY - desde[1]) > 5) return;
          window.location.href = direccion;
        });
      }
    },

    // Al salir de la página (htmx cambia la zona central): deja de vigilar y suelta los diagramas.
    destroy() {
      if (this.dejarDeVigilar) this.dejarDeVigilar();
      for (const zoom of this.dibujos) zoom.destroy();
      this.dibujos = [];
    },
  }));

  // Isla del editor colaborativo en tiempo real (el servicio aparte de editor/; ver base/editor.py). La
  // pinta base/templates/base/_editor.html con todo en data-*:
  //   data-cliente (el script del editor), data-url (su WebSocket), data-sala, data-pase, data-alias,
  //   data-color, data-permiso, data-renovar (dónde pedir un pase nuevo al reconectar) y, si hay vista
  //   previa, data-vista-previa (dónde se convierte el texto) y data-destino (el id del recuadro que se
  //   cambia).
  // Carga el editor la primera vez, se conecta a la sala y enseña quién está y si hay conexión.
  Alpine.data("editorEnVivo", () => ({
    // Quién está en la sala ([{name, color}]) y el estado de la conexión.
    personas: [],
    estado: "connecting",
    // El editor montado (para quitarlo al salir) y el reloj de la vista previa.
    editor: null,
    espera: null,

    // Al arrancar: carga el script del editor y lo monta. El primer pase viene en la página; los
    // siguientes (al reconectar, porque duran pocos minutos) se piden a data-renovar.
    async init() {
      const datos = this.$root.dataset;
      await cargarUnaVez(datos.cliente);
      let primero = datos.pase;
      const pase = async () => {
        if (primero) {
          const este = primero;
          primero = "";
          return este;
        }
        const respuesta = await fetch(datos.renovar, { headers: { Accept: "application/json" } });
        if (!respuesta.ok) throw new Error("Sin permiso");
        return (await respuesta.json()).pase;
      };
      this.editor = window.EditorColaborativo.montar(this.$refs.cuadro, {
        url: datos.url, sala: datos.sala, pase, alias: datos.alias, color: datos.color, permiso: datos.permiso,
        alCambiar: (texto) => this.previa(texto),
        alPersonas: (lista) => (this.personas = lista),
        alEstado: (estado) => (this.estado = estado),
      });
    },

    // Pide la vista previa del texto medio segundo después del último cambio (si la pantalla tiene).
    previa(texto) {
      const datos = this.$root.dataset;
      if (!datos.vistaPrevia) return;
      clearTimeout(this.espera);
      this.espera = setTimeout(async () => {
        const cuerpo = new URLSearchParams({ texto });
        const respuesta = await fetch(datos.vistaPrevia, {
          method: "POST",
          headers: { "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content },
          body: cuerpo,
        });
        const destino = document.getElementById(datos.destino);
        if (respuesta.ok && destino) destino.outerHTML = await respuesta.text();
      }, 500);
    },

    // Al salir de la pantalla: se desconecta.
    destroy() {
      clearTimeout(this.espera);
      this.editor?.destruir();
    },
  }));

  // Isla de calendario (FullCalendar), para la pantalla «Calendario» (calendario/templates). Se usa así:
  //   <div x-data="calendario" data-estaticos="/static/generado/fullcalendar/" data-datos="/calendario/datos/"
  //        data-mover="/calendario/mover/" data-nuevo="/calendario/recordatorios/nuevo/">
  //     <div x-ref="lienzo"></div>
  //   </div>
  // Pide al servidor las fechas del trozo que se ve (data-datos, en JSON), las pinta con el color de su
  // tipo, deja ocultar tipos con las casillas de filtro (se recuerda en este navegador), arrastrar lo que
  // se puede mover (data-mover) y, al pulsar un hueco, apuntar un recordatorio (data-nuevo). En el móvil
  // empieza en la vista de lista. FullCalendar se carga solo la primera vez que hace falta.
  Alpine.data("calendario", () => ({
    // El calendario de FullCalendar, para poder quitarlo al salir de la página.
    calendario: null,
    // Tipos que se han visto ({nombre, color, visible}), para las casillas de filtro.
    categorias: [],
    // Nombres de los tipos ocultos.
    ocultas: new Set(),
    // Mensaje de error al mover algo (vacío si no hay).
    mensaje: "",
    // Últimas fechas pedidas, para no volver a pedirlas al cambiar un filtro: {clave, fechas}.
    ultimas: { clave: "", fechas: [] },

    // Al arrancar: carga FullCalendar (si aún no estaba), recupera los filtros guardados y pinta el
    // calendario.
    async init() {
      const base = this.$root.dataset.estaticos;
      await cargarUnaVez(base + "index.global.min.js");
      await cargarUnaVez(base + "es.global.min.js");
      try {
        this.ocultas = new Set(JSON.parse(localStorage.getItem("calendario.ocultas") || "[]"));
      } catch {
        this.ocultas = new Set();
      }
      const estrecho = window.matchMedia("(max-width: 767px)").matches;
      const vistas = "dayGridMonth,timeGridWeek,timeGridDay,listMonth";
      this.calendario = new FullCalendar.Calendar(this.$refs.lienzo, {
        locale: "es",
        firstDay: 1,
        height: "auto",
        nowIndicator: true,
        navLinks: true,
        initialView: estrecho ? "listMonth" : "dayGridMonth",
        headerToolbar: estrecho
          ? { left: "prev,next", center: "title", right: "today" }
          : { left: "prev,next today", center: "title", right: vistas },
        footerToolbar: estrecho ? { center: vistas } : false,
        events: (info, bien, mal) => this.pedir(info).then(bien, mal),
        eventDrop: (info) => this.mover(info),
        eventResize: (info) => this.mover(info),
        dateClick: (info) => {
          window.location.href = `${this.$root.dataset.nuevo}?inicio=${encodeURIComponent(info.dateStr)}`;
        },
      });
      this.calendario.render();
    },

    // Pide las fechas del trozo visible (o reutiliza las últimas, si es el mismo trozo), apunta los tipos
    // nuevos para los filtros y devuelve solo las de los tipos que no están ocultos.
    //   - info: el trozo que pide FullCalendar (startStr, endStr).
    async pedir(info) {
      const clave = `${info.startStr}|${info.endStr}`;
      if (this.ultimas.clave !== clave) {
        const direccion = `${this.$root.dataset.datos}?start=${encodeURIComponent(info.startStr)}&end=${encodeURIComponent(info.endStr)}`;
        const respuesta = await fetch(direccion, { headers: { Accept: "application/json" } });
        if (!respuesta.ok) throw new Error("No se han podido cargar las fechas.");
        this.ultimas = { clave, fechas: (await respuesta.json()).fechas };
      }
      for (const fecha of this.ultimas.fechas) {
        if (!this.categorias.some((categoria) => categoria.nombre === fecha.categoria)) {
          this.categorias.push({ nombre: fecha.categoria, color: fecha.color, visible: !this.ocultas.has(fecha.categoria) });
        }
      }
      return this.ultimas.fechas.filter((fecha) => !this.ocultas.has(fecha.categoria));
    },

    // Muestra u oculta un tipo, lo recuerda en este navegador y vuelve a pintar (sin pedir nada).
    //   - categoria: {nombre, visible}.
    alternar(categoria) {
      categoria.visible = !categoria.visible;
      if (categoria.visible) this.ocultas.delete(categoria.nombre);
      else this.ocultas.add(categoria.nombre);
      try {
        localStorage.setItem("calendario.ocultas", JSON.stringify([...this.ocultas]));
      } catch {
        // Sin almacenamiento (ventana privada…): el filtro vale solo mientras no se salga de la página.
      }
      this.calendario.refetchEvents();
    },

    // Guarda la fecha nueva de algo que se ha arrastrado (o estirado). Si el servidor no lo acepta, lo
    // devuelve a su sitio y muestra por qué. No deja pasar algo con hora a «todo el día» ni al revés.
    //   - info: lo que da FullCalendar (event, oldEvent, revert).
    async mover(info) {
      this.mensaje = "";
      if (info.oldEvent.allDay !== info.event.allDay) {
        info.revert();
        this.mensaje = "Solo se puede cambiar el día o la hora, no pasarlo a «todo el día» (ni al revés).";
        return;
      }
      const datos = new FormData();
      datos.append("fuente", info.event.extendedProps.fuente);
      datos.append("id", info.event.extendedProps.numero);
      datos.append("todo_el_dia", info.event.allDay ? "1" : "0");
      datos.append("inicio", info.event.startStr);
      datos.append("fin", info.event.endStr || "");
      const cabeceras = JSON.parse(document.body.getAttribute("hx-headers") || "{}");
      const respuesta = await fetch(this.$root.dataset.mover, { method: "POST", body: datos, headers: cabeceras });
      if (!respuesta.ok) {
        info.revert();
        this.mensaje = respuesta.headers.get("Content-Type")?.includes("json")
          ? (await respuesta.json()).error
          : "No se ha podido guardar el cambio.";
        return;
      }
      // Las fechas guardadas ya no valen: la próxima vez se piden de nuevo.
      this.ultimas = { clave: "", fechas: [] };
    },

    // Al quitar el componente (al navegar a otra página): libera el calendario.
    destroy() {
      if (this.calendario) this.calendario.destroy();
    },
  }));
});

// Devuelve una promesa que se cumple cuando htmx ya está cargado. Hace falta porque Alpine arranca antes
// de que se ejecute htmx.min.js (va detrás en base/cabeza.html): si un componente quiere usar htmx al
// arrancar (el panel de ayuda, al recargar con el panel abierto), espera al final de la carga de la página
// (DOMContentLoaded), cuando ya se han ejecutado todos los scripts.
function htmxListo() {
  if (window.htmx) return Promise.resolve();
  return new Promise((resolver) => document.addEventListener("DOMContentLoaded", resolver, { once: true }));
}

// Tamaños de letra del panel de ayuda, de menor a mayor (1 es el normal). Los botones − y + van de uno a
// otro. La usa el componente panelDeAyuda.
const TAMANOS_DE_LETRA_DEL_PANEL = [0.7, 0.8, 0.9, 1, 1.1, 1.25, 1.4, 1.6];

// Ancho de partida del panel de ayuda, en píxeles: un tercio largo de la pantalla, entre 320 y 720. El
// script de la cabecera (base/templates/base/cabeza.html) hace el mismo cálculo antes de pintar. La usa
// el componente panelDeAyuda.
function anchoDePartidaDelPanel() {
  return Math.round(Math.min(Math.max(window.innerWidth * 0.35, 320), 720));
}

// Ficheros (scripts u hojas de estilo) ya pedidos, para no cargarlos dos veces: {dirección: promesa}.
const ficherosCargados = {};

// Carga un script o una hoja de estilos (por su terminación) y devuelve una promesa que se cumple cuando
// está listo. Si ya se pidió antes, devuelve la misma promesa. La usan los componentes «mapa», «calendario» y «documento».
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
