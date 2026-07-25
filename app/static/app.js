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
  activeTrades: new Map(),
  pendingTradeRows: new Set(),
  frozenOrder: [],
  socket: null,
  binanceSettings: null,
  binanceStatus: null,
  binanceBalance: null,
  bybitSettings: null,
  bybitStatus: null,
  bybitBalance: null,
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
  configureBybit: document.querySelector("#configure-bybit"),
  bybitState: document.querySelector("#bybit-state"),
  bybitBalance: document.querySelector("#bybit-balance"),
  bybitMessage: document.querySelector("#bybit-message"),
  bybitDialog: document.querySelector("#bybit-dialog"),
  bybitForm: document.querySelector("#bybit-form"),
  bybitApiKey: document.querySelector("#bybit-api-key"),
  bybitSecretKey: document.querySelector("#bybit-secret-key"),
  bybitConfigHint: document.querySelector("#bybit-config-hint"),
  bybitFormError: document.querySelector("#bybit-form-error"),
  disconnectBybit: document.querySelector("#disconnect-bybit"),
  tradingDialog: document.querySelector("#trading-dialog"),
  tradingForm: document.querySelector("#trading-form"),
  tradingExchange: document.querySelector("#trading-exchange"),
  tradingPositionUsdt: document.querySelector("#trading-position-usdt"),
  tradingLeverage: document.querySelector("#trading-leverage"),
  tradingRounding: document.querySelector("#trading-rounding"),
  tradingInsuranceSeconds: document.querySelector("#trading-insurance-seconds"),
  previewSymbol: document.querySelector("#preview-symbol"),
  volumePreview: document.querySelector("#volume-preview"),
  tradingFormError: document.querySelector("#trading-form-error"),
  tradingActionStatus: document.querySelector("#trading-action-status"),
  testOpenLong: document.querySelector("#test-open-long"),
  testOpenShort: document.querySelector("#test-open-short"),
  testClosePosition: document.querySelector("#test-close-position"),
  summaryPositionUsdt: document.querySelector("#summary-position-usdt"),
  summaryLeverage: document.querySelector("#summary-leverage"),
  summaryRounding: document.querySelector("#summary-rounding"),
  summaryInsurance: document.querySelector("#summary-insurance"),
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

function renderExchangeOverview(exchange) {
  const status = state[`${exchange}Status`];
  const balance = state[`${exchange}Balance`];
  const stateElement = elements[`${exchange}State`];
  const messageElement = elements[`${exchange}Message`];
  const balanceElement = elements[`${exchange}Balance`];
  stateElement.className = "status neutral";
  if (!status) {
    stateElement.textContent = "не проверено";
    messageElement.textContent = "—";
    balanceElement.textContent = "—";
    return;
  }
  const labels = { connected: "подключено", disabled: "отключено", not_configured: "не настроено", error: "ошибка" };
  stateElement.textContent = labels[status.state] || status.state;
  stateElement.className = `status ${status.state === "connected" ? "online" : status.state === "error" ? "offline" : "neutral"}`;
  messageElement.textContent = status.message || "—";
  balanceElement.textContent = balance
    ? `доступно ${formatMoney(balance.available, balance.currency)} · equity ${formatMoney(balance.equity, balance.currency)}`
    : "—";
}

async function loadExchangeSettings(exchange) {
  const settings = await api(`/api/v1/exchanges/${exchange}/settings`);
  state[`${exchange}Settings`] = settings;
  const hint = elements[`${exchange}ConfigHint`];
  hint.textContent = settings.api_key_configured
    ? `Ключ сохранён: ${settings.api_key_masked || "***"}`
    : "API-ключи ещё не сохранены";
  elements[`disconnect${exchange[0].toUpperCase()}${exchange.slice(1)}`].disabled = !settings.enabled;
}

async function refreshOneExchange(exchange) {
  try {
    state[`${exchange}Status`] = await api(`/api/v1/exchanges/${exchange}/status`);
    state[`${exchange}Balance`] = null;
    if (state[`${exchange}Status`].state === "connected") {
      try {
        state[`${exchange}Balance`] = await api(`/api/v1/exchanges/${exchange}/balance`);
      } catch (error) {
        state[`${exchange}Status`] = { ...state[`${exchange}Status`], state: "error", message: error.message };
      }
    }
  } catch (error) {
    state[`${exchange}Status`] = { state: "error", message: error.message };
    state[`${exchange}Balance`] = null;
  }
  renderExchangeOverview(exchange);
}

async function refreshExchangeOverview() {
  elements.refreshExchanges.disabled = true;
  try {
    await Promise.all([refreshOneExchange("binance"), refreshOneExchange("bybit")]);
  } finally {
    elements.refreshExchanges.disabled = false;
  }
}

