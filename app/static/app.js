const storageKey = "arbi3.ui.settings.v1";
const defaults = {
  mode: "all",
  interval: 1000,
  search: "",
  sortColumn: "current",
  sortDirection: "desc",
  sortingPaused: false,
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
  blacklist: new Map(),
  frozenOrder: [],
  socket: null,
  binanceSettings: null,
  binanceStatus: null,
  binanceBalance: null,
  tradingSettings: null,
  previewTimer: null,
};

const elements = {
  mode: document.querySelector("#mode"),
  interval: document.querySelector("#interval"),
  search: document.querySelector("#search"),
  sortPause: document.querySelector("#sort-pause"),
  theme: document.querySelector("#theme"),
  rows: document.querySelector("#rows"),
  connection: document.querySelector("#connection"),
  template: document.querySelector("#row-template"),
  blacklistCount: document.querySelector("#blacklist-count"),
  blacklistItems: document.querySelector("#blacklist-items"),
  sortableHeaders: [...document.querySelectorAll("th[data-sort-key]")],
  columnToggles: [...document.querySelectorAll("[data-column-toggle]")],
  refreshExchanges: document.querySelector("#refresh-exchanges"),
  configureBinance: document.querySelector("#configure-binance"),
  configureTrading: document.querySelector("#configure-trading"),
  binanceState: document.querySelector("#binance-state"),
  binanceBalance: document.querySelector("#binance-balance"),
  binanceMessage: document.querySelector("#binance-message"),
  binanceDialog: document.querySelector("#binance-dialog"),
  binanceForm: document.querySelector("#binance-form"),
  binanceApiKey: document.querySelector("#binance-api-key"),
  binanceSecretKey: document.querySelector("#binance-secret-key"),
  binanceConfigHint: document.querySelector("#binance-config-hint"),
  binanceFormError: document.querySelector("#binance-form-error"),
  disconnectBinance: document.querySelector("#disconnect-binance"),
  tradingDialog: document.querySelector("#trading-dialog"),
  tradingForm: document.querySelector("#trading-form"),
  tradingPositionUsdt: document.querySelector("#trading-position-usdt"),
  tradingLeverage: document.querySelector("#trading-leverage"),
  tradingRounding: document.querySelector("#trading-rounding"),
  previewSymbol: document.querySelector("#preview-symbol"),
  volumePreview: document.querySelector("#volume-preview"),
  tradingFormError: document.querySelector("#trading-form-error"),
  summaryPositionUsdt: document.querySelector("#summary-position-usdt"),
  summaryLeverage: document.querySelector("#summary-leverage"),
  summaryRounding: document.querySelector("#summary-rounding"),
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
  updateSortPauseButton();
  updateSortIndicators();
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text }; }
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : data.detail?.message;
    throw new Error(detail || data.message || `HTTP ${response.status}`);
  }
  return data;
}

function setFormError(element, error = null) {
  element.hidden = !error;
  element.textContent = error ? String(error.message || error) : "";
}

function formatMoney(value, currency = "USDT") {
  if (value === undefined || value === null) return "—";
  return `${Number(value).toLocaleString("ru-RU", { maximumFractionDigits: 4 })} ${currency}`;
}

function renderBinanceOverview() {
  const status = state.binanceStatus;
  elements.binanceState.className = "status neutral";
  if (!status) {
    elements.binanceState.textContent = "не проверено";
    elements.binanceMessage.textContent = "—";
    elements.binanceBalance.textContent = "—";
    return;
  }
  const labels = { connected: "подключено", disabled: "отключено", not_configured: "не настроено", error: "ошибка" };
  elements.binanceState.textContent = labels[status.state] || status.state;
  elements.binanceState.className = `status ${status.state === "connected" ? "online" : status.state === "error" ? "offline" : "neutral"}`;
  elements.binanceMessage.textContent = status.message || "—";
  elements.binanceBalance.textContent = state.binanceBalance
    ? `доступно ${formatMoney(state.binanceBalance.available, state.binanceBalance.currency)} · equity ${formatMoney(state.binanceBalance.equity, state.binanceBalance.currency)}`
    : "—";
}

async function loadBinanceSettings() {
  state.binanceSettings = await api("/api/v1/exchanges/binance/settings");
  const settings = state.binanceSettings;
  elements.binanceConfigHint.textContent = settings.api_key_configured
    ? `Ключ сохранён: ${settings.api_key_masked || "***"}`
    : "API-ключи ещё не сохранены";
  elements.disconnectBinance.disabled = !settings.enabled;
}

async function refreshExchangeOverview() {
  elements.refreshExchanges.disabled = true;
  try {
    state.binanceStatus = await api("/api/v1/exchanges/binance/status");
    state.binanceBalance = null;
    if (state.binanceStatus.state === "connected") {
      try {
        state.binanceBalance = await api("/api/v1/exchanges/binance/balance");
      } catch (error) {
        state.binanceStatus = { ...state.binanceStatus, state: "error", message: error.message };
      }
    }
  } catch (error) {
    state.binanceStatus = { state: "error", message: error.message };
    state.binanceBalance = null;
  } finally {
    renderBinanceOverview();
    elements.refreshExchanges.disabled = false;
  }
}

