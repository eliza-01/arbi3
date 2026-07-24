const storageKey = "arbi3.ui.settings.v1";
const defaults = {
  mode: "all",
  interval: 1000,
  search: "",
  sortColumn: "current",
  sortDirection: "desc",
  hiddenColumns: [],
  theme: "light",
};

function readSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
    const legacySortColumns = { hour: "hour_max", day: "day_max", all_time: "all_time_max" };
    if (saved.sort && !saved.sortColumn) {
      saved.sortColumn = legacySortColumns[saved.sort] || saved.sort;
    }
    if (!Array.isArray(saved.hiddenColumns)) saved.hiddenColumns = [];
    return { ...defaults, ...saved };
  } catch {
    return { ...defaults };
  }
}

const state = {
  settings: readSettings(),
  assets: new Map(),
  socket: null,
};

const elements = {
  mode: document.querySelector("#mode"),
  interval: document.querySelector("#interval"),
  search: document.querySelector("#search"),
  theme: document.querySelector("#theme"),
  rows: document.querySelector("#rows"),
  connection: document.querySelector("#connection"),
  template: document.querySelector("#row-template"),
  sortableHeaders: [...document.querySelectorAll("th[data-sort-key]")],
  columnToggles: [...document.querySelectorAll("[data-column-toggle]")],
};

function saveSettings() {
  localStorage.setItem(storageKey, JSON.stringify(state.settings));
}