function renderTradingSettings() {
  const settings = state.tradingSettings;
  if (!settings) return;
  elements.summaryPositionUsdt.textContent = formatMoney(settings.position_usdt);
  elements.summaryLeverage.textContent = `${settings.leverage}x`;
  elements.summaryRounding.textContent = settings.rounding === "up" ? "вверх" : "вниз";
  elements.summaryInsurance.textContent = `${Number(settings.insurance_seconds).toLocaleString("ru-RU")} сек`;
  elements.tradingPositionUsdt.value = settings.position_usdt;
  elements.tradingLeverage.value = settings.leverage;
  elements.tradingRounding.value = settings.rounding;
  elements.tradingInsuranceSeconds.value = settings.insurance_seconds;
}

async function loadTradingSettings() {
  state.tradingSettings = await api("/api/v1/trading/settings");
  renderTradingSettings();
}

function scheduleVolumePreview() {
  clearTimeout(state.previewTimer);
  state.previewTimer = setTimeout(loadVolumePreview, 300);
}

function favoriteAssets() {
  const unique = new Map();
  for (const row of state.assets.values()) {
    if (!row.is_favorite || unique.has(row.asset_id)) continue;
    unique.set(row.asset_id, row);
  }
  return [...unique.values()].sort((left, right) =>
    left.display_symbol.localeCompare(right.display_symbol, "ru-RU"));
}

function renderFavoriteOptions() {
  const current = elements.previewSymbol.value;
  const favorites = favoriteAssets();
  if (favorites.length === 0) {
    elements.previewSymbol.innerHTML = '<option value="">Добавьте связку в избранное</option>';
    elements.previewSymbol.disabled = true;
  } else {
    elements.previewSymbol.disabled = false;
    elements.previewSymbol.innerHTML = favorites
      .map((asset) => `<option value="${asset.base_asset}${asset.quote_asset}">${asset.display_symbol}</option>`)
      .join("");
    if (favorites.some((asset) => `${asset.base_asset}${asset.quote_asset}` === current)) {
      elements.previewSymbol.value = current;
    }
  }
  updateTradeActionAvailability();
}

function updateTradeActionAvailability(busy = false) {
  const disabled = busy || !elements.previewSymbol.value;
  elements.testOpenLong.disabled = disabled;
  elements.testOpenShort.disabled = disabled;
  elements.testClosePosition.disabled = disabled;
}

async function loadVolumePreview() {
  const exchange = elements.tradingExchange.value;
  const symbol = elements.previewSymbol.value.trim().toUpperCase();
  const amount = Number(elements.tradingPositionUsdt.value);
  const rounding = elements.tradingRounding.value;
  if (!symbol || !Number.isFinite(amount) || amount <= 0) {
    elements.volumePreview.textContent = "Выберите избранный актив и укажите объём";
    return;
  }
  elements.volumePreview.textContent = "Расчёт…";
  try {
    const query = new URLSearchParams({ symbol, amount_usdt: String(amount), rounding });
    const data = await api(`/api/v1/exchanges/${exchange}/volume-preview?${query}`);
    elements.volumePreview.classList.remove("muted");
    elements.volumePreview.innerHTML = `${exchange === "binance" ? "Binance" : "Bybit"} · LONG по ask: <strong>${data.buy.quantity}</strong> (${formatMoney(data.buy.rounded_amount_usdt)}) · SHORT по bid: <strong>${data.sell.quantity}</strong> (${formatMoney(data.sell.rounded_amount_usdt)})`;
  } catch (error) {
    elements.volumePreview.classList.add("muted");
    elements.volumePreview.textContent = error.message;
  }
}

async function executeTestOpen(direction) {
  const exchange = elements.tradingExchange.value;
  const symbol = elements.previewSymbol.value;
  const amount = Number(elements.tradingPositionUsdt.value);
  const leverage = Number(elements.tradingLeverage.value);
  const rounding = elements.tradingRounding.value;
  if (!symbol) return;
  const title = direction === "long" ? "LONG" : "SHORT";
  if (!confirm(`Открыть ${title} ${symbol} на ${exchange.toUpperCase()} объёмом ${amount} USDT, плечо ${leverage}x?`)) return;
  updateTradeActionAvailability(true);
  elements.tradingActionStatus.textContent = `Отправка ${title}…`;
  try {
    const result = await api(`/api/v1/exchanges/${exchange}/positions/open`, {
      method: "POST",
      body: JSON.stringify({
        symbol,
        direction,
        amount_usdt: amount,
        leverage,
        rounding,
        confirm: true,
      }),
    });
    elements.tradingActionStatus.className = "action-status positive";
    elements.tradingActionStatus.textContent = `${result.message}${result.order_id ? ` · order ${result.order_id}` : ""}`;
    await refreshOneExchange(exchange);
  } catch (error) {
    elements.tradingActionStatus.className = "action-status negative";
    elements.tradingActionStatus.textContent = error.message;
  } finally {
    updateTradeActionAvailability();
  }
}

