# Arbi3

Монитор котировок USDT perpetual futures на Binance и Bybit.

## Что реализовано

- синхронизация инструментов при запуске;
- отслеживание только общих активов, присутствующих минимум на двух биржах;
- WebSocket с автоматическим переходом на polling при ошибках;
- реальное отключение лишних подписок в режиме `favorites`;
- настраиваемый интервал расчёта и отправки данных;
- текущая исполнимая дельта по лучшим bid/ask;
- максимальная дельта за всё время, 24 часа и 1 час;
- минутные максимумы в MySQL вместо хранения каждого тика;
- избранные активы и чёрный список в MySQL;
- исключение чёрного списка из WebSocket/polling-подписок;
- пауза динамической сортировки без остановки обновления цен;
- настройки интерфейса в `localStorage` браузера;
- ручное подключение Binance USDⓈ-M Futures, проверка состояния и чтение USDT-баланса;
- ручные market-операции открытия/закрытия, установка плеча и расчёт количества по сумме USDT;
- локальные Binance-ключи и торговые параметры в `local_data/settings.json`;
- FastAPI, MySQL 8.4, phpMyAdmin и статический интерфейс в Docker Compose.

## Принятые ограничения первой версии

Сравниваются только линейные бессрочные USDT-контракты. Это исключает некорректное
сравнение контрактов с разной валютой расчёта или датой экспирации.

Интервал для WebSocket означает частоту расчёта, записи агрегатов и отправки данных
в интерфейс. Биржевой поток принимается постоянно. В polling-режиме этот же параметр
задаёт частоту HTTP-запросов.

## Запуск

```bash
copy .env.example .env
docker compose up --build
```

- интерфейс: http://localhost:8000
- API docs: http://localhost:8000/docs
- phpMyAdmin: http://localhost:8080

## Binance и ручная торговля

Автоматическая торговля отсутствует. Ручки открытия и закрытия отправляют market-ордер
только при явном `confirm=true`. Количество рассчитывается по `ask` для покупки и по
`bid` для продажи с учётом `MARKET_LOT_SIZE`, минимального notional и выбранного
округления.

Ключи не сохраняются в MySQL и не возвращаются через API. Они лежат локально в
`local_data/settings.json`, который подключён к контейнеру отдельным volume.

## Основные API

- `GET /api/v1/assets`
- `GET /api/v1/favorites`
- `POST /api/v1/favorites/{asset_id}`
- `DELETE /api/v1/favorites/{asset_id}`
- `GET /api/v1/blacklist`
- `POST /api/v1/blacklist/{asset_id}`
- `DELETE /api/v1/blacklist/{asset_id}`
- `GET /api/v1/runtime/settings`
- `PUT /api/v1/runtime/mode`
- `PUT /api/v1/runtime/interval`
- `POST /api/v1/system/sync-instruments`
- `WS /ws/quotes`


### Аккаунт Binance

- `GET /api/v1/exchanges/binance/settings`
- `GET /api/v1/exchanges/binance/status`
- `GET /api/v1/exchanges/binance/balance`
- `POST /api/v1/exchanges/binance/connect`
- `POST /api/v1/exchanges/binance/disconnect`

### Ручные операции Binance

- `GET /api/v1/exchanges/binance/volume-preview`
- `GET /api/v1/exchanges/binance/positions`
- `PUT /api/v1/exchanges/binance/leverage`
- `POST /api/v1/exchanges/binance/positions/open`
- `POST /api/v1/exchanges/binance/positions/close`
- `GET /api/v1/trading/settings`
- `PUT /api/v1/trading/settings`
