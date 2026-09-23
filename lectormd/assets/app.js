/* lectorMD — lógica del visor.
   Se ejecuta dentro del WebView; Python le pasa el contenido ya renderizado
   y lo controla a través del objeto global `lector`. */

(function () {
  "use strict";

  const $ = (sel, raiz = document) => raiz.querySelector(sel);
  const $$ = (sel, raiz = document) => Array.from(raiz.querySelectorAll(sel));

  // Mermaid pone las etiquetas como HTML dentro del SVG (foreignObject), que
  // se ve mejor pero "ensucia" el canvas y no se puede pasar a PNG. Para
  // exportar a Word se repinta con etiquetas SVG puras.
  let etiquetasSvg = false;

  /* ------------------------------------------------------------ fórmulas */
  function pintarFormulas() {
    if (typeof katex === "undefined") return;
    $$(".formula").forEach((el) => {
      if (el.dataset.hecho === "1") return;
      const origen = el.textContent;
      el.dataset.latex = origen;
      try {
        katex.render(origen, el, {
          displayMode: el.dataset.display === "1",
          throwOnError: false,
          output: "html",
        });
        el.dataset.hecho = "1";
      } catch (e) {
        el.classList.add("formula-error");
        el.textContent = origen;
      }
    });
  }

  /* ------------------------------------------------------------ diagramas */
  function temaMermaid() {
    return document.body.dataset.tema === "oscuro" ? "dark" : "default";
  }

  async function pintarDiagramas() {
    const nodos = $$(".mermaid");
    if (!nodos.length || typeof mermaid === "undefined") return;

    // Se guarda el código fuente para poder repintar al cambiar de tema.
    nodos.forEach((n) => {
      if (!n.dataset.fuente) n.dataset.fuente = n.textContent.trim();
      n.removeAttribute("data-processed");
      n.textContent = n.dataset.fuente;
    });

    mermaid.initialize({
      startOnLoad: false,
      theme: temaMermaid(),
      securityLevel: "strict",
      htmlLabels: !etiquetasSvg,
      // Con etiquetas SVG, Mermaid parte palabras largas a 200 px.
      flowchart: { htmlLabels: !etiquetasSvg, wrappingWidth: etiquetasSvg ? 480 : 200 },
      fontFamily: getComputedStyle(document.body).getPropertyValue("--fuente-ui"),
    });

    try {
      await mermaid.run({ nodes: nodos });
    } catch (e) {
      console.warn("mermaid:", e);
    }
  }

  /* Convierte un SVG de Mermaid en PNG. Devuelve null si no se puede. */
  function svgAPng(svg, escala = 2) {
    return new Promise((resolver) => {
      try {
        const caja = svg.getBoundingClientRect();
        const ancho = Math.ceil(caja.width) || 600;
        const alto = Math.ceil(caja.height) || 400;

        const copia = svg.cloneNode(true);
        copia.setAttribute("width", ancho);
        copia.setAttribute("height", alto);
        copia.setAttribute("xmlns", "http://www.w3.org/2000/svg");
        copia.style.maxWidth = "none";

        const xml = new XMLSerializer().serializeToString(copia);
        const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);

        const img = new Image();
        img.onload = () => {
          try {
            const lienzo = document.createElement("canvas");
            lienzo.width = ancho * escala;
            lienzo.height = alto * escala;
            const ctx = lienzo.getContext("2d");
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(0, 0, lienzo.width, lienzo.height);
            ctx.scale(escala, escala);
            ctx.drawImage(img, 0, 0, ancho, alto);
            resolver({ png: lienzo.toDataURL("image/png"), ancho, alto });
          } catch (e) {
            console.warn("canvas:", e);
            resolver(null);
          }
        };
        img.onerror = () => resolver(null);
        img.src = url;
      } catch (e) {
        resolver(null);
      }
    });
  }

  /* --------------------------------------------------------------- copiar */
  function activarCopiar() {
    $$(".copiar").forEach((btn) => {
      if (btn.dataset.listo === "1") return;
      btn.dataset.listo = "1";
      btn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(btn.dataset.codigo || "");
        } catch (e) {
          const ta = document.createElement("textarea");
          ta.value = btn.dataset.codigo || "";
          ta.style.position = "fixed";
          ta.style.opacity = "0";
          document.body.appendChild(ta);
          ta.select();
          try { document.execCommand("copy"); } catch (_) {}
          ta.remove();
        }
        const previo = btn.textContent;
        btn.textContent = "Copiado";
        btn.classList.add("listo");
        setTimeout(() => {
          btn.textContent = previo;
          btn.classList.remove("listo");
        }, 1400);
      });
    });
  }

  /* --------------------------------------------------------------- anclas */
  function ponerAnclas() {
    $$(".encabezado").forEach((h) => {
      if (!h.id || $(".ancla", h)) return;
      const a = document.createElement("a");
      a.className = "ancla";
      a.href = "#" + h.id;
      a.textContent = "#";
      a.setAttribute("aria-label", "Enlace a esta sección");
      h.prepend(a);
    });
  }

  /* ---------------------------------------------------------------- lupa */
  function activarLupa() {
    const lupa = $("#lupa");
    const img = $("img", lupa);
    $$(".contenido img").forEach((el) => {
      if (el.dataset.lupa === "1") return;
      el.dataset.lupa = "1";
      el.addEventListener("click", () => {
        img.src = el.src;
        lupa.classList.add("visible");
      });
    });
  }

  /* --------------------------------------------- progreso y índice activo */
  let encabezados = [];
  let enlacesIndice = new Map();

  function indexar() {
    encabezados = $$(".contenido .encabezado").filter((h) => h.id);
    enlacesIndice = new Map();
    $$("#indice a").forEach((a) => enlacesIndice.set(a.getAttribute("href").slice(1), a));
  }

  function alDesplazar() {
    const alto = document.documentElement.scrollHeight - window.innerHeight;
    const pct = alto > 0 ? (window.scrollY / alto) * 100 : 0;
    $("#progreso").style.width = pct + "%";

    if (!encabezados.length) return;
    const limite = window.innerHeight * 0.3;
    let actual = encabezados[0];
    for (const h of encabezados) {
      if (h.getBoundingClientRect().top <= limite) actual = h;
      else break;
    }
    if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 4) {
      actual = encabezados[encabezados.length - 1];
    }

    enlacesIndice.forEach((a) => a.classList.remove("activo"));
    const activo = enlacesIndice.get(actual.id);
    if (activo) {
      activo.classList.add("activo");
      const caja = $("#indice");
      const r = activo.getBoundingClientRect();
      const rc = caja.getBoundingClientRect();
      if (r.top < rc.top || r.bottom > rc.bottom) activo.scrollIntoView({ block: "nearest" });
    }
  }

  /* ------------------------------------------------------ aviso flotante */
  let temporizador = null;
  function avisar(texto, tipo = "ok") {
    const el = $("#flotante");
    el.textContent = texto;
    el.className = "visible " + tipo;
    clearTimeout(temporizador);
    temporizador = setTimeout(() => (el.className = ""), tipo === "error" ? 5000 : 2600);
  }

  /* ------------------------------------------------------- API para Python */
  let temaPrevio = null;

  window.lector = {
    estilos(css) {
      $("#css-resaltado").textContent = css;
    },

    cargar(datos) {
      $("#vacio").style.display = "none";
      $("#cabecera").style.display = "";
      $(".contenido").innerHTML = datos.cuerpo;
      $("#titulo").textContent = datos.titulo || "";

      const meta = $("#meta");
      meta.innerHTML = "";
      const m = datos.meta || {};
      const trozos = [m.autor, m.author, m.fecha, m.date].filter(Boolean).map(String);
      trozos.push(datos.palabras.toLocaleString("es") + " palabras");
      trozos.push(datos.minutos + " min de lectura");
      trozos.forEach((t, i) => {
        if (i) {
          const p = document.createElement("span");
          p.className = "punto";
          meta.appendChild(p);
        }
        const s = document.createElement("span");
        s.textContent = t;
        meta.appendChild(s);
      });

      const idx = $("#indice");
      idx.innerHTML = "";
      if (datos.indice && datos.indice.length > 1) {
        const h2 = document.createElement("h2");
        h2.textContent = "Contenido";
        const ul = document.createElement("ul");
        datos.indice.forEach((e) => {
          const li = document.createElement("li");
          const a = document.createElement("a");
          a.href = "#" + e.id;
          a.className = "n" + e.nivel;
          a.textContent = e.texto;
          a.title = e.texto;
          li.appendChild(a);
          ul.appendChild(li);
        });
        idx.append(h2, ul);
        if (document.body.dataset.indice !== "cerrado") document.body.dataset.indice = "visible";
      } else {
        document.body.dataset.indice = document.body.dataset.indice === "cerrado" ? "cerrado" : "oculto";
      }

      ponerAnclas();
      activarCopiar();
      activarLupa();
      pintarFormulas();
      pintarDiagramas();
      indexar();
      if (!datos.conservarScroll) window.scrollTo(0, 0);
      alDesplazar();
      window.__docCargado = true;
      return datos.indice ? datos.indice.length : 0;
    },

    tema(t) {
      document.body.dataset.tema = t;
      pintarDiagramas();
    },

    fuente(cual) {
      document.body.dataset.fuente = cual;
    },

    indice(visible) {
      document.body.dataset.indice = visible ? "visible" : "cerrado";
    },

    avisar,

    /* Exportación: Python llama a prepararExportacion, espera la bandera,
       hace su trabajo y luego llama a restaurar. */
    prepararExportacion(opciones = {}) {
      window.__exportListo = false;
      temaPrevio = document.body.dataset.tema;
      document.body.dataset.tema = "claro";
      etiquetasSvg = !!opciones.svg;
      $("#lupa").classList.remove("visible");
      Promise.all([pintarDiagramas(), document.fonts.ready]).then(() => {
        // Dos fotogramas para que el repintado termine antes de imprimir. Una
        // vista oculta no genera fotogramas: por eso hay un plazo de respaldo.
        let hecho = false;
        const listo = () => {
          if (!hecho) {
            hecho = true;
            window.__exportListo = true;
          }
        };
        requestAnimationFrame(() => requestAnimationFrame(listo));
        setTimeout(listo, 300);
      });
      return true;
    },

    capturarDiagramas() {
      window.__diagramas = null;
      const svgs = $$(".mermaid").map((n) => $("svg", n));
      Promise.all(svgs.map((s) => (s ? svgAPng(s) : Promise.resolve(null)))).then((r) => {
        window.__diagramas = JSON.stringify(r);
      });
      return svgs.length;
    },

    restaurar() {
      etiquetasSvg = false;
      if (temaPrevio) document.body.dataset.tema = temaPrevio;
      temaPrevio = null;
      pintarDiagramas();
    },
  };

  /* ------------------------------------------------------------- arranque */
  window.addEventListener("scroll", alDesplazar, { passive: true });
  window.addEventListener("resize", alDesplazar, { passive: true });
  $("#lupa").addEventListener("click", () => $("#lupa").classList.remove("visible"));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") $("#lupa").classList.remove("visible");
  });
})();