async function executeTestClose() {
  const exchange = elements.tradingExchange.value;
  const symbol = elements.previewSymbol.value;
  if (!symbol) return;
  updateTradeActionAvailability(true);
  elements.tradingActionStatus.textContent = "Проверка открытых позиций…";
  try {
    const query = new URLSearchParams({ symbol });
    const data = await api(`/api/v1/exchanges/${exchange}/positions?${query}`);
    const normalizedSymbol = symbol.replace(/[^A-Z0-9]/g, "");
    const positions = (data.items || []).filter((item) => item.symbol === normalizedSymbol);
    if (positions.length === 0) throw new Error(`Открытые позиции ${symbol} не найдены`);
    const directions = positions.map((item) => item.direction.toUpperCase()).join(" и ");
    if (!confirm(`Закрыть ${directions} по ${symbol} на ${exchange.toUpperCase()} market-ордером?`)) return;
    const results = [];
    for (const position of positions) {
      results.push(await api(`/api/v1/exchanges/${exchange}/positions/close`, {
        method: "POST",
        body: JSON.stringify({
          symbol,
          direction: position.direction,
          amount_usdt: null,
          rounding: elements.tradingRounding.value,
          confirm: true,
        }),
      }));
    }
    elements.tradingActionStatus.className = "action-status positive";
    elements.tradingActionStatus.textContent = results.map((item) => item.message).join(" · ");
    await refreshOneExchange(exchange);
  } catch (error) {
    elements.tradingActionStatus.className = "action-status negative";
    elements.tradingActionStatus.textContent = error.message;
  } finally {
    updateTradeActionAvailability();
  }
}

async function loadAssets() {
  const assets = await api("/api/v1/assets");
  const receivedKeys = new Set();
  for (const asset of assets) {
    const key = asset.row_key;
    receivedKeys.add(key);
    const previous = state.assets.get(key) || {};
    state.assets.set(key, { ...previous, ...asset });
  }
  for (const rowKey of state.assets.keys()) {
    if (!receivedKeys.has(rowKey)) state.assets.delete(rowKey);
  }
  state.frozenOrder = state.frozenOrder.filter((rowKey) => state.assets.has(rowKey));
  renderFavoriteOptions();
  render();
}

