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
- избранные активы в MySQL;
- настройки интерфейса в `localStorage` браузера;
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

## Основные API

- `GET /api/v1/assets`
- `GET /api/v1/favorites`
- `POST /api/v1/favorites/{asset_id}`
- `DELETE /api/v1/favorites/{asset_id}`
- `GET /api/v1/runtime/settings`
- `PUT /api/v1/runtime/mode`
- `PUT /api/v1/runtime/interval`
- `POST /api/v1/system/sync-instruments`
- `WS /ws/quotes`