function applySettings() {
  elements.mode.value = state.settings.mode;
  elements.interval.value = String(state.settings.interval);
  elements.search.value = state.settings.search;
  document.documentElement.dataset.theme = state.settings.theme;
  for (const toggle of elements.columnToggles) {
    toggle.checked = !state.settings.hiddenColumns.includes(toggle.dataset.columnToggle);
  }
  applyColumnVisibility();
  updateSortIndicators();
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function loadAssets() {
  const assets = await api("/api/v1/assets");
  const receivedIds = new Set();
  for (const asset of assets) {
    receivedIds.add(asset.id);
    const previous = state.assets.get(asset.id) || {};
    state.assets.set(asset.id, { ...previous, ...asset });
  }
  for (const assetId of state.assets.keys()) {
    if (!receivedIds.has(assetId)) state.assets.delete(assetId);
  }
  render();
}

async function applyRuntimeSettings() {
  await Promise.all([
    api("/api/v1/runtime/mode", {
      method: "PUT",
      body: JSON.stringify({ mode: state.settings.mode }),
    }),
    api("/api/v1/runtime/interval", {
      method: "PUT",
      body: JSON.stringify({ interval_ms: Number(state.settings.interval) }),
    }),
  ]);
}

function connectSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${location.host}/ws/quotes`);
  state.socket = socket;
  socket.addEventListener("open", () => {
    elements.connection.textContent = "online";
    elements.connection.className = "status online";
  });
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.type !== "quotes") return;
    for (const update of message.items) {
      const asset = state.assets.get(update.asset_id);
      if (!asset) continue;
      asset.quotes = update.quotes;
      asset.current_spread = update.current_spread;
    }
    render();
  });
  socket.addEventListener("close", () => {
    elements.connection.textContent = "offline";
    elements.connection.className = "status offline";
    setTimeout(connectSocket, 2000);
  });
}

function formatPrice(value) {
  if (value === undefined || value === null) return "—";
  const number = Number(value);
  if (number >= 1000) return number.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
  if (number >= 1) return number.toLocaleString("ru-RU", { maximumFractionDigits: 5 });
  return number.toLocaleString("ru-RU", { maximumSignificantDigits: 7 });
}

function executionPrice(asset, exchangeCode) {
  const spread = asset.current_spread;
  if (!spread) return null;
  if (spread.buy_exchange === exchangeCode) return Number(spread.buy_price);
  if (spread.sell_exchange === exchangeCode) return Number(spread.sell_price);
  return null;
}

function renderExecutionQuote(cell, asset, exchangeCode) {
  const spread = asset.current_spread;
  cell.classList.remove("buy-price", "sell-price", "muted");
  if (!spread) {
    cell.textContent = "—";
    cell.classList.add("muted");
    return;
  }
  if (spread.buy_exchange === exchangeCode) {
    cell.textContent = `ask ${formatPrice(spread.buy_price)}`;
    cell.classList.add("buy-price");
    return;
  }
  if (spread.sell_exchange === exchangeCode) {
    cell.textContent = `bid ${formatPrice(spread.sell_price)}`;
    cell.classList.add("sell-price");
    return;
  }
  cell.textContent = "—";
  cell.classList.add("muted");
}

function formatDelta(value) {
  if (value === undefined || value === null) return "—";
  return `${Number(value).toFixed(4)}%`;
}

function deltaClass(value) {
  if (value === undefined || value === null) return "muted";
  return Number(value) >= 0 ? "positive" : "negative";
}

function directionText(asset) {
  const spread = asset.current_spread;
  if (!spread) return "—";
  return `${spread.buy_exchange.toUpperCase()} ask → ${spread.sell_exchange.toUpperCase()} bid`;
}

function sortValue(item, key) {
  const values = {
    symbol: () => item.display_symbol,
    binance: () => executionPrice(item, "binance"),
    bybit: () => executionPrice(item, "bybit"),
    current: () => item.current_spread?.delta_pct,
    hour_max: () => item.peaks?.hour_pct,
    hour_min: () => item.peaks?.hour_min_pct,
    day_max: () => item.peaks?.day_pct,
    day_min: () => item.peaks?.day_min_pct,
    all_time_max: () => item.peaks?.all_time_pct,
    all_time_min: () => item.peaks?.all_time_min_pct,
    direction: () => directionText(item),
  };
  return values[key]?.() ?? null;
}

function compareValues(left, right, direction) {
  const leftMissing = left === null || left === undefined;
  const rightMissing = right === null || right === undefined;
  if (leftMissing && rightMissing) return 0;
  if (leftMissing) return 1;
  if (rightMissing) return -1;
  if (typeof left === "string" || typeof right === "string") {
    return String(left).localeCompare(String(right), "ru-RU") * direction;
  }
  return (Number(left) - Number(right)) * direction;
}

function sortedAssets() {
  const query = state.settings.search.trim().toUpperCase();
  let items = [...state.assets.values()];
  if (state.settings.mode === "favorites") items = items.filter((item) => item.is_favorite);
  if (query) items = items.filter((item) => item.display_symbol.includes(query));
  const direction = state.settings.sortDirection === "asc" ? 1 : -1;
  items.sort((left, right) =>
    compareValues(
      sortValue(left, state.settings.sortColumn),
      sortValue(right, state.settings.sortColumn),
      direction,
    ),
  );
  return items;
}

function applyColumnVisibility() {
  const hidden = new Set(state.settings.hiddenColumns);
  for (const cell of document.querySelectorAll("[data-column]")) {
    cell.classList.toggle("column-hidden", hidden.has(cell.dataset.column));
  }
}

function updateSortIndicators() {
  for (const header of elements.sortableHeaders) {
    const active = header.dataset.sortKey === state.settings.sortColumn;
    header.classList.toggle("sort-active", active);
    header.setAttribute(
      "aria-sort",
      active ? (state.settings.sortDirection === "asc" ? "ascending" : "descending") : "none",
    );
    header.querySelector(".sort-indicator").textContent = active
      ? state.settings.sortDirection === "asc" ? "▲" : "▼"
      : "";
  }
}

function render() {
  const fragment = document.createDocumentFragment();
  for (const asset of sortedAssets()) {
    const row = elements.template.content.firstElementChild.cloneNode(true);
    const favorite = row.querySelector(".favorite");
    favorite.textContent = asset.is_favorite ? "★" : "☆";
    favorite.classList.toggle("active", asset.is_favorite);
    favorite.addEventListener("click", () => toggleFavorite(asset));
    row.querySelector(".symbol").textContent = asset.display_symbol;
    renderExecutionQuote(row.querySelector(".binance"), asset, "binance");
    renderExecutionQuote(row.querySelector(".bybit"), asset, "bybit");

    const values = {
      ".current": asset.current_spread?.delta_pct,
      ".hour-max": asset.peaks?.hour_pct,
      ".hour-min": asset.peaks?.hour_min_pct,
      ".day-max": asset.peaks?.day_pct,
      ".day-min": asset.peaks?.day_min_pct,
      ".all-time-max": asset.peaks?.all_time_pct,
      ".all-time-min": asset.peaks?.all_time_min_pct,
    };
    for (const [selector, value] of Object.entries(values)) {
      const cell = row.querySelector(selector);
      cell.textContent = formatDelta(value);
      cell.classList.add(deltaClass(value));
    }
    row.querySelector(".direction").textContent = directionText(asset);
    fragment.appendChild(row);
  }
  elements.rows.replaceChildren(fragment);
  applyColumnVisibility();
  updateSortIndicators();
}

async function toggleFavorite(asset) {
  const method = asset.is_favorite ? "DELETE" : "POST";
  await api(`/api/v1/favorites/${asset.id}`, { method });
  asset.is_favorite = !asset.is_favorite;
  render();
}

for (const header of elements.sortableHeaders) {
  header.querySelector("button").addEventListener("click", () => {
    const key = header.dataset.sortKey;
    if (state.settings.sortColumn === key) {
      state.settings.sortDirection = state.settings.sortDirection === "asc" ? "desc" : "asc";
    } else {
      state.settings.sortColumn = key;
      state.settings.sortDirection = ["symbol", "direction"].includes(key) ? "asc" : "desc";
    }
    saveSettings();
    render();
  });
}

for (const toggle of elements.columnToggles) {
  toggle.addEventListener("change", () => {
    const hidden = new Set(state.settings.hiddenColumns);
    if (toggle.checked) hidden.delete(toggle.dataset.columnToggle);
    else hidden.add(toggle.dataset.columnToggle);
    state.settings.hiddenColumns = [...hidden];
    saveSettings();
    applyColumnVisibility();
  });
}

elements.mode.addEventListener("change", async () => {
  state.settings.mode = elements.mode.value;
  saveSettings();
  await api("/api/v1/runtime/mode", {
    method: "PUT",
    body: JSON.stringify({ mode: state.settings.mode }),
  });
  render();
});

elements.interval.addEventListener("change", async () => {
  state.settings.interval = Number(elements.interval.value);
  saveSettings();
  await api("/api/v1/runtime/interval", {
    method: "PUT",
    body: JSON.stringify({ interval_ms: state.settings.interval }),
  });
});

elements.search.addEventListener("input", () => {
  state.settings.search = elements.search.value;
  saveSettings();
  render();
});

elements.theme.addEventListener("click", () => {
  state.settings.theme = state.settings.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = state.settings.theme;
  saveSettings();
});

applySettings();
await loadAssets();
await applyRuntimeSettings();
connectSocket();
setInterval(loadAssets, 60000);