async function loadActiveTrades() {
  const items = await api("/api/v1/arbitrage/trades");
  state.activeTrades = new Map(items.map((item) => [item.row_key, item]));
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
      const asset = state.assets.get(update.row_key);
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

function isPinnedRow(rowKey) {
  return state.activeTrades.has(rowKey) || state.pendingTradeRows.has(rowKey);
}

function filteredAssets() {
  const query = state.settings.search.trim().toUpperCase();
  const allItems = [...state.assets.values()];
  let items = allItems.filter((item) => {
    if (isPinnedRow(item.row_key)) return true;
    if (state.settings.mode === "favorites" && !item.is_favorite) return false;
    if (query && !item.display_symbol.includes(query)) return false;
    return true;
  });
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
  const pinned = items
    .filter((item) => isPinnedRow(item.row_key))
    .sort((left, right) => {
      const leftTrade = state.activeTrades.get(left.row_key);
      const rightTrade = state.activeTrades.get(right.row_key);
      return String(leftTrade?.created_at || "").localeCompare(String(rightTrade?.created_at || ""));
    });
  const regular = items.filter((item) => !isPinnedRow(item.row_key));

  if (!state.settings.sortingPaused) return [...pinned, ...sortByPreference(regular)];

  if (state.frozenOrder.length === 0) {
    state.frozenOrder = sortByPreference(regular).map((item) => item.row_key);
  }

  const itemsByKey = new Map(regular.map((item) => [item.row_key, item]));
  const ordered = [];
  for (const rowKey of state.frozenOrder) {
    const item = itemsByKey.get(rowKey);
    if (!item) continue;
    ordered.push(item);
    itemsByKey.delete(rowKey);
  }

  const newItems = sortByPreference([...itemsByKey.values()]);
  for (const item of newItems) state.frozenOrder.push(item.row_key);
  return [...pinned, ...ordered, ...newItems];
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
    row.dataset.rowKey = asset.row_key;
    row.dataset.assetId = String(asset.asset_id);

    const favorite = row.querySelector(".favorite");
    favorite.textContent = asset.is_favorite ? "★" : "☆";
    favorite.classList.toggle("active", asset.is_favorite);
    favorite.title = `${asset.display_symbol} · ${asset.exchange_a.toUpperCase()} ↔ ${asset.exchange_b.toUpperCase()}`;
    favorite.addEventListener("click", () => toggleFavorite(asset));

    row.querySelector(".blacklist-action").addEventListener("click", () => addToBlacklist(asset));
    row.querySelector(".symbol-name").textContent = asset.display_symbol;
    row.querySelector(".pair-label").textContent = ` ${asset.exchange_a.toUpperCase()} ↔ ${asset.exchange_b.toUpperCase()}`;

    const tradeButton = row.querySelector(".pair-trade-action");
    const activeTrade = state.activeTrades.get(asset.row_key);
    const pending = state.pendingTradeRows.has(asset.row_key);
    if (activeTrade) {
      row.classList.add("active-trade-row");
      tradeButton.textContent = "■";
      tradeButton.classList.add("close-pair-action");
      tradeButton.title = `Закрыть ${activeTrade.buy_exchange.toUpperCase()} LONG ↔ ${activeTrade.sell_exchange.toUpperCase()} SHORT`;
      tradeButton.addEventListener("click", () => closePairTrade(activeTrade));
    } else if (pending) {
      row.classList.add("active-trade-row");
      tradeButton.textContent = "…";
      tradeButton.disabled = true;
      tradeButton.title = "Открытие обеих ног";
    } else {
      tradeButton.textContent = "▶";
      tradeButton.disabled = !asset.current_spread;
      tradeButton.title = asset.current_spread
        ? `Открыть ${directionText(asset)}`
        : "Нет свежей ask→bid связки";
      tradeButton.addEventListener("click", () => openPairTrade(asset));
    }

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
    const direction = row.querySelector(".direction");
    direction.textContent = activeTrade
      ? `ОТКРЫТО: ${activeTrade.buy_exchange.toUpperCase()} LONG ↔ ${activeTrade.sell_exchange.toUpperCase()} SHORT`
      : directionText(asset);
    direction.classList.toggle("positive", Boolean(activeTrade));
    fragment.appendChild(row);
  }
  elements.rows.replaceChildren(fragment);
  applyColumnVisibility();
  updateSortIndicators();
}

async function openPairTrade(asset) {
  if (!asset.current_spread || state.pendingTradeRows.has(asset.row_key)) return;
  const spread = asset.current_spread;
  const settings = state.tradingSettings || await api("/api/v1/trading/settings");
  const confirmed = confirm(
    `Открыть арбитражную связку ${asset.display_symbol}?

` +
    `${spread.buy_exchange.toUpperCase()}: LONG по ask
` +
    `${spread.sell_exchange.toUpperCase()}: SHORT по bid
` +
    `Объём каждой ноги: ${settings.position_usdt} USDT
` +
    `Плечо: ${settings.leverage}x
` +
    `Страховка: ${settings.insurance_seconds} сек`,
  );
  if (!confirmed) return;

  state.pendingTradeRows.add(asset.row_key);
  render();
  try {
    const trade = await api("/api/v1/arbitrage/trades/open", {
      method: "POST",
      body: JSON.stringify({
        asset_id: asset.asset_id,
        exchange_a: asset.exchange_a,
        exchange_b: asset.exchange_b,
        confirm: true,
      }),
    });
    state.activeTrades.set(trade.row_key, trade);
    await Promise.all([
      refreshOneExchange(trade.buy_exchange),
      refreshOneExchange(trade.sell_exchange),
    ]);
  } catch (error) {
    alert(`Связка не открыта: ${error.message}`);
    await loadActiveTrades();
  } finally {
    state.pendingTradeRows.delete(asset.row_key);
    render();
  }
}

async function closePairTrade(trade) {
  const confirmed = confirm(
    `Закрыть арбитражную связку ${trade.display_symbol}?

` +
    `${trade.buy_exchange.toUpperCase()}: закрыть LONG
` +
    `${trade.sell_exchange.toUpperCase()}: закрыть SHORT`,
  );
  if (!confirmed) return;

  state.pendingTradeRows.add(trade.row_key);
  render();
  try {
    await api(`/api/v1/arbitrage/trades/${trade.id}/close`, {
      method: "POST",
      body: JSON.stringify({ confirm: true }),
    });
    state.activeTrades.delete(trade.row_key);
    await Promise.all([
      refreshOneExchange(trade.buy_exchange),
      refreshOneExchange(trade.sell_exchange),
    ]);
  } catch (error) {
    alert(`Не удалось закрыть обе ноги: ${error.message}`);
    await loadActiveTrades();
  } finally {
    state.pendingTradeRows.delete(trade.row_key);
    render();
  }
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
    await api(`/api/v1/favorites/${asset.asset_id}/${asset.exchange_a}/${asset.exchange_b}`, { method });
    asset.is_favorite = !asset.is_favorite;
    renderFavoriteOptions();
    render();
  } catch (error) {
    console.error(error);
    alert(`Не удалось изменить избранное: ${error.message}`);
  }
}