function renderTradingSettings() {
  const settings = state.tradingSettings;
  if (!settings) return;
  elements.summaryPositionUsdt.textContent = formatMoney(settings.position_usdt);
  elements.summaryLeverage.textContent = `${settings.leverage}x`;
  elements.summaryRounding.textContent = settings.rounding === "up" ? "вверх" : "вниз";
  elements.tradingPositionUsdt.value = settings.position_usdt;
  elements.tradingLeverage.value = settings.leverage;
  elements.tradingRounding.value = settings.rounding;
}

async function loadTradingSettings() {
  state.tradingSettings = await api("/api/v1/trading/settings");
  renderTradingSettings();
}

function scheduleVolumePreview() {
  clearTimeout(state.previewTimer);
  state.previewTimer = setTimeout(loadVolumePreview, 300);
}

async function loadVolumePreview() {
  const symbol = elements.previewSymbol.value.trim().toUpperCase();
  const amount = Number(elements.tradingPositionUsdt.value);
  const rounding = elements.tradingRounding.value;
  if (!symbol || !Number.isFinite(amount) || amount <= 0) {
    elements.volumePreview.textContent = "Введите актив и объём";
    return;
  }
  elements.volumePreview.textContent = "Расчёт…";
  try {
    const query = new URLSearchParams({ symbol, amount_usdt: String(amount), rounding });
    const data = await api(`/api/v1/exchanges/binance/volume-preview?${query}`);
    elements.volumePreview.classList.remove("muted");
    elements.volumePreview.innerHTML = `Покупка: <strong>${data.buy.quantity}</strong> (${formatMoney(data.buy.rounded_amount_usdt)}) · Продажа: <strong>${data.sell.quantity}</strong> (${formatMoney(data.sell.rounded_amount_usdt)})`;
  } catch (error) {
    elements.volumePreview.classList.add("muted");
    elements.volumePreview.textContent = error.message;
  }
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
  state.frozenOrder = state.frozenOrder.filter((assetId) => state.assets.has(assetId));
  render();
}

