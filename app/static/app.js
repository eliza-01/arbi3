const storageKey = "arbi3.ui.settings.v1";
const defaults = { mode: "all", interval: 1000, search: "", sort: "current", theme: "light" };

function readSettings() {
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(storageKey) || "{}") };
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
  sort: document.querySelector("#sort"),
  theme: document.querySelector("#theme"),
  rows: document.querySelector("#rows"),
  connection: document.querySelector("#connection"),
  template: document.querySelector("#row-template"),
};

function saveSettings() {
  localStorage.setItem(storageKey, JSON.stringify(state.settings));
}

function applySettings() {
  elements.mode.value = state.settings.mode;
  elements.interval.value = String(state.settings.interval);
  elements.search.value = state.settings.search;
  elements.sort.value = state.settings.sort;
  document.documentElement.dataset.theme = state.settings.theme;
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
  for (const asset of assets) {
    const previous = state.assets.get(asset.id) || {};
    state.assets.set(asset.id, { ...previous, ...asset });
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

function formatQuote(quote) {
  if (!quote) return "—";
  return `${formatPrice(quote.bid)} / ${formatPrice(quote.ask)}`;
}

function formatDelta(value) {
  if (value === undefined || value === null) return "—";
  return `${Number(value).toFixed(4)}%`;
}

function deltaClass(value) {
  if (value === undefined || value === null) return "muted";
  return Number(value) >= 0 ? "positive" : "negative";
}

function sortedAssets() {
  const query = state.settings.search.trim().toUpperCase();
  let items = [...state.assets.values()];
  if (state.settings.mode === "favorites") items = items.filter((item) => item.is_favorite);
  if (query) items = items.filter((item) => item.display_symbol.includes(query));
  const getValue = {
    current: (item) => item.current_spread?.delta_pct ?? -Infinity,
    hour: (item) => item.peaks?.hour_pct ?? -Infinity,
    day: (item) => item.peaks?.day_pct ?? -Infinity,
    all_time: (item) => item.peaks?.all_time_pct ?? -Infinity,
    symbol: (item) => item.display_symbol,
  }[state.settings.sort];
  items.sort((a, b) => {
    const av = getValue(a);
    const bv = getValue(b);
    return typeof av === "string" ? av.localeCompare(bv) : bv - av;
  });
  return items;
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
    row.querySelector(".binance").textContent = formatQuote(asset.quotes?.binance);
    row.querySelector(".bybit").textContent = formatQuote(asset.quotes?.bybit);

    const values = {
      ".current": asset.current_spread?.delta_pct,
      ".hour": asset.peaks?.hour_pct,
      ".day": asset.peaks?.day_pct,
      ".all-time": asset.peaks?.all_time_pct,
    };
    for (const [selector, value] of Object.entries(values)) {
      const cell = row.querySelector(selector);
      cell.textContent = formatDelta(value);
      cell.classList.add(deltaClass(value));
    }
    const direction = asset.current_spread
      ? `${asset.current_spread.buy_exchange} → ${asset.current_spread.sell_exchange}`
      : "—";
    row.querySelector(".direction").textContent = direction;
    fragment.appendChild(row);
  }
  elements.rows.replaceChildren(fragment);
}

async function toggleFavorite(asset) {
  const method = asset.is_favorite ? "DELETE" : "POST";
  await api(`/api/v1/favorites/${asset.id}`, { method });
  asset.is_favorite = !asset.is_favorite;
  render();
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

elements.sort.addEventListener("change", () => {
  state.settings.sort = elements.sort.value;
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