async function addToBlacklist(asset) {
  const confirmed = confirm(
    `Добавить ${asset.display_symbol} в чёрный список? Получение его котировок будет остановлено.`,
  );
  if (!confirmed) return;

  try {
    await api(`/api/v1/blacklist/${asset.asset_id}`, { method: "POST" });
    for (const [rowKey, row] of state.assets) {
      if (row.asset_id === asset.asset_id) state.assets.delete(rowKey);
    }
    state.frozenOrder = state.frozenOrder.filter((rowKey) => state.assets.has(rowKey));
    renderFavoriteOptions();
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
    const visibleOrder = [...elements.rows.querySelectorAll("tr[data-row-key]")]
      .map((row) => row.dataset.rowKey)
      .filter((rowKey) => !isPinnedRow(rowKey));
    state.frozenOrder = visibleOrder.length
      ? visibleOrder
      : sortByPreference(filteredAssets().filter((item) => !isPinnedRow(item.row_key)))
        .map((item) => item.row_key);
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

function bindExchangeDialog(exchange) {
  const title = exchange[0].toUpperCase() + exchange.slice(1);
  const configure = elements[`configure${title}`];
  const dialog = elements[`${exchange}Dialog`];
  const form = elements[`${exchange}Form`];
  const apiKey = elements[`${exchange}ApiKey`];
  const secretKey = elements[`${exchange}SecretKey`];
  const formError = elements[`${exchange}FormError`];
  const disconnect = elements[`disconnect${title}`];

  configure.addEventListener("click", async () => {
    setFormError(formError);
    apiKey.value = "";
    secretKey.value = "";
    await loadExchangeSettings(exchange);
    dialog.showModal();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormError(formError);
    try {
      await api(`/api/v1/exchanges/${exchange}/connect`, {
        method: "POST",
        body: JSON.stringify({
          api_key: apiKey.value || null,
          secret_key: secretKey.value || null,
        }),
      });
      dialog.close();
      await Promise.all([loadExchangeSettings(exchange), refreshOneExchange(exchange)]);
    } catch (error) {
      setFormError(formError, error);
    }
  });

  disconnect.addEventListener("click", async () => {
    setFormError(formError);
    try {
      await api(`/api/v1/exchanges/${exchange}/disconnect`, { method: "POST" });
      dialog.close();
      await Promise.all([loadExchangeSettings(exchange), refreshOneExchange(exchange)]);
    } catch (error) {
      setFormError(formError, error);
    }
  });
}

bindExchangeDialog("binance");
bindExchangeDialog("bybit");

elements.configureTrading.addEventListener("click", async () => {
  setFormError(elements.tradingFormError);
  elements.tradingActionStatus.className = "action-status muted";
  elements.tradingActionStatus.textContent = "Операции не выполнялись";
  await Promise.all([loadTradingSettings(), loadAssets()]);
  renderFavoriteOptions();
  elements.tradingDialog.showModal();
  scheduleVolumePreview();
});
for (const input of [elements.tradingExchange, elements.tradingPositionUsdt, elements.tradingRounding, elements.previewSymbol]) {
  input.addEventListener("input", scheduleVolumePreview);
  input.addEventListener("change", scheduleVolumePreview);
}
elements.testOpenLong.addEventListener("click", () => executeTestOpen("long"));
elements.testOpenShort.addEventListener("click", () => executeTestOpen("short"));
elements.testClosePosition.addEventListener("click", executeTestClose);

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
        insurance_seconds: Number(elements.tradingInsuranceSeconds.value),
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
await Promise.all([
  loadAssets(),
  loadBlacklist(),
  loadExchangeSettings("binance"),
  loadExchangeSettings("bybit"),
  loadTradingSettings(),
  loadActiveTrades(),
]);
await Promise.all([applyRuntimeSettings(), refreshExchangeOverview()]);
connectSocket();
setInterval(() => Promise.all([loadAssets(), loadBlacklist(), loadActiveTrades()]), 60000);
