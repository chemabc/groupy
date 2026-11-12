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

// Alpine lanza «alpine:init» justo antes de arrancar: es el momento de registrar almacenes y componentes.
document.addEventListener("alpine:init", () => {
  // Almacén de preferencias de presentación. Las aplica como atributos de <html> (data-tema,
  // data-letra, data-densidad), que la hoja de estilos usa para cambiar colores, tamaño y espacios.
  // El script del <head> ya las aplicó al cargar; aquí se leen de nuevo para poder cambiarlas.
  // Cuando exista «usuarios» (fase 1), se guardarán también en las preferencias de cada persona.
  Alpine.store("preferencias", {
    tema: document.documentElement.dataset.tema,
    letra: document.documentElement.dataset.letra,
    densidad: document.documentElement.dataset.densidad,

    // Cambia una preferencia, la aplica a la página y la guarda en el navegador.
    //   - clave: «tema», «letra» o «densidad».
    //   - valor: por ejemplo «oscuro», «grande» o «compacta».
    poner(clave, valor) {
      this[clave] = valor;
      document.documentElement.dataset[clave] = valor;
      guardar(clave, valor);
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
});