async function loadBlacklist() {
  const items = await api("/api/v1/blacklist");
  state.blacklist = new Map(items.map((item) => [item.id, item]));
  renderBlacklist();
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

function filteredAssets() {
  const query = state.settings.search.trim().toUpperCase();
  let items = [...state.assets.values()];
  if (state.settings.mode === "favorites") items = items.filter((item) => item.is_favorite);
  if (query) items = items.filter((item) => item.display_symbol.includes(query));
  return items;
}

function sortByPreference(items) {
  const direction = state.settings.sortDirection === "asc" ? 1 : -1;
  return [...items].sort((left, right) =>
    compareValues(
      sortValue(left, state.settings.sortColumn),
      sortValue(right, state.settings.sortColumn),
      direction,
    ),
  );
}

function sortedAssets() {
  const items = filteredAssets();
  if (!state.settings.sortingPaused) return sortByPreference(items);

  if (state.frozenOrder.length === 0) {
    state.frozenOrder = sortByPreference(items).map((item) => item.id);
  }

  const itemsById = new Map(items.map((item) => [item.id, item]));
  const ordered = [];
  for (const assetId of state.frozenOrder) {
    const item = itemsById.get(assetId);
    if (!item) continue;
    ordered.push(item);
    itemsById.delete(assetId);
  }

  const newItems = sortByPreference([...itemsById.values()]);
  for (const item of newItems) state.frozenOrder.push(item.id);
  return [...ordered, ...newItems];
}

function applyColumnVisibility() {
  const hidden = new Set(state.settings.hiddenColumns);
  for (const cell of document.querySelectorAll("[data-column]")) {
    cell.classList.toggle("column-hidden", hidden.has(cell.dataset.column));
  }
}

function updateSortPauseButton() {
  const paused = state.settings.sortingPaused;
  elements.sortPause.textContent = paused ? "Продолжить сортировку" : "Пауза сортировки";
  elements.sortPause.classList.toggle("active", paused);
  elements.sortPause.setAttribute("aria-pressed", String(paused));
}

function updateSortIndicators() {
  for (const header of elements.sortableHeaders) {
    const active = header.dataset.sortKey === state.settings.sortColumn;
    header.classList.toggle("sort-active", active);
    header.classList.toggle("sort-paused", active && state.settings.sortingPaused);
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
    row.dataset.assetId = String(asset.id);

    const favorite = row.querySelector(".favorite");
    favorite.textContent = asset.is_favorite ? "★" : "☆";
    favorite.classList.toggle("active", asset.is_favorite);
    favorite.addEventListener("click", () => toggleFavorite(asset));

    row.querySelector(".blacklist-action").addEventListener("click", () => addToBlacklist(asset));
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

function renderBlacklist() {
  elements.blacklistCount.textContent = String(state.blacklist.size);
  if (state.blacklist.size === 0) {
    const empty = document.createElement("div");
    empty.className = "blacklist-empty";
    empty.textContent = "Список пуст";
    elements.blacklistItems.replaceChildren(empty);
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const item of [...state.blacklist.values()].sort((left, right) =>
    left.display_symbol.localeCompare(right.display_symbol, "ru-RU"))) {
    const row = document.createElement("div");
    row.className = "blacklist-item";

    const symbol = document.createElement("span");
    symbol.textContent = item.display_symbol;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Убрать";
    remove.addEventListener("click", () => removeFromBlacklist(item));

    row.append(symbol, remove);
    fragment.appendChild(row);
  }
  elements.blacklistItems.replaceChildren(fragment);
}

async function toggleFavorite(asset) {
  const method = asset.is_favorite ? "DELETE" : "POST";
  try {
    await api(`/api/v1/favorites/${asset.id}`, { method });
    asset.is_favorite = !asset.is_favorite;
    render();
  } catch (error) {
    console.error(error);
    alert("Не удалось изменить избранное");
  }
}

async function addToBlacklist(asset) {
  const confirmed = confirm(
    `Добавить ${asset.display_symbol} в чёрный список? Получение его котировок будет остановлено.`,
  );
  if (!confirmed) return;

  try {
    await api(`/api/v1/blacklist/${asset.id}`, { method: "POST" });
    state.assets.delete(asset.id);
    state.frozenOrder = state.frozenOrder.filter((assetId) => assetId !== asset.id);
    await loadBlacklist();
    render();
  } catch (error) {
    console.error(error);
    alert("Не удалось добавить актив в чёрный список");
  }
}

async function removeFromBlacklist(item) {
  try {
    await api(`/api/v1/blacklist/${item.id}`, { method: "DELETE" });
    await Promise.all([loadBlacklist(), loadAssets()]);
  } catch (error) {
    console.error(error);
    alert("Не удалось убрать актив из чёрного списка");
  }
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

elements.sortPause.addEventListener("click", () => {
  const nextPaused = !state.settings.sortingPaused;
  if (nextPaused) {
    const visibleOrder = [...elements.rows.querySelectorAll("tr[data-asset-id]")]
      .map((row) => Number(row.dataset.assetId));
    state.frozenOrder = visibleOrder.length
      ? visibleOrder
      : sortByPreference(filteredAssets()).map((item) => item.id);
  } else {
    state.frozenOrder = [];
  }
  state.settings.sortingPaused = nextPaused;
  saveSettings();
  updateSortPauseButton();
  render();
});

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

elements.refreshExchanges.addEventListener("click", refreshExchangeOverview);
elements.configureBinance.addEventListener("click", async () => {
  setFormError(elements.binanceFormError);
  elements.binanceApiKey.value = "";
  elements.binanceSecretKey.value = "";
  await loadBinanceSettings();
  elements.binanceDialog.showModal();
});
elements.binanceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setFormError(elements.binanceFormError);
  try {
    await api("/api/v1/exchanges/binance/connect", {
      method: "POST",
      body: JSON.stringify({
        api_key: elements.binanceApiKey.value || null,
        secret_key: elements.binanceSecretKey.value || null,
      }),
    });
    elements.binanceDialog.close();
    await Promise.all([loadBinanceSettings(), refreshExchangeOverview()]);
  } catch (error) {
    setFormError(elements.binanceFormError, error);
  }
});
elements.disconnectBinance.addEventListener("click", async () => {
  setFormError(elements.binanceFormError);
  try {
    await api("/api/v1/exchanges/binance/disconnect", { method: "POST" });
    elements.binanceDialog.close();
    await Promise.all([loadBinanceSettings(), refreshExchangeOverview()]);
  } catch (error) {
    setFormError(elements.binanceFormError, error);
  }
});

elements.configureTrading.addEventListener("click", async () => {
  setFormError(elements.tradingFormError);
  await loadTradingSettings();
  elements.tradingDialog.showModal();
  scheduleVolumePreview();
});
for (const input of [elements.tradingPositionUsdt, elements.tradingRounding, elements.previewSymbol]) {
  input.addEventListener("input", scheduleVolumePreview);
  input.addEventListener("change", scheduleVolumePreview);
}
elements.tradingForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setFormError(elements.tradingFormError);
  try {
    state.tradingSettings = await api("/api/v1/trading/settings", {
      method: "PUT",
      body: JSON.stringify({
        position_usdt: Number(elements.tradingPositionUsdt.value),
        leverage: Number(elements.tradingLeverage.value),
        rounding: elements.tradingRounding.value,
      }),
    });
    renderTradingSettings();
    elements.tradingDialog.close();
  } catch (error) {
    setFormError(elements.tradingFormError, error);
  }
});
for (const button of document.querySelectorAll("[data-close-dialog]")) {
  button.addEventListener("click", () => document.querySelector(`#${button.dataset.closeDialog}`).close());
}

applySettings();
await Promise.all([loadAssets(), loadBlacklist(), loadBinanceSettings(), loadTradingSettings()]);
await Promise.all([applyRuntimeSettings(), refreshExchangeOverview()]);
connectSocket();
setInterval(() => Promise.all([loadAssets(), loadBlacklist()]), 60000);
