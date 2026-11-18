"use strict";

const state = {
  q: "",
  retailers: new Set(),
  categories: new Set(),
  minDiscount: 0,
  sort: "discount",
  scraping: false,
};

const CATEGORY_EMOJI = {
  "Obst": "🍎",
  "Gemüse": "🥕",
  "Fleisch & Wurst": "🥩",
  "Fisch & Meeresfrüchte": "🐟",
  "Milchprodukte & Eier": "🧀",
  "Brot & Gebäck": "🍞",
  "Süßes & Snacks": "🍫",
  "Tiefkühl & Fertig": "❄️",
  "Getränke": "🥤",
  "Alkohol": "🍺",
  "Grundnahrung & Vorrat": "🍝",
  "Drogerie & Haushalt": "🧴",
  "Haustier": "🐾",
  "Sonstiges": "📦",
};

// Groups highlighted by default in "Aktuelle Aktionen" (everything except the
// non-food catch-all, so pots/furniture/travel deals don't dominate the strip).
const HIGHLIGHT_GROUPS = Object.keys(CATEGORY_EMOJI).filter((g) => g !== "Sonstiges");

const el = {
  search: document.getElementById("search"),
  sort: document.getElementById("sort"),
  minDiscount: document.getElementById("minDiscount"),
  minDiscountVal: document.getElementById("minDiscountVal"),
  categories: document.getElementById("categories"),
  retailers: document.getElementById("retailers"),
  actionsSection: document.getElementById("actionsSection"),
  actionsStrip: document.getElementById("actionsStrip"),
  grid: document.getElementById("grid"),
  resultInfo: document.getElementById("resultInfo"),
  meta: document.getElementById("meta"),
};

// Shared filter params (retailer/category/search) used by both the main grid
// and the "Aktuelle Aktionen" highlights strip.
function filterParams() {
  const p = new URLSearchParams();
  if (state.q) p.set("q", state.q);
  if (state.retailers.size) p.set("retailer", [...state.retailers].join(","));
  if (state.categories.size) p.set("category", [...state.categories].join(","));
  return p;
}

function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

function fmtPrice(v) {
  return v == null ? "" : "€ " + v.toFixed(2).replace(".", ",");
}

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  return d.toLocaleDateString("de-AT", { day: "2-digit", month: "2-digit" });
}

async function loadMeta() {
  try {
    const m = await (await fetch("/api/meta")).json();
    const when = m.last_scrape ? new Date(m.last_scrape).toLocaleString("de-AT") : "—";
    state.scraping = !!m.scraping;
    let txt = `${m.active_offers ?? 0} aktive Angebote · zuletzt aktualisiert ${when}`;
    if (m.scraping) txt += " · ⏳ Aktualisierung läuft…";
    if (m.scrape_error) txt += " · ⚠️ Fehler beim Scrapen";
    el.meta.textContent = txt;
    return m;
  } catch {
    el.meta.textContent = "";
    return {};
  }
}

async function loadRetailers() {
  const list = await (await fetch("/api/retailers")).json();
  renderChips(el.retailers, list, "retailer", state.retailers, (r) => r.retailer);
}

async function loadCategories() {
  const list = await (await fetch("/api/categories")).json();
  renderChips(el.categories, list, "category", state.categories, (r) => {
    const emoji = CATEGORY_EMOJI[r.category] || "";
    return (emoji ? emoji + " " : "") + r.category;
  });
}

// Render a set of toggle chips into `container`. `selected` is the Set that
// tracks active values; `label` builds each chip's text. Preserves current
// selection across re-renders (e.g. when counts refresh during a scrape).
function renderChips(container, list, key, selected, label) {
  container.innerHTML = "";
  for (const item of list) {
    const value = item[key];
    const chip = document.createElement("span");
    chip.className = "chip" + (selected.has(value) ? " active" : "");
    chip.innerHTML = `${escapeHtml(label(item))}<span class="count">${item.count}</span>`;
    chip.onclick = () => {
      if (selected.has(value)) selected.delete(value);
      else selected.add(value);
      chip.classList.toggle("active");
      loadOffers();
    };
    container.appendChild(chip);
  }
}

// The highlights strip: strongest current % deals, honoring active filters.
async function loadActions() {
  const p = filterParams();
  // Default the strip to food/drugstore groups; an explicit category tick wins.
  if (!state.categories.size) p.set("category", HIGHLIGHT_GROUPS.join(","));
  p.set("min_discount", "25");
  p.set("sort", "discount");
  p.set("limit", "20");

  let offers = [];
  try {
    offers = await (await fetch("/api/offers?" + p)).json();
  } catch {
    offers = [];
  }

  el.actionsSection.hidden = offers.length === 0;
  el.actionsStrip.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const o of offers) frag.appendChild(renderActionCard(o));
  el.actionsStrip.appendChild(frag);
}

