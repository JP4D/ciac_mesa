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

  let activeSectionSlug = null;

  function sectionLabel(section) {
    const label = section.title || section.slug;
    return label.replace(/^\d+(\.\d+)?\s*-\s*/g, "");
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

  function updateMedia(media, imagesOnlyMode) {
    const items = (media || []).filter((m) => m.url);
    const groups = buildMediaGroups(items);
    contentImages.innerHTML = groups.map(renderMediaGroup).join("");
    bindGroupedMediaControls();

    if (imagesOnlyMode) {
      contentArea.classList.add("images-only");
    } else {
      contentArea.classList.remove("images-only");
    }
  }

  function mediaCaption(item) {
    return item.caption || item.caption_en || "";
  }

  function captionKey(item) {
    return (item.caption || "").trim().toLowerCase();
  }

  function buildMediaGroups(items) {
    const groups = [];
    const groupedByCaption = {};

    items.forEach((item, idx) => {
      const key = captionKey(item);
      if (key && groupedByCaption[key]) {
        groupedByCaption[key].items.push(item);
        return;
      }
      const group = {
        id: key ? `caption-${groups.length}` : `single-${idx}`,
        key,
        caption: mediaCaption(item),
        items: [item],
      };
      groups.push(group);
      if (key) groupedByCaption[key] = group;
    });

    return groups;
  }

  function renderMediaItem(item, active) {
    if (item.type === "video") {
      return `<video class="media-asset" src="${item.url}" controls preload="metadata"${active ? ' class="active"' : ""}></video>`;
    }
    return `<img class="media-asset" src="${item.url}" alt="${mediaCaption(item)}"${active ? ' class="active"' : ""}>`;
  }

  function renderMediaGroup(group) {
    if (group.items.length === 1) {
      const item = group.items[0];
      return `
        <div class="content-image">
          <div class="media-frame">
            ${renderMediaItem(item, false)}
          </div>
          <div class="caption">${group.caption}</div>
        </div>
      `;
    }

    return `
      <div class="content-image-group">
        <div class="content-image-carousel" data-group-id="${group.id}">
          <button class="media-nav prev" aria-label="Imagem anterior">‹</button>
          <div class="media-slides">
            ${group.items
              .map(
                (item, index) => `
                  <div class="media-slide ${index === 0 ? "active" : ""}" data-slide-index="${index}">
                    <div class="media-frame">
                      ${renderMediaItem(item, index === 0)}
                    </div>
                  </div>
                `
              )
              .join("")}
          </div>
          <button class="media-nav next" aria-label="Próxima imagem">›</button>
        </div>
        <div class="caption">${group.caption}</div>
      </div>
    `;
  }

  function bindGroupedMediaControls() {
    contentImages.querySelectorAll(".content-image-carousel").forEach((carousel) => {
      const slides = Array.from(carousel.querySelectorAll(".media-slide"));
      if (slides.length <= 1) return;
      let activeIndex = 0;

      const update = () => {
        slides.forEach((slide, idx) => {
          slide.classList.toggle("active", idx === activeIndex);
        });
      };

      const prev = carousel.querySelector(".media-nav.prev");
      const next = carousel.querySelector(".media-nav.next");

      prev.addEventListener("click", (e) => {
        e.stopPropagation();
        activeIndex = (activeIndex - 1 + slides.length) % slides.length;
        update();
      });

      next.addEventListener("click", (e) => {
        e.stopPropagation();
        activeIndex = (activeIndex + 1) % slides.length;
        update();
      });
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
          updateBody(target);
        });
      });
      return;
    }

    contentArea.classList.remove("project-grid");
    const html = contentItem.content || "";
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
      contentBody.classList.remove("hidden");
    } else {
      contentBody.innerHTML = `
        <h3 class="content-item-title">${itemTitle}</h3>
      `;
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
      contentSubnav.innerHTML = "";
      return { setActive: () => {} };
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

  function animateLine(item) {
    const nodeRect = item.querySelector(".menu-node").getBoundingClientRect();
    const y = nodeRect.top + nodeRect.height / 2;
    const xStart = nodeRect.left + nodeRect.width + 8;
    const xTarget = 455;
    connectionLine.style.top = `${y}px`;
    connectionLine.style.left = `${xStart}px`;
    connectionLine.style.width = `${Math.max(20, xTarget - xStart)}px`;
    connectionLine.style.transform = "scaleX(1)";

    const contentTop = 160;
    const contentBottom = window.innerHeight - 50;
    verticalLineUp.style.left = `${xTarget}px`;
    verticalLineDown.style.left = `${xTarget}px`;
    verticalLineUp.style.top = `${contentTop}px`;
    verticalLineUp.style.height = `${Math.max(0, y - contentTop)}px`;
    verticalLineUp.style.transform = "scaleY(1)";

    verticalLineDown.style.top = `${y}px`;
    verticalLineDown.style.height = `${Math.max(0, contentBottom - y)}px`;
    verticalLineDown.style.transform = "scaleY(1)";
  }

  function showSection(slug, item) {
    const section = getSectionBySlug(slug);
    if (!section) return;
    activeSectionSlug = slug;
    menu.querySelectorAll(".menu-item").forEach((el) => {
      el.classList.toggle("active", el.dataset.section === slug);
    });
    animateLine(item);
    renderTabs(section);
    contentPanel.classList.add("visible");
  }

  function hideContent() {
    activeSectionSlug = null;
    contentPanel.classList.remove("visible");
    menu.querySelectorAll(".menu-item").forEach((el) => el.classList.remove("active"));
    connectionLine.style.transform = "scaleX(0)";
    verticalLineUp.style.transform = "scaleY(0)";
    verticalLineDown.style.transform = "scaleY(0)";
    contentSubnav.classList.add("hidden");
    contentArea.classList.remove("has-subnav");
    contentSubnav.innerHTML = "";
  }

  closeBtn.addEventListener("click", hideContent);

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
          const mat = new THREE.LineBasicMaterial({ color: new THREE.Color(0xf8992c), transparent: true, opacity: 0.9 });
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
  initThree();
})();
