(function () {
  const sections = JSON.parse(document.getElementById("app-data").textContent);
  const modelUrl = window.APP_MODEL_URL;

  const menu = document.getElementById("main-menu");
  const contentPanel = document.getElementById("content-panel");
  const contentTitle = document.getElementById("content-title");
  const contentTabs = document.getElementById("content-tabs");
  const contentArea = document.querySelector(".content-area");
  const contentSubnav = document.getElementById("content-subnav");
  const contentBody = document.getElementById("content-body");
  const contentImages = document.getElementById("content-images");
  const closeBtn = document.getElementById("close-btn");
  const connectionLine = document.getElementById("connection-line");
  const verticalLineUp = document.getElementById("vertical-line-up");
  const verticalLineDown = document.getElementById("vertical-line-down");
  const langToggle = document.getElementById("lang-toggle");

  let currentLang = "pt";

  const headerStrings = window.APP_HEADER;

  function setLang(lang) {
    currentLang = lang;
    langToggle.querySelectorAll("button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === lang);
    });
    // Update app header
    const hs = headerStrings[lang];
    document.getElementById("header-subtitle").textContent = hs.subtitle;
    document.getElementById("header-title").textContent    = hs.title;
    // Rebuild menu labels
    buildMenu();
    // Re-render current view if open
    if (activeSectionSlug) {
      const section = getSectionBySlug(activeSectionSlug);
      if (section) renderTabs(section);
    }
    // Refresh lightbox caption if open
    if (lightboxEl && lightboxEl.classList.contains("visible")) {
      lightboxEl._refresh();
    }
  }

  langToggle.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => setLang(btn.dataset.lang));
  });

  const INTERACTIVE_MAP_SLUG = "aquisicao-de-terrenos";
  const USO_SOLOS_SLUG = "uso-dos-solos";

  // ── Switch between "v1" and "v2" when the client decides ──────────────────
  const USO_SOLOS_ACTIVE_VERSION = "v1"; // change to "v2" to show V2 maps
  // ──────────────────────────────────────────────────────────────────────────

  const USO_SOLOS_VERSIONS = {
    v1: {
      years: ["2002", "2018", "2026"],
      images: {
        "2002": "/static/app/maps/uso_solos_2002.png",
        "2018": "/static/app/maps/uso_solos_2018.png",
        "2026": "/static/app/maps/uso_solos_2026.png",
      },
      legendUrl: "/static/app/maps/uso_solos_legenda.png",
    },
    v2: {
      years: ["2002", "2018", "2026"],
      images: {
        "2002": "/static/app/maps/uso_solos_2002_v2.png",
        "2018": "/static/app/maps/uso_solos_2018_v2.png",
        "2026": "/static/app/maps/uso_solos_2026_v2.png",
      },
      legendUrl: "/static/app/maps/uso_solos_legenda_v2.png",
    },
  };
  const USO_SOLOS_CONFIG = USO_SOLOS_VERSIONS[USO_SOLOS_ACTIVE_VERSION];
  const INTERACTIVE_MAP_CONFIG = {
    svgUrl: "/static/app/maps/furnas_svg.svg",
    // Background image aligned inside SVG frame rect.
    baseImageUrl: "/static/app/maps/furnas_map_sample.png?v=2",
    // Temporary helper while mapping DB rows to SVG areas.
    showAreaIndexLabels: false,
    // Customize colors/content by SVG path index (0-based, excluding the outer frame rect).
    areas: {
      0: { title: "Área 1", color: "rgba(245, 99, 132, 0.35)", popup: "Detalhes desta área." },
      1: { title: "Área 2", color: "rgba(54, 162, 235, 0.35)", popup: "Detalhes desta área." },
      2: { title: "Área 3", color: "rgba(75, 192, 192, 0.35)", popup: "Detalhes desta área." },
      3: { title: "Área 4", color: "rgba(255, 206, 86, 0.35)", popup: "Detalhes desta área." },
      4: { title: "Área 5", color: "rgba(153, 102, 255, 0.35)", popup: "Detalhes desta área." },
      5: { title: "Área 6", color: "rgba(255, 159, 64, 0.35)", popup: "Detalhes desta área." },
      6: { title: "Área 7", color: "rgba(46, 204, 113, 0.35)", popup: "Detalhes desta área." },
      7: { title: "Área 8", color: "rgba(26, 188, 156, 0.35)", popup: "Detalhes desta área." },
      8: { title: "Área 9", color: "rgba(231, 76, 60, 0.35)", popup: "Detalhes desta área." },
      9: { title: "Área 10", color: "rgba(52, 152, 219, 0.35)", popup: "Detalhes desta área." },
    },
    defaultColor: "rgba(248, 153, 44, 0.25)",
    defaultStroke: "rgba(248, 153, 44, 0.9)",
  };

  let activeSectionSlug = null;
  let interactiveMapState = {
    modal: null,
    stage: null,
    canvas: null,
    legend: null,
    title: null,
    popup: null,
    closeBtn: null,
    lastSvgUrl: null,
    lastImageUrl: null,
    lastContentId: null,
    areaElementsByIndex: {},
    activeAreaIndex: null,
    activateAreaByIndex: null,
  };

  function sectionLabel(section) {
    const label = (currentLang === "en" && section.title_en)
      ? section.title_en
      : (section.title || section.slug);
    return label.replace(/^\d+(\.\d+)?\s*-\s*/g, "");
  }

  function shouldShowInteractiveMap(contentItem) {
    return contentItem && contentItem.slug === INTERACTIVE_MAP_SLUG;
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatAreaHa(value) {
    if (value === null || value === undefined || value === "") return "";
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return String(value);
    return `${numeric.toLocaleString("pt-PT", { maximumFractionDigits: 9 })} ha`;
  }

  function buildDbPopupText(mapArea) {
    if (!mapArea) return "";
    const lines = [];
    if (mapArea.location) lines.push(`Local: ${mapArea.location}`);
    if (mapArea.area_ha !== "") lines.push(`Área: ${formatAreaHa(mapArea.area_ha)}`);
    return lines.join("\n");
  }

  function defaultAreaColor(index) {
    const palette = [
      "rgba(245, 99, 132, 0.35)",
      "rgba(54, 162, 235, 0.35)",
      "rgba(75, 192, 192, 0.35)",
      "rgba(255, 206, 86, 0.35)",
      "rgba(153, 102, 255, 0.35)",
      "rgba(255, 159, 64, 0.35)",
      "rgba(46, 204, 113, 0.35)",
      "rgba(26, 188, 156, 0.35)",
      "rgba(231, 76, 60, 0.35)",
      "rgba(52, 152, 219, 0.35)",
    ];
    return palette[index % palette.length];
  }

  function toActiveFillColor(color) {
    if (!color) return color;
    const value = String(color).trim();
    const rgbaMatch = value.match(/^rgba?\(([^)]+)\)$/i);
    if (rgbaMatch) {
      const parts = rgbaMatch[1].split(",").map((part) => part.trim());
      if (parts.length >= 3) {
        const r = parts[0];
        const g = parts[1];
        const b = parts[2];
        const alpha = parts[3] !== undefined ? Number(parts[3]) : 1;
        const boosted = Number.isFinite(alpha) ? Math.max(alpha, 0.8) : 0.8;
        return `rgba(${r}, ${g}, ${b}, ${Math.min(1, boosted)})`;
      }
    }
    const hexMatch = value.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
    if (hexMatch) {
      let hex = hexMatch[1];
      if (hex.length === 3) {
        hex = hex.split("").map((ch) => ch + ch).join("");
      }
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      return `rgba(${r}, ${g}, ${b}, 0.8)`;
    }
    return value;
  }

  function getInteractiveMapAreaConfig(index, mapArea) {
    const custom = INTERACTIVE_MAP_CONFIG.areas[index];
    const dbColor = (mapArea?.fill_color || "").trim();
    const popupText = buildDbPopupText(mapArea);
    return {
      title: mapArea?.title || custom?.title || `Área ${index + 1}`,
      popup: popupText || custom?.popup || `Sem descrição configurada para o índice SVG ${index}.`,
      color: dbColor || custom?.color || defaultAreaColor(index) || INTERACTIVE_MAP_CONFIG.defaultColor,
      stroke: custom?.stroke || INTERACTIVE_MAP_CONFIG.defaultStroke,
    };
  }

  function mapAreasByIndex(contentItem) {
    const source = Array.isArray(contentItem?.map_areas) ? contentItem.map_areas : [];
    const byIndex = {};
    source.forEach((item) => {
      const index = Number(item.area_index);
      if (!Number.isNaN(index)) byIndex[index] = item;
    });
    return byIndex;
  }

  function renderAreaIndexLabels(svgRoot, areaElementsByIndex) {
    if (!INTERACTIVE_MAP_CONFIG.showAreaIndexLabels) return;
    const svgNs = "http://www.w3.org/2000/svg";
    const labelsGroup = document.createElementNS(svgNs, "g");
    labelsGroup.setAttribute("class", "interactive-map-index-labels");

    Object.entries(areaElementsByIndex).forEach(([index, pathEl]) => {
      if (!pathEl || typeof pathEl.getBBox !== "function") return;
      let bbox = null;
      try {
        bbox = pathEl.getBBox();
      } catch (error) {
        return;
      }
      if (!bbox || !Number.isFinite(bbox.x) || !Number.isFinite(bbox.y)) return;

      const cx = bbox.x + bbox.width / 2;
      const cy = bbox.y + bbox.height / 2;

      const badge = document.createElementNS(svgNs, "circle");
      badge.setAttribute("cx", String(cx));
      badge.setAttribute("cy", String(cy));
      badge.setAttribute("r", "9");
      badge.setAttribute("class", "interactive-map-index-badge");
      labelsGroup.appendChild(badge);

      const text = document.createElementNS(svgNs, "text");
      text.setAttribute("x", String(cx));
      text.setAttribute("y", String(cy + 0.5));
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("dominant-baseline", "middle");
      text.setAttribute("class", "interactive-map-index-label");
      text.textContent = String(index);
      labelsGroup.appendChild(text);
    });

    svgRoot.appendChild(labelsGroup);
  }

  function renderLegend(contentItem) {
    const state = interactiveMapState;
    if (!state.legend) return;
    const rows = Array.isArray(contentItem?.map_areas) ? [...contentItem.map_areas] : [];
    rows.sort((a, b) => {
      const orderA = Number.isFinite(Number(a.legend_order)) ? Number(a.legend_order) : 0;
      const orderB = Number.isFinite(Number(b.legend_order)) ? Number(b.legend_order) : 0;
      if (orderA !== orderB) return orderA - orderB;
      return Number(a.area_index) - Number(b.area_index);
    });
    if (!rows.length) {
      state.legend.innerHTML = `<div class="interactive-map-legend-empty">Sem áreas configuradas.</div>`;
      return;
    }
    state.legend.innerHTML = rows
      .map((row) => {
        const idx = Number(row.area_index);
        const cfg = getInteractiveMapAreaConfig(idx, row);
        return `
          <button type="button" class="interactive-map-legend-item" data-area-index="${idx}">
            <span class="interactive-map-legend-swatch" style="background:${cfg.color}; border-color:${cfg.stroke};"></span>
            <span class="interactive-map-legend-text">
              <span class="interactive-map-legend-title">${escapeHtml(cfg.title)}</span>
              <span class="interactive-map-legend-meta">${escapeHtml(row.location || "")}</span>
            </span>
          </button>
        `;
      })
      .join("");
  }

  function setLegendActive(areaIndex) {
    const state = interactiveMapState;
    if (!state.legend) return;
    state.legend.querySelectorAll(".interactive-map-legend-item").forEach((el) => {
      const isActive = Number(el.dataset.areaIndex) === areaIndex;
      el.classList.toggle("active", isActive);
      if (isActive) {
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
  }

  function closeInteractiveMap() {
    if (!interactiveMapState.modal) return;
    interactiveMapState.modal.classList.remove("visible");
  }

  function ensureInteractiveMapModal() {
    if (interactiveMapState.modal) return interactiveMapState;

    const modal = document.createElement("div");
    modal.id = "interactive-map-modal";
    modal.innerHTML = `
      <div class="interactive-map-dialog" role="dialog" aria-modal="true" aria-label="Mapa interativo">
        <div class="interactive-map-top">
          <h3 class="interactive-map-title" id="interactive-map-title">Mapa Interativo</h3>
          <button class="interactive-map-close" type="button" aria-label="Fechar mapa">✕</button>
        </div>
        <div class="interactive-map-stage" id="interactive-map-stage">
          <div class="interactive-map-canvas" id="interactive-map-canvas"></div>
          <aside class="interactive-map-legend" id="interactive-map-legend"></aside>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const state = {
      modal,
      stage: modal.querySelector("#interactive-map-stage"),
      canvas: modal.querySelector("#interactive-map-canvas"),
      legend: modal.querySelector("#interactive-map-legend"),
      title: modal.querySelector("#interactive-map-title"),
      popup: null,
      closeBtn: modal.querySelector(".interactive-map-close"),
      lastSvgUrl: null,
      lastImageUrl: null,
      lastContentId: null,
      areaElementsByIndex: {},
      activeAreaIndex: null,
      activateAreaByIndex: null,
    };

    state.closeBtn.addEventListener("click", closeInteractiveMap);
    modal.addEventListener("click", (event) => {
      if (event.target === modal) closeInteractiveMap();
    });

    interactiveMapState = state;
    return state;
  }

  function buildAreaPopup(canvas) {
    const popup = document.createElement("div");
    popup.className = "interactive-map-popup";
    popup.setAttribute("role", "status");
    popup.classList.add("hidden");
    canvas.appendChild(popup);
    return popup;
  }

  function placePopupNearPoint(popup, stage, clientX, clientY) {
    const stageRect = stage.getBoundingClientRect();
    const pad = 12;
    const popupRect = popup.getBoundingClientRect();
    let left = clientX - stageRect.left + 16;
    let top = clientY - stageRect.top + 16;

    if (left + popupRect.width + pad > stageRect.width) {
      left = stageRect.width - popupRect.width - pad;
    }
    if (top + popupRect.height + pad > stageRect.height) {
      top = stageRect.height - popupRect.height - pad;
    }
    left = Math.max(pad, left);
    top = Math.max(pad, top);

    popup.style.left = `${left}px`;
    popup.style.top = `${top}px`;
  }

  function showAreaPopup(areaCfg, event, stage) {
    const state = interactiveMapState;
    if (!state.popup) {
      state.popup = buildAreaPopup(stage);
    }
    state.popup.innerHTML = `
      <div class="interactive-map-popup-title">${escapeHtml(areaCfg.title)}</div>
      <div class="interactive-map-popup-body">${escapeHtml(areaCfg.popup)}</div>
    `;
    state.popup.classList.remove("hidden");
    placePopupNearPoint(state.popup, stage, event.clientX, event.clientY);
  }

  function resolveMapImageUrl(contentItem) {
    if (INTERACTIVE_MAP_CONFIG.baseImageUrl) {
      return INTERACTIVE_MAP_CONFIG.baseImageUrl;
    }
    const candidate = (contentItem.media || []).find((item) => item && item.type === "image" && (item.full_url || item.url));
    return candidate ? (candidate.full_url || candidate.url) : "";
  }

  async function renderInteractiveMapSvg(stage, imageUrl, contentItem) {
    const state = interactiveMapState;
    const canvas = state.canvas || stage;
    if (
      state.lastSvgUrl === INTERACTIVE_MAP_CONFIG.svgUrl &&
      state.lastImageUrl === imageUrl &&
      state.lastContentId === contentItem?.id &&
      canvas.querySelector("svg")
    ) {
      return;
    }
    const response = await fetch(INTERACTIVE_MAP_CONFIG.svgUrl, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Não foi possível carregar o SVG do mapa.");
    }
    const svgText = await response.text();
    const parsed = new DOMParser().parseFromString(svgText, "image/svg+xml");
    const svgRoot = parsed.documentElement;
    svgRoot.classList.add("interactive-map-svg");
    svgRoot.removeAttribute("width");
    svgRoot.removeAttribute("height");

    const frameRect = svgRoot.querySelector("rect");
    if (frameRect && imageUrl) {
      const svgNs = "http://www.w3.org/2000/svg";
      const imageNode = document.createElementNS(svgNs, "image");
      imageNode.setAttribute("href", imageUrl);
      imageNode.setAttribute("x", frameRect.getAttribute("x") || "0");
      imageNode.setAttribute("y", frameRect.getAttribute("y") || "0");
      imageNode.setAttribute("width", frameRect.getAttribute("width") || "100%");
      imageNode.setAttribute("height", frameRect.getAttribute("height") || "100%");
      // Exact frame fit keeps traced overlays aligned with source map.
      imageNode.setAttribute("preserveAspectRatio", "none");
      imageNode.classList.add("interactive-map-base-image");
      svgRoot.insertBefore(imageNode, svgRoot.firstChild);
    }

    const paths = Array.from(svgRoot.querySelectorAll("path"));
    const areaDataByIndex = mapAreasByIndex(contentItem);
    state.areaElementsByIndex = {};
    state.activeAreaIndex = null;

    state.activateAreaByIndex = (areaIndex, event) => {
      const target = state.areaElementsByIndex[areaIndex];
      if (!target) return;
      const mapArea = areaDataByIndex[areaIndex];
      const areaCfg = getInteractiveMapAreaConfig(areaIndex, mapArea);
      svgRoot.querySelectorAll(".interactive-map-area.active").forEach((el) => el.classList.remove("active"));
      Object.values(state.areaElementsByIndex).forEach((el) => {
        if (el && el.dataset.baseFill) {
          el.style.fill = el.dataset.baseFill;
        }
      });
      target.classList.add("active");
      if (target.dataset.activeFill) {
        target.style.fill = target.dataset.activeFill;
      }
      state.activeAreaIndex = areaIndex;
      setLegendActive(areaIndex);

      let clickEvent = event;
      if (!clickEvent) {
        const rect = target.getBoundingClientRect();
        clickEvent = {
          clientX: rect.left + rect.width / 2,
          clientY: rect.top + rect.height / 2,
        };
      }
      showAreaPopup(areaCfg, clickEvent, canvas);
    };

    let interactiveIndex = 0;
    paths.forEach((path) => {
      const currentIndex = interactiveIndex;
      const areaCfg = getInteractiveMapAreaConfig(currentIndex, areaDataByIndex[currentIndex]);
      // The source SVG defines `.cls-1 { fill: none; }`; set inline style so areas stay clickable.
      path.style.fill = areaCfg.color;
      path.style.stroke = areaCfg.stroke;
      path.style.strokeWidth = "1px";
      path.style.cursor = "pointer";
      path.style.pointerEvents = "all";
      path.dataset.baseFill = areaCfg.color;
      path.dataset.activeFill = toActiveFillColor(areaCfg.color);
      path.classList.add("interactive-map-area");
      path.dataset.mapAreaIndex = String(currentIndex);
      state.areaElementsByIndex[currentIndex] = path;
      path.addEventListener("mouseenter", () => {
        path.classList.add("hovered");
      });
      path.addEventListener("mouseleave", () => {
        path.classList.remove("hovered");
      });
      path.addEventListener("click", (event) => {
        event.stopPropagation();
        state.activateAreaByIndex(currentIndex, event);
      });
      interactiveIndex += 1;
    });

    if (frameRect) {
      frameRect.classList.add("interactive-map-frame");
      frameRect.setAttribute("fill", "none");
      frameRect.setAttribute("stroke", "rgba(255,255,255,0.08)");
    }

    canvas.querySelectorAll(".interactive-map-svg").forEach((el) => el.remove());
    canvas.appendChild(svgRoot);
    renderAreaIndexLabels(svgRoot, state.areaElementsByIndex);
    canvas.onclick = () => {
      if (interactiveMapState.popup) {
        interactiveMapState.popup.classList.add("hidden");
      }
      canvas.querySelectorAll(".interactive-map-area.active").forEach((el) => el.classList.remove("active"));
      Object.values(interactiveMapState.areaElementsByIndex).forEach((el) => {
        if (el && el.dataset.baseFill) {
          el.style.fill = el.dataset.baseFill;
        }
      });
      interactiveMapState.activeAreaIndex = null;
      setLegendActive(-1);
    };

    state.lastSvgUrl = INTERACTIVE_MAP_CONFIG.svgUrl;
    state.lastImageUrl = imageUrl;
    state.lastContentId = contentItem?.id || null;
  }

  async function openInteractiveMap(contentItem) {
    const state = ensureInteractiveMapModal();
    const itemTitle = sectionLabel(contentItem);
    state.title.textContent = `${itemTitle} - Mapa Interativo`;

    const imageUrl = resolveMapImageUrl(contentItem);
    renderLegend(contentItem);

    if (!state.popup) {
      state.popup = buildAreaPopup(state.canvas || state.stage);
    } else {
      state.popup.classList.add("hidden");
    }

    try {
      await renderInteractiveMapSvg(state.stage, imageUrl, contentItem);
      state.legend.querySelectorAll(".interactive-map-legend-item").forEach((item) => {
        item.addEventListener("click", (event) => {
          event.stopPropagation();
          const idx = Number(item.dataset.areaIndex);
          if (!Number.isNaN(idx) && state.activateAreaByIndex) {
            state.activateAreaByIndex(idx);
          }
        });
      });
      state.modal.classList.add("visible");
    } catch (error) {
      state.stage.innerHTML = `<div class="interactive-map-error">Erro ao carregar mapa interativo.</div>`;
      state.modal.classList.add("visible");
    }
  }

  // ── Uso dos Solos — year-comparison map ──────────────────────────────────
  function shouldShowUsoSolosMap(contentItem) {
    return contentItem && contentItem.slug === USO_SOLOS_SLUG;
  }

  function openUsoSolosMap() {
    const state = ensureInteractiveMapModal();
    const cfg = USO_SOLOS_CONFIG;
    let activeYear = cfg.years[0];

    state.title.textContent = "Uso dos Solos";

    // Build canvas content
    state.canvas.innerHTML = `
      <div class="uso-solos-img-wrap">
        ${cfg.years.map(y => `
          <img class="uso-solos-img${y === activeYear ? ' active' : ''}"
               data-year="${y}"
               src="${cfg.images[y]}"
               alt="Uso dos Solos ${y}" />
        `).join('')}
      </div>
      <div class="uso-solos-btns">
        ${cfg.years.map(y => `
          <button class="uso-solos-year-btn${y === activeYear ? ' active' : ''}" data-year="${y}">${y}</button>
        `).join('')}
      </div>
    `;

    // Legend
    state.legend.innerHTML = `
      <img class="uso-solos-legend" src="${cfg.legendUrl}" alt="Legenda" />
    `;

    // Year switching with crossfade
    state.canvas.querySelectorAll(".uso-solos-year-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const year = btn.dataset.year;
        if (year === activeYear) return;
        activeYear = year;
        state.canvas.querySelectorAll(".uso-solos-year-btn").forEach(b => b.classList.toggle("active", b.dataset.year === year));
        state.canvas.querySelectorAll(".uso-solos-img").forEach(img => img.classList.toggle("active", img.dataset.year === year));
      });
    });

    state.modal.classList.add("visible");
  }

  function appendUsoSolosButton(contentItem) {
    if (!shouldShowUsoSolosMap(contentItem)) return;
    const actions = document.createElement("div");
    actions.className = "interactive-map-actions";
    actions.innerHTML = `<button type="button" class="view-map-btn">VER MAPA</button>`;
    actions.querySelector(".view-map-btn").addEventListener("click", openUsoSolosMap);
    contentBody.appendChild(actions);
  }
  // ─────────────────────────────────────────────────────────────────────────

  function appendInteractiveMapButton(contentItem) {
    if (!shouldShowInteractiveMap(contentItem)) return;
    const actions = document.createElement("div");
    actions.className = "interactive-map-actions";
    actions.innerHTML = `
      <button type="button" class="view-map-btn">VER MAPA</button>
    `;
    const btn = actions.querySelector(".view-map-btn");
    btn.addEventListener("click", () => {
      openInteractiveMap(contentItem);
    });
    contentBody.appendChild(actions);
  }

  function buildMenu() {
    menu.innerHTML = sections
      .map(
        (section) => `
          <div class="menu-item" data-section="${section.slug}">
            <div class="menu-connector"></div>
            <div class="menu-node"></div>
            <div class="menu-label">${sectionLabel(section)}</div>
          </div>
        `
      )
      .join("");

    menu.querySelectorAll(".menu-item").forEach((item) => {
      // Restore active state after language rebuild
      if (item.dataset.section === activeSectionSlug) {
        item.classList.add("active");
      }
      item.addEventListener("click", () => {
        const slug = item.dataset.section;
        if (slug === activeSectionSlug) {
          hideContent();
        } else {
          showSection(slug, item);
        }
      });
    });
  }

  function getSectionBySlug(slug) {
    return sections.find((s) => s.slug === slug);
  }

  // ── Lightbox state ────────────────────────────────────────────────────────
  let lightboxItems = [];   // flat array of all image items in current view
  let lightboxIndex = 0;    // currently shown index
  let lightboxEl = null;    // cached modal element

  function ensureLightbox() {
    if (lightboxEl) return lightboxEl;
    const el = document.createElement("div");
    el.id = "lightbox-modal";
    el.innerHTML = `
      <div class="lightbox-dialog">
        <div class="lightbox-top">
          <span class="lightbox-counter"></span>
          <button class="lightbox-close" aria-label="Fechar">✕</button>
        </div>
        <div class="lightbox-stage">
          <button class="lightbox-nav lightbox-prev" aria-label="Anterior">‹</button>
          <div class="lightbox-img-wrap">
            <img class="lightbox-img" src="" alt="" />
          </div>
          <button class="lightbox-nav lightbox-next" aria-label="Seguinte">›</button>
        </div>
        <div class="lightbox-caption"></div>
      </div>
    `;
    document.body.appendChild(el);

    const img     = el.querySelector(".lightbox-img");
    const caption = el.querySelector(".lightbox-caption");
    const counter = el.querySelector(".lightbox-counter");
    const prev    = el.querySelector(".lightbox-prev");
    const next    = el.querySelector(".lightbox-next");

    function refreshLightbox() {
      const item = lightboxItems[lightboxIndex];
      img.src     = item.full_url || item.url;
      img.alt     = mediaCaption(item);
      caption.textContent = mediaCaption(item);
      counter.textContent = `${lightboxIndex + 1} / ${lightboxItems.length}`;
      prev.classList.toggle("nav-invisible", lightboxIndex === 0);
      next.classList.toggle("nav-invisible", lightboxIndex === lightboxItems.length - 1);
    }

    prev.addEventListener("click", () => { if (lightboxIndex > 0) { lightboxIndex--; refreshLightbox(); } });
    next.addEventListener("click", () => { if (lightboxIndex < lightboxItems.length - 1) { lightboxIndex++; refreshLightbox(); } });
    el.querySelector(".lightbox-close").addEventListener("click", closeLightbox);
    el.addEventListener("click", (e) => { if (e.target === el) closeLightbox(); });

    el._refresh = refreshLightbox;
    lightboxEl = el;
    return el;
  }

  function openLightbox(index) {
    lightboxIndex = index;
    const el = ensureLightbox();
    el._refresh();
    el.classList.add("visible");
  }

  function closeLightbox() {
    if (lightboxEl) lightboxEl.classList.remove("visible");
  }
  // ─────────────────────────────────────────────────────────────────────────

  function updateMedia(media, imagesOnlyMode) {
    const allItems = (media || []).filter((m) => m.url);
    const groups = buildMediaGroups(allItems);
    _lbCounter = 0;

    // Build flat lightbox array (images only, in group order)
    lightboxItems = [];
    groups.forEach((g) => g.items.forEach((item) => {
      if (item.type !== "video") lightboxItems.push(item);
    }));

    contentImages.innerHTML = groups.map(renderMediaGroup).join("");
    bindGroupedMediaControls();
    bindLightboxTriggers();

    if (imagesOnlyMode) {
      contentArea.classList.add("images-only");
    } else {
      contentArea.classList.remove("images-only");
    }
  }

  function bindLightboxTriggers() {
    // no-op: delegation handled by the single listener set up at init
  }

  function mediaCaption(item) {
    if (currentLang === "en") return item.caption_en || item.caption || "";
    return item.caption || item.caption_en || "";
  }

  function buildMediaGroups(items) {
    const groups = [];
    const groupedByKey = {};

    items.forEach((item, idx) => {
      // Use explicit group field if set, otherwise treat as standalone
      const key = (item.group || "").trim();
      if (key && groupedByKey[key]) {
        groupedByKey[key].items.push(item);
        return;
      }
      const group = {
        id: key ? `group-${key}-${groups.length}` : `single-${idx}`,
        key,
        caption: mediaCaption(item),
        items: [item],
      };
      groups.push(group);
      if (key) groupedByKey[key] = group;
    });

    return groups;
  }

  function renderMediaItem(item) {
    if (item.type === "video") {
      return `<video class="media-asset" src="${item.url}" controls preload="metadata"></video>`;
    }
    return `<img class="media-asset" src="${item.url}" alt="${mediaCaption(item)}">`;
  }

  // Counter shared across all groups per render pass — gives each image its flat lightbox index
  let _lbCounter = 0;

  function renderMediaGroup(group) {
    if (group.items.length === 1) {
      const item = group.items[0];
      const lbAttr = item.type !== "video" ? `data-lightbox-index="${_lbCounter++}"` : "";
      return `
        <div class="content-image">
          <div class="media-frame" ${lbAttr}>
            ${renderMediaItem(item)}
          </div>
          <div class="caption">${mediaCaption(item)}</div>
        </div>
      `;
    }

    return `
      <div class="content-image-group">
        <div class="content-image-carousel" data-group-id="${group.id}">
          <button class="media-nav prev" aria-label="Imagem anterior">‹</button>
          <div class="media-slides">
            ${group.items
              .map((item, index) => {
                const lbAttr = item.type !== "video" ? `data-lightbox-index="${_lbCounter++}"` : "";
                return `
                  <div class="media-slide ${index === 0 ? "active" : ""}" data-slide-index="${index}">
                    <div class="media-frame" ${lbAttr}>
                      ${renderMediaItem(item)}
                    </div>
                  </div>
                `;
              })
              .join("")}
          </div>
          <div class="media-counter">1/${group.items.length}</div>
          <button class="media-nav next" aria-label="Próxima imagem">›</button>
        </div>
        <div class="caption">${mediaCaption(group.items[0])}</div>
      </div>
    `;
  }

  function bindGroupedMediaControls() {
    contentImages.querySelectorAll(".content-image-carousel").forEach((carousel) => {
      const slides = Array.from(carousel.querySelectorAll(".media-slide"));
      if (slides.length <= 1) return;
      let activeIndex = 0;
      const counter = carousel.querySelector(".media-counter");

      const update = () => {
        slides.forEach((slide, idx) => {
          slide.classList.toggle("active", idx === activeIndex);
        });
        if (counter) {
          counter.textContent = `${activeIndex + 1}/${slides.length}`;
        }
        if (prev) {
          prev.classList.toggle("hidden", activeIndex === 0);
        }
        if (next) {
          next.classList.toggle("hidden", activeIndex === slides.length - 1);
        }
      };

      const prev = carousel.querySelector(".media-nav.prev");
      const next = carousel.querySelector(".media-nav.next");

      prev.addEventListener("click", (e) => {
        e.stopPropagation();
        if (activeIndex > 0) {
          activeIndex -= 1;
        }
        update();
      });

      next.addEventListener("click", (e) => {
        e.stopPropagation();
        if (activeIndex < slides.length - 1) {
          activeIndex += 1;
        }
        update();
      });

      update();
    });
  }

  function hasRenderableText(value) {
    if (!value) return false;
    const stripped = String(value)
      .replace(/<[^>]*>/g, " ")
      .replace(/&nbsp;/gi, " ")
      .trim();
    return stripped.length > 0;
  }

  function hasRenderableMedia(media) {
    return (media || []).some((item) => item && item.url);
  }

  function resolveDisplayNode(node) {
    if (!node) return null;
    // Keep this node visible as a project hub even if it has no own body/media.
    if (node.slug === "parceiros-e-projetos") {
      return node;
    }
    if (hasRenderableText(node.content) || hasRenderableMedia(node.media)) {
      return node;
    }
    for (const child of node.children || []) {
      const found = resolveDisplayNode(child);
      if (found) return found;
    }
    return node;
  }

  function updateBody(contentItem) {
    if (contentItem.slug === "parceiros-e-projetos" && (contentItem.children || []).length) {
      contentArea.classList.add("project-grid");
      contentArea.classList.remove("images-only");
      contentBody.classList.remove("hidden");
      contentImages.classList.add("hidden");
      contentImages.innerHTML = "";
      contentBody.innerHTML = `
        <div class="projects-grid">
          ${(contentItem.children || [])
            .map((child) => {
              const cover = (child.media || []).find((m) => m.url);
              return `
                <button class="project-card" data-project-id="${child.id}">
                  ${
                    cover
                      ? `<img src="${cover.url}" alt="${sectionLabel(child)}">`
                      : `<div class="project-card-placeholder"></div>`
                  }
                  <div class="project-card-title">${sectionLabel(child)}</div>
                </button>
              `;
            })
            .join("")}
        </div>
      `;

      contentBody.querySelectorAll(".project-card").forEach((card) => {
        card.addEventListener("click", () => {
          const targetId = Number(card.dataset.projectId);
          const target = (contentItem.children || []).find((child) => child.id === targetId);
          if (!target) return;
          contentSubnav.querySelectorAll(".content-subnav-item").forEach((item) => {
            item.classList.toggle("active", Number(item.dataset.contentId) === targetId);
          });
          updateBody(target);
        });
      });
      return;
    }

    contentArea.classList.remove("project-grid");
    const html = (currentLang === "en" && contentItem.content_en)
      ? contentItem.content_en
      : (contentItem.content || "");
    const itemTitle = sectionLabel(contentItem);
    const fallback = html
      .split("\n")
      .filter(Boolean)
      .map((line) => `<p>${line}</p>`)
      .join("");
    const hasText = hasRenderableText(html);

    if (hasText) {
      const bodyHtml = html.includes("<") ? html : fallback;
      contentBody.innerHTML = `
        <h3 class="content-item-title">${itemTitle}</h3>
        ${bodyHtml}
      `;
      appendInteractiveMapButton(contentItem);
      appendUsoSolosButton(contentItem);
      contentBody.classList.remove("hidden");
    } else {
      contentBody.innerHTML = `
        <h3 class="content-item-title">${itemTitle}</h3>
      `;
      appendInteractiveMapButton(contentItem);
      appendUsoSolosButton(contentItem);
      contentBody.classList.remove("hidden");
    }
    contentImages.classList.remove("hidden");

    updateMedia(contentItem.media, !hasText);
  }

  function flattenTree(nodes, depth, bucket) {
    (nodes || []).forEach((node) => {
      bucket.push({ node, depth });
      flattenTree(node.children || [], depth + 1, bucket);
    });
  }

  function renderSubnav(rootNode) {
    // For 3.3.4.1 we show projects as grid cards, not in the side subnav.
    if (rootNode && rootNode.slug === "parceiros-e-projetos") {
      contentSubnav.classList.remove("hidden");
      contentArea.classList.add("has-subnav");
      const children = rootNode.children || [];
      contentSubnav.innerHTML = children
        .map(
          (node) => `
            <div class="content-subnav-item" data-content-id="${node.id}">
              ${sectionLabel(node)}
            </div>
          `
        )
        .join("");
      return {
        setActive(contentId) {
          contentSubnav.querySelectorAll(".content-subnav-item").forEach((el) => {
            el.classList.toggle("active", String(contentId) === el.dataset.contentId);
            if (el.classList.contains("active")) {
              el.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
            }
          });
        },
      };
    }

    const treeRows = [];
    flattenTree(rootNode.children || [], 0, treeRows);
    if (!treeRows.length) {
      contentSubnav.classList.add("hidden");
      contentArea.classList.remove("has-subnav");
      contentSubnav.innerHTML = "";
      return { setActive: () => {} };
    }

    contentSubnav.classList.remove("hidden");
    contentArea.classList.add("has-subnav");
    contentSubnav.innerHTML = treeRows
      .map(
        ({ node, depth }) => `
          <div class="content-subnav-item depth-${Math.min(depth, 2)}" data-content-id="${node.id}">
            ${sectionLabel(node)}
          </div>
        `
      )
      .join("");

    return {
      setActive(contentId) {
        contentSubnav.querySelectorAll(".content-subnav-item").forEach((el) => {
          el.classList.toggle("active", String(contentId) === el.dataset.contentId);
          if (el.classList.contains("active")) {
            el.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
          }
        });
      },
    };
  }

  function renderTabs(section) {
    const roots = section.contents || [];
    if (roots.length <= 1) {
      contentTabs.classList.remove("has-tabs");
      contentTabs.innerHTML = "";
      if (roots[0]) {
        contentTitle.textContent = sectionLabel(section);
        let activeNode = resolveDisplayNode(roots[0]);
        const subnav = renderSubnav(roots[0]);
        subnav.setActive(activeNode.id);
        updateBody(activeNode);

        contentSubnav.querySelectorAll(".content-subnav-item").forEach((item) => {
          item.addEventListener("click", () => {
            const targetId = Number(item.dataset.contentId);
            const stack = [];
            flattenTree(roots[0].children || [], 0, stack);
            const found = stack.find((row) => row.node.id === targetId);
            if (!found) return;
            activeNode = found.node;
            subnav.setActive(activeNode.id);
            updateBody(activeNode);
          });
        });
      } else {
        contentTitle.textContent = sectionLabel(section);
        contentBody.innerHTML = "<p>Sem conteúdo disponível.</p>";
        contentImages.innerHTML = "";
        contentSubnav.classList.add("hidden");
        contentSubnav.innerHTML = "";
      }
      return;
    }

    contentTabs.classList.add("has-tabs");
    contentTabs.innerHTML = roots
      .map(
        (item, idx) => `
          <button class="tab-btn ${idx === 0 ? "active" : ""}" data-content-id="${item.id}">
            ${sectionLabel(item)}
          </button>
        `
      )
      .join("");

    const first = roots[0];
    let activeNode = resolveDisplayNode(first);
    const subnav = renderSubnav(first);
    contentTitle.textContent = sectionLabel(section);
    subnav.setActive(activeNode.id);
    updateBody(activeNode);

    contentSubnav.querySelectorAll(".content-subnav-item").forEach((item) => {
      item.addEventListener("click", () => {
        const targetId = Number(item.dataset.contentId);
        const stack = [];
        flattenTree(activeNode.children ? [activeNode] : [first], 0, stack);
        const found = stack.find((row) => row.node.id === targetId);
        if (!found) return;
        activeNode = found.node;
        subnav.setActive(activeNode.id);
        updateBody(activeNode);
      });
    });

    contentTabs.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        contentTabs.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const selected = roots.find((item) => String(item.id) === btn.dataset.contentId);
        if (selected) {
          activeNode = resolveDisplayNode(selected);
          const nextSubnav = renderSubnav(selected);
          nextSubnav.setActive(activeNode.id);
          updateBody(activeNode);
          contentSubnav.querySelectorAll(".content-subnav-item").forEach((subItem) => {
            subItem.addEventListener("click", () => {
              const targetId = Number(subItem.dataset.contentId);
              const stack = [];
              flattenTree(selected.children || [], 0, stack);
              const found = stack.find((row) => row.node.id === targetId);
              if (!found) return;
              activeNode = found.node;
              nextSubnav.setActive(activeNode.id);
              updateBody(activeNode);
            });
          });
        }
      });
    });
  }

  function restartAnimation(el) {
    el.classList.remove("animating", "closing");
    void el.offsetWidth; // force reflow so animation restarts
  }

  function animateLine(item) {
    const node = item.querySelector(".menu-node");
    const rect = node.getBoundingClientRect();
    const x = rect.right;  // right edge of the dot — no gap
    const y = rect.top + rect.height / 2;
    const targetX = 460; // left edge of content panel

    // Horizontal line
    restartAnimation(connectionLine);
    connectionLine.style.top   = `${y}px`;
    connectionLine.style.left  = `${x}px`;
    connectionLine.style.width = `${Math.max(20, targetX - x)}px`;
    connectionLine.classList.add("animating");

    // Vertical line UP — grows from connection point upward to content top
    const contentTop = 160;
    restartAnimation(verticalLineUp);
    verticalLineUp.style.left   = `${targetX}px`;
    verticalLineUp.style.top    = `${contentTop}px`;
    verticalLineUp.style.height = `${Math.max(0, y - contentTop)}px`;
    verticalLineUp.classList.add("animating");

    // Vertical line DOWN — grows from connection point downward to content bottom
    const contentBottom = window.innerHeight - 50;
    restartAnimation(verticalLineDown);
    verticalLineDown.style.left   = `${targetX}px`;
    verticalLineDown.style.top    = `${y}px`;
    verticalLineDown.style.height = `${Math.max(0, contentBottom - y)}px`;
    verticalLineDown.classList.add("animating");
  }

  function hideLines(callback) {
    verticalLineUp.classList.remove("animating");
    verticalLineUp.classList.add("closing");
    verticalLineDown.classList.remove("animating");
    verticalLineDown.classList.add("closing");
    setTimeout(() => {
      connectionLine.classList.remove("animating");
      connectionLine.classList.add("closing");
    }, 100);
    setTimeout(() => {
      connectionLine.classList.remove("closing");
      verticalLineUp.classList.remove("closing");
      verticalLineDown.classList.remove("closing");
      if (callback) callback();
    }, 350);
  }

  function showSection(slug, item) {
    const section = getSectionBySlug(slug);
    if (!section) return;

    // If switching menus, fade out content first then re-animate
    if (activeSectionSlug && activeSectionSlug !== slug) {
      contentPanel.classList.remove("visible");
      setTimeout(() => {
        activeSectionSlug = slug;
        menu.querySelectorAll(".menu-item").forEach((el) => {
          el.classList.toggle("active", el.dataset.section === slug);
        });
        animateLine(item);
        renderTabs(section);
        setTimeout(() => contentPanel.classList.add("visible"), 300);
      }, 200);
      return;
    }

    activeSectionSlug = slug;
    menu.querySelectorAll(".menu-item").forEach((el) => {
      el.classList.toggle("active", el.dataset.section === slug);
    });
    animateLine(item);
    renderTabs(section);
    // Delay fade-in to let the horizontal line grow first (~300ms)
    setTimeout(() => contentPanel.classList.add("visible"), 300);
  }

  function hideContent() {
    activeSectionSlug = null;
    closeInteractiveMap();
    // Fade panel out first, then shrink lines
    contentPanel.classList.remove("visible");
    setTimeout(() => {
      hideLines();
      menu.querySelectorAll(".menu-item").forEach((el) => el.classList.remove("active"));
      contentSubnav.classList.add("hidden");
      contentArea.classList.remove("has-subnav");
      contentSubnav.innerHTML = "";
    }, 250);
  }

  closeBtn.addEventListener("click", hideContent);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeLightbox();
      closeInteractiveMap();
    }
  });

  // Basic kiosk hardening for accidental browser gestures.
  document.addEventListener("contextmenu", (e) => e.preventDefault());
  document.addEventListener("dragstart", (e) => e.preventDefault());
  document.addEventListener("touchmove", (e) => {
    if (e.touches && e.touches.length > 1) e.preventDefault();
  }, { passive: false });

  function initThree() {
    const loadingEl = document.getElementById("loading");
    const container = document.getElementById("canvas-container");
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x2d2d2d);

    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(1.2, 0.7, 1.2);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.autoRotate = true;
    controls.autoRotateSpeed = -0.3;
    controls.minPolarAngle = 0.1;
    controls.maxPolarAngle = Math.PI / 2 - 0.1;
    controls.minDistance = 1;
    controls.maxDistance = 4;

    const loader = new THREE.GLTFLoader();
    if (!modelUrl) {
      loadingEl.innerHTML = "<p>Modelo 3D indisponível.</p>";
      return;
    }

    // Color map for named meshes in the multic.glb two-mesh model.
    // Falls back to orange for any unrecognised mesh name (e.g. furnas_10.glb).
    const WIREFRAME_COLORS = {
      mosaico_dentro: new THREE.Color(0xf8992c), // highlight — orange
      mosaico_fora:   new THREE.Color(0x5a5a5a), // base terrain — dark grey
    };
    const DEFAULT_WIREFRAME_COLOR = new THREE.Color(0xf8992c);

    loader.load(
      modelUrl,
      (gltf) => {
        const model = gltf.scene;
        const wireframeGroup = new THREE.Group();
        model.traverse((child) => {
          if (!child.isMesh) return;
          child.updateWorldMatrix(true, false);
          const geo = child.geometry.clone();
          geo.applyMatrix4(child.matrixWorld);
          const wf = new THREE.WireframeGeometry(geo);
          const colorKey = Object.keys(WIREFRAME_COLORS).find(k => child.name.startsWith(k));
          const color = colorKey ? WIREFRAME_COLORS[colorKey] : DEFAULT_WIREFRAME_COLOR;
          const mat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.9 });
          wireframeGroup.add(new THREE.LineSegments(wf, mat));
        });
        scene.add(wireframeGroup);
        const box = new THREE.Box3().setFromObject(wireframeGroup);
        const size = box.getSize(new THREE.Vector3());
        const scale = 4 / Math.max(size.x, size.y, size.z);
        wireframeGroup.scale.setScalar(scale);
        const center = new THREE.Box3().setFromObject(wireframeGroup).getCenter(new THREE.Vector3());
        wireframeGroup.position.set(-center.x, -center.y, -center.z);
        controls.target.set(0, 0, 0);
        controls.update();
        loadingEl.classList.add("hidden");
      },
      undefined,
      () => {
        loadingEl.innerHTML = "<p>Modelo 3D indisponível.</p>";
      }
    );

    function animate() {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }
    animate();

    window.addEventListener("resize", () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });
  }

  buildMenu();

  // Delegated lightbox listener — one handler for all current and future images
  contentImages.addEventListener("click", (e) => {
    const img = e.target.closest("[data-lightbox-index]");
    if (!img) return;
    const idx = parseInt(img.dataset.lightboxIndex, 10);
    openLightbox(idx);
  });

  initThree();
})();