function renderActionCard(o) {
  const c = document.createElement("div");
  c.className = "action-card";
  const img = o.image_url
    ? `<img src="${o.image_url}" alt="" loading="lazy" onerror="this.parentNode.innerHTML='<span class=&quot;noimg&quot;>🛒</span>'">`
    : `<span class="noimg">🛒</span>`;
  const old = o.old_price ? `<s>${fmtPrice(o.old_price)}</s>` : "";
  c.innerHTML = `
    <div class="sticker">-${Math.round(o.discount_pct)}%</div>
    <div class="action-img">${img}</div>
    <div class="action-body">
      <div class="action-name">${escapeHtml(o.product_name || "")}</div>
      <div class="action-retailer">${escapeHtml(o.retailer || "")}</div>
      <div class="action-price">${fmtPrice(o.price)}${old}</div>
    </div>`;
  return c;
}

async function loadOffers() {
  loadActions(); // refresh highlights alongside the grid (runs concurrently)

  const p = filterParams();
  if (state.minDiscount > 0) p.set("min_discount", state.minDiscount);
  p.set("sort", state.sort);
  p.set("limit", "500");

  el.resultInfo.textContent = "lädt…";
  const offers = await (await fetch("/api/offers?" + p)).json();

  el.resultInfo.textContent = `${offers.length} Angebote`;
  el.grid.innerHTML = "";

  if (!offers.length) {
    el.grid.innerHTML = state.scraping
      ? `<div class="empty">⏳ Angebote werden geladen…<br>Der erste Scrape dauert etwa eine Minute. Die Seite füllt sich automatisch.</div>`
      : `<div class="empty">Keine Angebote gefunden.<br>Versuch es mit anderen Filtern.</div>`;
    return;
  }

  const frag = document.createDocumentFragment();
  for (const o of offers) frag.appendChild(renderCard(o));
  el.grid.appendChild(frag);
}

function renderCard(o) {
  const card = document.createElement("article");
  card.className = "card";

  const img = o.image_url
    ? `<img src="${o.image_url}" alt="" loading="lazy" onerror="this.parentNode.innerHTML='<span class=&quot;noimg&quot;>🛒</span>'">`
    : `<span class="noimg">🛒</span>`;

  const discount = o.discount_pct
    ? `<span class="discount-badge">-${Math.round(o.discount_pct)}%</span>`
    : "";

  const oldPrice = o.old_price && o.old_price > (o.price ?? 0)
    ? `<span class="old-price">${fmtPrice(o.old_price)}</span>`
    : "";

  const ref = o.reference_price && o.unit
    ? `<div class="refprice">${fmtPrice(o.reference_price)} / ${o.unit}</div>`
    : "";

  const valid = o.valid_to
    ? `<div class="valid">gültig bis ${fmtDate(o.valid_to)}</div>`
    : "";

  card.innerHTML = `
    <div class="card-img">${img}</div>
    <div class="card-body">
      <div class="badges">
        <span class="retailer-badge">${o.retailer || ""}</span>
        ${discount}
      </div>
      <div class="name">${escapeHtml(o.product_name || "")}</div>
      ${o.brand ? `<div class="brand">${escapeHtml(o.brand)}</div>` : ""}
      <div class="price-row">
        <span class="price">${fmtPrice(o.price)}</span>
        ${oldPrice}
      </div>
      ${ref}
      ${valid}
    </div>`;
  return card;
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

// --- wire up events ---
el.search.addEventListener("input", debounce((e) => {
  state.q = e.target.value.trim();
  loadOffers();
}, 300));
el.sort.addEventListener("change", (e) => { state.sort = e.target.value; loadOffers(); });
el.minDiscount.addEventListener("input", (e) => {
  state.minDiscount = +e.target.value;
  el.minDiscountVal.textContent = state.minDiscount + "%";
  loadOffers();
});

// --- initial load + auto-refresh while scraping ---
let pollTimer = null;

async function refresh() {
  const m = await loadMeta();
  await loadCategories();
  await loadRetailers();
  await loadOffers();

  const needsPoll = m.scraping || (m.active_offers ?? 0) === 0;
  if (needsPoll && !pollTimer) {
    pollTimer = setInterval(async () => {
      const mm = await loadMeta();
      await loadCategories();
      await loadRetailers();
      await loadOffers();
      if (!mm.scraping && (mm.active_offers ?? 0) > 0) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    }, 4000);
  }
}

refresh();
